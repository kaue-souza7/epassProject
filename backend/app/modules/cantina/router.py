import os
import uuid
import uuid as uuid_mod
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, UploadFile, File as FastAPIFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.cantina.schemas import (
    CantinaConfigResponse,
    CantinaConfigUpdate,
    CantinaStudentResponse,
    ConsumoDiretoRequest,
    ConsumoDiretoResponse,
    AutonomiaResponse,
    AutonomiaUpdate,
    EstoqueOperacao,
    EstoqueResponse,
    ItemPedidoResponse,
    MenuResponse,
    MovimentacaoEstoqueResponse,
    PedidoCreate,
    PedidoListResponse,
    PedidoResponse,
    ProdutoCreate,
    ProdutoResponse,
    ProdutoUpdate,
)
from app.modules.cantina.service import CantinaService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/cantina", tags=["cantina"], redirect_slashes=False)

CANTINA_ADMIN_CANTINEIRO = (Perfil.ADMIN, Perfil.CANTINEIRO)


def _pedido_to_response(pedido) -> PedidoResponse:
    """Convert a Pedido ORM object to PedidoResponse schema."""
    return PedidoResponse(
        id=pedido.id,
        aluno_id=pedido.aluno_id,
        aluno_nome=pedido.aluno.nome if pedido.aluno else None,
        responsavel_id=pedido.responsavel_id,
        status=pedido.status,
        valor_total=pedido.valor_total,
        saldo_debitado=pedido.saldo_debitado,
        movimentacao_id=pedido.movimentacao_id,
        observacoes=pedido.observacoes,
        itens=[
            ItemPedidoResponse(
                id=item.id,
                produto_id=item.produto_id,
                produto_nome=item.produto.nome if item.produto else None,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                preco_total=item.preco_total,
            )
            for item in pedido.itens
        ],
        created_at=pedido.created_at,
        updated_at=pedido.updated_at,
    )


@router.post("/upload", response_model=dict)
async def upload_imagem(
    file: UploadFile = FastAPIFile(...),
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
) -> dict:
    from fastapi import HTTPException

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Tipo de arquivo não permitido: {file.content_type}")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Arquivo excede o limite de 5MB")

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid_mod.uuid4().hex}.{ext}"
    upload_dir = os.path.join("storage", "cantina")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/storage/cantina/{filename}"
    return {"url": url}


@router.get("/dashboard", response_model=dict)
async def obter_dashboard(
    dias: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    service = CantinaService(session)
    return await service.obter_dashboard(dias=dias)


# ══════════════════════════════════════════════════════════════════
# CARDÁPIO PÚBLICO (sem autenticação)
# ══════════════════════════════════════════════════════════════════


@router.get("/menu", response_model=MenuResponse)
async def obter_cardapio(
    session: AsyncSession = Depends(get_session),
) -> MenuResponse:
    service = CantinaService(session)
    return await service.obter_cardapio()


# ══════════════════════════════════════════════════════════════════
# CONSULTA DE ALUNO (ADMIN + CANTINEIRO)
# ══════════════════════════════════════════════════════════════════


@router.get("/students/search", response_model=list[CantinaStudentResponse])
async def buscar_alunos_cantina(
    q: str = Query(..., min_length=1, description="Termo de busca (nome do aluno)"),
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> list[CantinaStudentResponse]:
    from app.modules.students.repository import AlunoRepository
    from app.modules.enrollments.repository import MatriculaRepository
    from app.modules.financial.repository import WalletRepository

    aluno_repo = AlunoRepository(session)
    matricula_repo = MatriculaRepository(session)
    wallet_repo = WalletRepository(session)

    alunos = await aluno_repo.search_by_nome(q)
    alunos_limitados = alunos[:20]

    if not alunos_limitados:
        return []

    aluno_ids = [a.id for a in alunos_limitados]

    matriculas_result, _ = await matricula_repo.search(aluno_ids=aluno_ids, size=len(aluno_ids))
    turmas_map: dict[uuid.UUID, str | None] = {}
    for matricula, _nome, codigo in matriculas_result:
        turmas_map[matricula.aluno_id] = codigo

    from sqlalchemy import select as sa_select
    from app.modules.financial.models import Wallet
    wallets_result = await session.execute(
        sa_select(Wallet).where(Wallet.aluno_id.in_(aluno_ids))
    )
    wallets_map = {w.aluno_id: w.saldo for w in wallets_result.scalars().all()}

    result: list[CantinaStudentResponse] = []
    for aluno in alunos_limitados:
        result.append(CantinaStudentResponse(
            id=aluno.id,
            nome=aluno.nome,
            turma=turmas_map.get(aluno.id),
            saldo=wallets_map.get(aluno.id, Decimal("0.00")),
            autonomia_cantina=aluno.autonomia_cantina,
        ))

    return result


# ══════════════════════════════════════════════════════════════════
# PEDIDOS DO RESPONSÁVEL
# ══════════════════════════════════════════════════════════════════


@router.get("/me/orders/today", response_model=PedidoResponse | None)
async def obter_pedido_do_dia(
    aluno_id: uuid.UUID = Query(..., description="ID do aluno"),
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse | None:
    service = CantinaService(session)
    pedido = await service.obter_pedido_do_dia(
        responsavel_id=uuid.UUID(current_user["sub"]),
        aluno_id=aluno_id,
    )
    if pedido is None:
        return None
    return _pedido_to_response(pedido)


@router.get("/me/orders", response_model=PaginatedResponse)
async def listar_meus_pedidos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    aluno_id: uuid.UUID | None = Query(None, description="Filtra por aluno vinculado"),
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = CantinaService(session)
    items, total = await service.listar_pedidos_do_responsavel(
        responsavel_id=uuid.UUID(current_user["sub"]),
        page=page,
        size=size,
        aluno_id=aluno_id,
    )
    return PaginatedResponse(
        items=[PedidoListResponse(
            id=p.id,
            aluno_id=p.aluno_id,
            aluno_nome=p.aluno.nome if p.aluno else None,
            status=p.status,
            valor_total=p.valor_total,
            observacoes=p.observacoes,
            itens=[
                ItemPedidoResponse(
                    id=item.id,
                    produto_id=item.produto_id,
                    produto_nome=item.produto.nome if item.produto else None,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    preco_total=item.preco_total,
                )
                for item in p.itens
            ],
            created_at=p.created_at,
        ).model_dump() for p in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/me/orders/{id}", response_model=PedidoResponse)
async def obter_meu_pedido(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.obter_pedido(
        pedido_id=id,
        responsavel_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


@router.post("/orders", response_model=PedidoResponse, status_code=201)
async def criar_pedido(
    body: PedidoCreate,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.criar_pedido(
        data=body,
        responsavel_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


# ══════════════════════════════════════════════════════════════════
# GESTÃO DE PRODUTOS — VISUALIZAÇÃO (ADMIN + CANTINEIRO)
# ══════════════════════════════════════════════════════════════════


@router.get("/products", response_model=PaginatedResponse)
async def listar_produtos(
    ativo: bool | None = Query(None),
    categoria: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = CantinaService(session)
    items, total = await service.listar_produtos(
        ativo=ativo, categoria=categoria, page=page, size=size,
    )
    return PaginatedResponse(
        items=[ProdutoResponse.model_validate(p).model_dump() for p in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/products/{id}", response_model=ProdutoResponse)
async def obter_produto(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> ProdutoResponse:
    service = CantinaService(session)
    produto = await service.obter_produto(id)
    return ProdutoResponse.model_validate(produto)


# ══════════════════════════════════════════════════════════════════
# GESTÃO DE PRODUTOS — ESCRITA (ADMIN)
# ══════════════════════════════════════════════════════════════════


@router.post("/products", response_model=ProdutoResponse, status_code=201)
async def criar_produto(
    body: ProdutoCreate,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> ProdutoResponse:
    service = CantinaService(session)
    produto = await service.criar_produto(body)
    return ProdutoResponse.model_validate(produto)


@router.put("/products/{id}", response_model=ProdutoResponse)
async def editar_produto(
    id: uuid.UUID,
    body: ProdutoUpdate,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> ProdutoResponse:
    service = CantinaService(session)
    produto = await service.editar_produto(id, body)
    return ProdutoResponse.model_validate(produto)


@router.patch("/products/{id}/toggle", response_model=ProdutoResponse)
async def toggle_produto(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> ProdutoResponse:
    service = CantinaService(session)
    produto = await service.toggle_status(id)
    return ProdutoResponse.model_validate(produto)


# ══════════════════════════════════════════════════════════════════
# ESTOQUE (ADMIN + CANTINEIRO)
# ══════════════════════════════════════════════════════════════════


@router.post("/products/{id}/stock", response_model=EstoqueResponse, status_code=201)
async def ajustar_estoque(
    id: uuid.UUID,
    body: EstoqueOperacao,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> EstoqueResponse:
    service = CantinaService(session)
    return await service.ajustar_estoque(
        id, body, usuario_id=uuid.UUID(current_user["sub"]),
    )


@router.get("/products/{id}/stock-history", response_model=PaginatedResponse)
async def historico_estoque(
    id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    from app.modules.users.repository import UsuarioRepository

    service = CantinaService(session)
    items, total = await service.listar_historico_estoque(
        produto_id=id, page=page, size=size,
    )
    user_ids = [m.usuario_id for m in items if m.usuario_id]
    user_names: dict[uuid.UUID, str] = {}
    if user_ids:
        user_repo = UsuarioRepository(session)
        usuarios = await user_repo.get_by_ids(user_ids)
        user_names = {u.id: u.nome for u in usuarios}

    return PaginatedResponse(
        items=[MovimentacaoEstoqueResponse(
            id=m.id,
            produto_id=m.produto_id,
            tipo=m.tipo.value,
            quantidade=m.quantidade,
            estoque_anterior=m.estoque_anterior,
            estoque_atual=m.estoque_atual,
            motivo=m.motivo,
            usuario_nome=user_names.get(m.usuario_id) if m.usuario_id else None,
            created_at=m.created_at,
        ).model_dump() for m in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


# ══════════════════════════════════════════════════════════════════
# GESTÃO DE PEDIDOS (ADMIN + CANTINEIRO)
# ══════════════════════════════════════════════════════════════════


@router.get("/orders", response_model=PaginatedResponse)
async def listar_pedidos(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    from app.modules.enrollments.repository import MatriculaRepository

    service = CantinaService(session)
    items, total = await service.listar_pedidos_cantina(
        status=status,
        page=page,
        size=size,
    )

    aluno_ids = list({p.aluno_id for p in items})
    turmas_map: dict[uuid.UUID, str | None] = {}
    if aluno_ids:
        matricula_repo = MatriculaRepository(session)
        matriculas_result, _ = await matricula_repo.search(aluno_ids=aluno_ids, size=len(aluno_ids))
        for matricula, _nome, codigo in matriculas_result:
            turmas_map[matricula.aluno_id] = codigo

    return PaginatedResponse(
        items=[PedidoListResponse(
            id=p.id,
            aluno_id=p.aluno_id,
            aluno_nome=p.aluno.nome if p.aluno else None,
            aluno_turma=turmas_map.get(p.aluno_id),
            status=p.status,
            valor_total=p.valor_total,
            observacoes=p.observacoes,
            itens=[
                ItemPedidoResponse(
                    id=item.id,
                    produto_id=item.produto_id,
                    produto_nome=item.produto.nome if item.produto else None,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    preco_total=item.preco_total,
                )
                for item in p.itens
            ],
            created_at=p.created_at,
        ).model_dump() for p in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/orders/{id}", response_model=PedidoResponse)
async def obter_pedido(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.obter_pedido(pedido_id=id)
    return _pedido_to_response(pedido)


@router.patch("/orders/{id}/approve", response_model=PedidoResponse)
async def aprovar_pedido(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.aprovar_pedido(
        pedido_id=id,
        usuario_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


@router.patch("/orders/{id}/reject", response_model=PedidoResponse)
async def rejeitar_pedido(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    pedido = await service.rejeitar_pedido(pedido_id=id, usuario_id=usuario_id)
    return _pedido_to_response(pedido)


@router.patch("/orders/{id}/produce", response_model=PedidoResponse)
async def iniciar_producao(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.iniciar_producao(
        pedido_id=id, usuario_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


@router.patch("/orders/{id}/ready", response_model=PedidoResponse)
async def marcar_pronto(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.marcar_pronto(
        pedido_id=id, usuario_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


@router.patch("/orders/{id}/delivered", response_model=PedidoResponse)
async def marcar_retirado(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.marcar_retirado(
        pedido_id=id, usuario_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


@router.get("/orders/{id}/history", response_model=list[dict])
async def historico_pedido(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    from app.modules.users.repository import UsuarioRepository

    service = CantinaService(session)
    historico = await service.obter_historico_status(id)

    user_ids = [h.usuario_id for h in historico if h.usuario_id]
    user_names: dict[uuid.UUID, str] = {}
    if user_ids:
        usuarios = await UsuarioRepository(session).get_by_ids(user_ids)
        user_names = {u.id: u.nome for u in usuarios}

    return [
        {
            "id": h.id,
            "status_anterior": h.status_anterior.value if h.status_anterior else None,
            "status_novo": h.status_novo.value,
            "usuario_id": h.usuario_id,
            "usuario_nome": user_names.get(h.usuario_id) if h.usuario_id else None,
            "observacao": h.observacao,
            "created_at": h.created_at,
        }
        for h in historico
    ]


@router.patch("/orders/{id}/cancel", response_model=PedidoResponse)
async def cancelar_pedido_cantina(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.cancelar_pedido(
        pedido_id=id,
        usuario_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


@router.patch("/me/orders/{id}/cancel", response_model=PedidoResponse)
async def cancelar_pedido_responsavel(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    service = CantinaService(session)
    pedido = await service.cancelar_pedido(
        pedido_id=id,
        usuario_id=uuid.UUID(current_user["sub"]),
        responsavel_id=uuid.UUID(current_user["sub"]),
    )
    return _pedido_to_response(pedido)


# ══════════════════════════════════════════════════════════════════
# CONVERSÃO DE PROGRAMAÇÃO EM PEDIDO (ADMIN + RESPONSÁVEL)
# ══════════════════════════════════════════════════════════════════


@router.post("/programacao/{programacao_id}/converter-pedido", response_model=PedidoResponse, status_code=201)
async def converter_programacao_em_pedido(
    programacao_id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL, Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> PedidoResponse:
    from app.modules.cantina.programacao_repository import ProgramacaoRepository
    from app.modules.cantina.programacao_models import ProgramacaoCantina

    service = CantinaService(session)
    repo = ProgramacaoRepository(session)

    programacao = await repo.get_by_id(programacao_id)
    if programacao is None:
        from app.core.exceptions import NotFound
        raise NotFound("Programação não encontrada")

    if current_user["perfil"] == "responsavel":
        if programacao.responsavel_id != uuid.UUID(current_user["sub"]):
            from app.core.exceptions import Forbidden
            raise Forbidden("Você não possui acesso a esta programação")

    await service.validar_config_para_pedido()

    pedido = await service._criar_pedido_de_programacao_manual(programacao)
    return _pedido_to_response(pedido)


# ══════════════════════════════════════════════════════════════════
# AUTONOMIA DO ALUNO (RESPONSAVEL + ADMIN + CANTINEIRO leitura)
# ══════════════════════════════════════════════════════════════════


@router.get("/students/{aluno_id}/autonomy", response_model=AutonomiaResponse)
async def obter_autonomia(
    aluno_id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL, Perfil.ADMIN, Perfil.CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> AutonomiaResponse:
    from app.modules.students.repository import AlunoRepository
    repo = AlunoRepository(session)
    aluno = await repo.get_by_id(aluno_id)
    if aluno is None:
        from app.core.exceptions import NotFound
        raise NotFound("Aluno não encontrado")

    # RESPONSAVEL must be linked to the student
    if current_user["perfil"] == "responsavel":
        from app.modules.students.repository import ResponsavelAlunoRepository
        vinculo_repo = ResponsavelAlunoRepository(session)
        vinculo = await vinculo_repo.get_by_aluno_and_responsavel(
            aluno_id, uuid.UUID(current_user["sub"]),
        )
        if vinculo is None:
            from app.core.exceptions import Forbidden
            raise Forbidden("Você não possui acesso a este aluno")

    return AutonomiaResponse(
        aluno_id=aluno.id,
        autonomia_cantina=aluno.autonomia_cantina,
    )


@router.put("/students/{aluno_id}/autonomy", response_model=AutonomiaResponse)
async def atualizar_autonomia(
    aluno_id: uuid.UUID,
    body: AutonomiaUpdate,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL, Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> AutonomiaResponse:
    from app.modules.students.repository import AlunoRepository, ResponsavelAlunoRepository
    from app.core.exceptions import Forbidden, NotFound

    repo = AlunoRepository(session)
    aluno = await repo.get_by_id(aluno_id)
    if aluno is None:
        raise NotFound("Aluno não encontrado")

    # RESPONSAVEL must be linked to the student
    if current_user["perfil"] == "responsavel":
        vinculo_repo = ResponsavelAlunoRepository(session)
        vinculo = await vinculo_repo.get_by_aluno_and_responsavel(
            aluno_id, uuid.UUID(current_user["sub"]),
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a este aluno")

    # CANTINEIRO cannot modify
    if current_user["perfil"] == "cantineiro":
        raise Forbidden("Cantineiro não pode alterar autonomia")

    aluno.autonomia_cantina = body.autonomia_cantina
    await repo.update(aluno)

    return AutonomiaResponse(
        aluno_id=aluno.id,
        autonomia_cantina=aluno.autonomia_cantina,
    )


# ══════════════════════════════════════════════════════════════════
# CONSUMO DIRETO NA CANTINA (CANTINEIRO + ADMIN)
# ══════════════════════════════════════════════════════════════════


@router.post("/consumo-direto", response_model=ConsumoDiretoResponse, status_code=201)
async def consumo_direto(
    body: ConsumoDiretoRequest,
    current_user: dict = Depends(require_roles(*CANTINA_ADMIN_CANTINEIRO)),
    session: AsyncSession = Depends(get_session),
) -> ConsumoDiretoResponse:
    service = CantinaService(session)
    return await service.registrar_consumo_direto(
        data=body,
        operador_id=uuid.UUID(current_user["sub"]),
    )


# ══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA CANTINA (ADMIN)
# ══════════════════════════════════════════════════════════════════


@router.get("/config", response_model=CantinaConfigResponse)
async def obter_config(
    current_user: dict = Depends(require_roles(Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> CantinaConfigResponse:
    service = CantinaService(session)
    config = await service.obter_config()
    return CantinaConfigResponse.model_validate(config)


@router.put("/config", response_model=CantinaConfigResponse)
async def atualizar_config(
    body: CantinaConfigUpdate,
    current_user: dict = Depends(require_roles(Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> CantinaConfigResponse:
    service = CantinaService(session)
    config = await service.atualizar_config(body)
    return CantinaConfigResponse.model_validate(config)
