from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationError
from app.modules.cantina.models import (
    CantinaConfig,
    ItemPedido,
    MovimentacaoEstoque,
    Pedido,
    PedidoStatusHistorico,
    Produto,
)
from app.modules.cantina.repository import MovimentacaoEstoqueRepository, PedidoRepository, ProdutoRepository
from app.modules.cantina.utils import (
    DIAS_PARA_ALERTA_VENCIMENTO,
    agora_local,
    dias_para_vencer,
    get_timezone,
    produto_vencido,
)
from app.modules.cantina.schemas import (
    CantinaConfigUpdate,
    ConsumoDiretoRequest,
    ConsumoDiretoResponse,
    EstoqueOperacao,
    EstoqueResponse,
    ItemPedidoCreate,
    ItemPedidoResponse,
    MenuResponse,
    MenuItem,
    PedidoCreate,
    PedidoListResponse,
    PedidoResponse,
    ProdutoCreate,
    ProdutoResponse,
    ProdutoUpdate,
)
from app.modules.auth.models import Sessao  # noqa: F401 — ensure Sessao mapper is configured
from app.modules.financial.service import FinancialService
from app.modules.students.repository import AlunoRepository, ResponsavelAlunoRepository
from app.shared.enums import (
    DiaSemana,
    OrigemPedido,
    Perfil,
    StatusPedido,
    StatusProduto,
    TipoMovimentacaoEstoque,
    TipoNotificacao,
)


# Transições de status permitidas
TRANSICOES_PERMITIDAS: dict[StatusPedido, list[StatusPedido]] = {
    StatusPedido.PENDENTE: [StatusPedido.APROVADO, StatusPedido.CANCELADO],
    StatusPedido.APROVADO: [StatusPedido.EM_PRODUCAO, StatusPedido.CANCELADO],
    StatusPedido.EM_PRODUCAO: [StatusPedido.PRONTO],
    StatusPedido.PRONTO: [StatusPedido.RETIRADO],
    StatusPedido.RETIRADO: [],
    StatusPedido.CANCELADO: [],
}

_DIA_SEMANA_MAP: dict[int, DiaSemana] = {
    0: DiaSemana.SEG,
    1: DiaSemana.TER,
    2: DiaSemana.QUA,
    3: DiaSemana.QUI,
    4: DiaSemana.SEX,
    5: DiaSemana.SAB,
}


class CantinaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._produto_repo = ProdutoRepository(session)
        self._pedido_repo = PedidoRepository(session)
        self._movimentacao_repo = MovimentacaoEstoqueRepository(session)
        self._aluno_repo = AlunoRepository(session)
        self._vinculo_repo = ResponsavelAlunoRepository(session)
        self._financial_service = FinancialService(session)

    # ── Config ─────────────────────────────────────────────────────

    async def _get_config(self) -> CantinaConfig:
        from sqlalchemy import select as sa_select
        result = await self._session.execute(
            sa_select(CantinaConfig).order_by(CantinaConfig.updated_at.asc()).limit(1)
        )
        config = result.scalars().first()
        if config is None:
            config = CantinaConfig(aberta=True)
            self._session.add(config)
            await self._session.flush()
        return config

    async def obter_config(self) -> CantinaConfig:
        return await self._get_config()

    async def atualizar_config(self, data: CantinaConfigUpdate) -> CantinaConfig:
        config = await self._get_config()
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        config.updated_at = datetime.now(timezone.utc)
        self._session.add(config)
        await self._session.flush()
        return config

    async def _hoje(self, config: CantinaConfig | None = None) -> date:
        if config is None:
            config = await self._get_config()
        return agora_local(config.timezone).date()

    async def _validar_matricula_ativa(self, aluno) -> None:
        """Aluno com matrículas cadastradas precisa ter ao menos uma ativa."""
        from app.modules.enrollments.repository import MatriculaRepository
        from app.shared.enums import StatusMatricula

        matriculas = await MatriculaRepository(self._session).get_by_aluno(aluno.id)
        if matriculas and not any(m.status == StatusMatricula.ATIVA for m in matriculas):
            raise ValidationError("Aluno sem matrícula ativa")

    async def validar_config_para_pedido(self) -> None:
        config = await self._get_config()

        if not config.aberta:
            raise ValidationError("A cantina está fechada no momento")

        agora = agora_local(config.timezone)
        hoje = agora.date()
        dia_semana_atual = _DIA_SEMANA_MAP.get(hoje.weekday())
        if dia_semana_atual is None:
            raise ValidationError("A cantina não funciona aos domingos")

        if config.dias_funcionamento:
            dias_ativos = [d.strip().lower() for d in config.dias_funcionamento.split(",")]
            if dia_semana_atual.value not in dias_ativos:
                raise ValidationError("A cantina não funciona neste dia da semana")

        hora_atual = agora.time().replace(tzinfo=None)
        h_fechamento: time | None = None

        if config.horario_abertura:
            try:
                h_abertura = time.fromisoformat(config.horario_abertura)
            except ValueError:
                h_abertura = None
            if h_abertura and hora_atual < h_abertura:
                raise ValidationError(
                    f"A cantina ainda não abriu. Horário de abertura: {config.horario_abertura}"
                )

        if config.horario_fechamento:
            try:
                h_fechamento = time.fromisoformat(config.horario_fechamento)
            except ValueError:
                h_fechamento = None
            if h_fechamento and hora_atual > h_fechamento:
                raise ValidationError(
                    f"A cantina já fechou. Horário de fechamento: {config.horario_fechamento}"
                )

        # Prazo para pedir: o pedido deve ser feito até N minutos antes do fechamento.
        if (
            h_fechamento is not None
            and config.prazo_pedido_minutos
            and config.prazo_pedido_minutos > 0
        ):
            hora_limite = (
                datetime.combine(hoje, h_fechamento) - timedelta(minutes=config.prazo_pedido_minutos)
            ).time()
            if hora_atual > hora_limite:
                raise ValidationError(
                    "O prazo para pedidos expirou. "
                    f"Pedidos são aceitos até {hora_limite.strftime('%H:%M')}."
                )

    async def validar_config_para_cancelamento(self, pedido: Pedido) -> None:
        config = await self._get_config()

        if config.prazo_cancelamento_minutos is not None and config.prazo_cancelamento_minutos > 0:
            from datetime import timedelta
            tempo_desde_criacao = datetime.now(timezone.utc) - pedido.created_at
            if tempo_desde_criacao > timedelta(minutes=config.prazo_cancelamento_minutos):
                raise ValidationError(
                    "O prazo para cancelamento expirou. "
                    f"O cancelamento deve ser feito em até {config.prazo_cancelamento_minutos} minutos."
                )

    # ── Produtos ──────────────────────────────────────────────────

    async def listar_produtos(
        self,
        ativo: StatusProduto | None = None,
        categoria: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Produto], int]:
        return await self._produto_repo.get_all(ativo=ativo, categoria=categoria, page=page, size=size)

    async def obter_produto(self, produto_id: uuid.UUID) -> Produto:
        produto = await self._produto_repo.get_by_id(produto_id)
        if produto is None:
            raise NotFound("Produto não encontrado")
        return produto

    async def criar_produto(self, data: ProdutoCreate) -> Produto:
        self._validar_produto(data)
        produto = Produto(
            nome=data.nome,
            descricao=data.descricao,
            preco=data.preco,
            imagem_url=data.imagem_url,
            categoria=data.categoria,
            estoque_atual=data.estoque_atual,
            estoque_minimo=data.estoque_minimo,
            codigo=data.codigo,
            custo=data.custo,
            unidade_medida=data.unidade_medida,
            perecivel=data.perecivel,
            data_validade=data.data_validade,
            ativo=True,
        )
        return await self._produto_repo.create(produto)

    async def editar_produto(
        self, produto_id: uuid.UUID, data: ProdutoUpdate,
    ) -> Produto:
        produto = await self._produto_repo.get_by_id(produto_id)
        if produto is None:
            raise NotFound("Produto não encontrado")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return produto

        if "preco" in update_data and update_data["preco"] is not None:
            if update_data["preco"] <= 0:
                raise ValidationError("Preço deve ser maior que zero")
            produto.preco = update_data["preco"]

        if "nome" in update_data and update_data["nome"] is not None:
            produto.nome = update_data["nome"]

        if "descricao" in update_data:
            produto.descricao = update_data["descricao"]

        if "imagem_url" in update_data:
            produto.imagem_url = update_data["imagem_url"]

        if "categoria" in update_data and update_data["categoria"] is not None:
            produto.categoria = update_data["categoria"]

        if "estoque_minimo" in update_data and update_data["estoque_minimo"] is not None:
            if update_data["estoque_minimo"] < 0:
                raise ValidationError("Estoque mínimo não pode ser negativo")
            produto.estoque_minimo = update_data["estoque_minimo"]

        if "codigo" in update_data:
            produto.codigo = update_data["codigo"]
        if "custo" in update_data:
            produto.custo = update_data["custo"]
        if "unidade_medida" in update_data:
            produto.unidade_medida = update_data["unidade_medida"]
        if "perecivel" in update_data and update_data["perecivel"] is not None:
            produto.perecivel = update_data["perecivel"]
        if "data_validade" in update_data:
            produto.data_validade = update_data["data_validade"]

        if produto.perecivel and produto.data_validade is None:
            raise ValidationError("Produto perecível deve possuir data de validade")

        return await self._produto_repo.update(produto)

    async def toggle_status(self, produto_id: uuid.UUID) -> Produto:
        produto = await self._produto_repo.toggle_status(produto_id)
        if produto is None:
            raise NotFound("Produto não encontrado")
        return produto

    # ── Estoque ───────────────────────────────────────────────────

    async def ajustar_estoque(
        self,
        produto_id: uuid.UUID,
        data: EstoqueOperacao,
        usuario_id: uuid.UUID | None = None,
    ) -> EstoqueResponse:
        produto = await self._produto_repo.get_by_id_for_update(produto_id)
        if produto is None:
            raise NotFound("Produto não encontrado")

        if data.quantidade == 0:
            raise ValidationError("Informe uma quantidade diferente de zero")

        estoque_anterior = produto.estoque_atual
        novo_estoque = estoque_anterior + data.quantidade

        if novo_estoque < 0:
            raise ValidationError(
                f"Estoque insuficiente. Estoque atual: {estoque_anterior}, "
                f"tentativa de redução: {abs(data.quantidade)}"
            )

        produto.estoque_atual = novo_estoque
        await self._produto_repo.update(produto)

        tipo = TipoMovimentacaoEstoque.ENTRADA if data.quantidade > 0 else TipoMovimentacaoEstoque.SAIDA
        mov = MovimentacaoEstoque(
            produto_id=produto_id,
            tipo=tipo,
            quantidade=abs(data.quantidade),
            estoque_anterior=estoque_anterior,
            estoque_atual=novo_estoque,
            motivo=data.motivo,
            usuario_id=usuario_id,
        )
        await self._movimentacao_repo.create(mov)

        return EstoqueResponse(
            produto_id=produto.id,
            estoque_anterior=estoque_anterior,
            quantidade=data.quantidade,
            estoque_atual=novo_estoque,
            motivo=data.motivo,
        )

    async def listar_historico_estoque(
        self,
        produto_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[MovimentacaoEstoque], int]:
        return await self._movimentacao_repo.list_by_produto(
            produto_id=produto_id, page=page, size=size,
        )

    # ── Cardápio público ──────────────────────────────────────────

    async def obter_cardapio(self) -> MenuResponse:
        config = await self._get_config()
        tz = config.timezone
        produtos = await self._produto_repo.get_all_active()
        itens = []
        for p in produtos:
            itens.append(
                MenuItem(
                    id=p.id,
                    nome=p.nome,
                    descricao=p.descricao,
                    preco=p.preco,
                    imagem_url=p.imagem_url,
                    disponivel=p.estoque_atual > 0 and not produto_vencido(p, tz),
                    perecivel=p.perecivel,
                    data_validade=p.data_validade,
                )
            )
        return MenuResponse(itens=itens)

    # ── Validações ────────────────────────────────────────────────

    def _validar_produto(self, data: ProdutoCreate) -> None:
        if not data.nome or not data.nome.strip():
            raise ValidationError("Nome do produto é obrigatório")
        if data.preco <= 0:
            raise ValidationError("Preço deve ser maior que zero")
        if data.estoque_atual < 0:
            raise ValidationError("Estoque atual não pode ser negativo")
        if data.estoque_minimo < 0:
            raise ValidationError("Estoque mínimo não pode ser negativo")
        if data.perecivel and data.data_validade is None:
            raise ValidationError("Produto perecível deve possuir data de validade")

    def _validar_transicao_status(
        self, status_atual: StatusPedido, novo_status: StatusPedido,
    ) -> None:
        transicoes = TRANSICOES_PERMITIDAS.get(status_atual, [])
        if novo_status not in transicoes:
            raise ValidationError(
                f"Transição de status inválida: {status_atual.value} → {novo_status.value}"
            )

    def _agregar_itens(self, itens) -> list[tuple[uuid.UUID, int]]:
        """Agrega quantidades por produto (evita validar o mesmo produto 2x)."""
        agregados: dict[uuid.UUID, int] = {}
        for item in itens:
            agregados[item.produto_id] = agregados.get(item.produto_id, 0) + item.quantidade
        return list(agregados.items())

    def _validar_produto_para_venda(
        self, produto: Produto, quantidade: int, tz: str | None,
    ) -> None:
        if not produto.ativo:
            raise ValidationError(f"Produto '{produto.nome}' está inativo")
        if produto_vencido(produto, tz):
            raise ValidationError(
                f"Produto '{produto.nome}' está vencido e não pode ser vendido"
            )
        if produto.estoque_atual < quantidade:
            raise ValidationError(
                f"Estoque insuficiente para '{produto.nome}'. "
                f"Disponível: {produto.estoque_atual}, solicitado: {quantidade}"
            )

    async def _baixar_estoque(
        self,
        produto: Produto,
        quantidade: int,
        usuario_id: uuid.UUID | None,
        motivo: str,
    ) -> MovimentacaoEstoque:
        estoque_anterior = produto.estoque_atual
        produto.estoque_atual = estoque_anterior - quantidade
        await self._produto_repo.update(produto)
        return await self._movimentacao_repo.create(MovimentacaoEstoque(
            produto_id=produto.id,
            tipo=TipoMovimentacaoEstoque.SAIDA,
            quantidade=quantidade,
            estoque_anterior=estoque_anterior,
            estoque_atual=produto.estoque_atual,
            motivo=motivo,
            usuario_id=usuario_id,
        ))

    async def _devolver_estoque(
        self,
        produto: Produto,
        quantidade: int,
        usuario_id: uuid.UUID | None,
        motivo: str,
    ) -> MovimentacaoEstoque:
        estoque_anterior = produto.estoque_atual
        produto.estoque_atual = estoque_anterior + quantidade
        await self._produto_repo.update(produto)
        return await self._movimentacao_repo.create(MovimentacaoEstoque(
            produto_id=produto.id,
            tipo=TipoMovimentacaoEstoque.ENTRADA,
            quantidade=quantidade,
            estoque_anterior=estoque_anterior,
            estoque_atual=produto.estoque_atual,
            motivo=motivo,
            usuario_id=usuario_id,
        ))

    # ── Notificações ──────────────────────────────────────────────

    async def _notificar(
        self,
        destinatario_id: uuid.UUID,
        titulo: str,
        mensagem: str,
        evento_key: str,
        pedido_id: uuid.UUID,
    ) -> None:
        from app.core.notifications import NotificationDispatcher

        await NotificationDispatcher(self._session).dispatch(
            usuario_id=destinatario_id,
            titulo=titulo,
            corpo=mensagem,
            canal="inapp",
            tipo=TipoNotificacao.CANTINA,
            entidade_tipo="pedido",
            entidade_id=pedido_id,
            evento_key=evento_key,
        )

    async def _notificar_staff_cantina(
        self,
        pedido: Pedido,
        titulo: str,
        mensagem: str,
        evento: str,
    ) -> None:
        from app.modules.users.repository import UsuarioRepository

        usuarios = await UsuarioRepository(self._session).get_by_perfis(
            [Perfil.ADMIN, Perfil.CANTINEIRO],
        )
        for usuario in usuarios:
            await self._notificar(
                destinatario_id=usuario.id,
                titulo=titulo,
                mensagem=mensagem,
                evento_key=f"pedido-{evento}:{pedido.id}:{usuario.id}",
                pedido_id=pedido.id,
            )

    async def _notificar_responsavel_pedido(
        self,
        pedido: Pedido,
        titulo: str,
        mensagem: str,
        evento: str,
    ) -> None:
        await self._notificar(
            destinatario_id=pedido.responsavel_id,
            titulo=titulo,
            mensagem=mensagem,
            evento_key=f"pedido-{evento}:{pedido.id}",
            pedido_id=pedido.id,
        )

    def _registrar_status(
        self,
        pedido: Pedido,
        novo_status: StatusPedido,
        usuario_id: uuid.UUID | None = None,
        observacao: str | None = None,
    ) -> None:
        status_anterior = pedido.status
        pedido.status = novo_status
        if pedido.id is not None:
            self._session.add(PedidoStatusHistorico(
                pedido_id=pedido.id,
                status_anterior=status_anterior,
                status_novo=novo_status,
                usuario_id=usuario_id,
                observacao=observacao,
            ))

    # ── Pedidos ──────────────────────────────────────────────────

    async def criar_pedido(
        self,
        data: PedidoCreate,
        responsavel_id: uuid.UUID,
    ) -> Pedido:
        config = await self._get_config()
        await self.validar_config_para_pedido()
        tz = config.timezone

        aluno = await self._aluno_repo.get_by_id(data.aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if not aluno.ativo:
            raise ValidationError("Aluno inativo não pode realizar pedidos")
        await self._validar_matricula_ativa(aluno)

        vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
            data.aluno_id, responsavel_id,
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a este aluno")

        hoje = agora_local(tz).date()
        if await self._pedido_repo.existe_pedido_hoje_para_aluno(data.aluno_id, hoje):
            raise Conflict("Já existe um pedido para este aluno hoje")

        # Ordem de lock consistente em todo o módulo: carteira → produtos.
        wallet = await self._financial_service._wallet_repo.get_by_aluno_id_for_update(
            data.aluno_id,
        )
        if wallet is None:
            raise ValidationError("Este aluno não possui carteira ativa")
        self._financial_service._validar_wallet_ativa(wallet)

        itens_processados: list[tuple[Produto, int, Decimal]] = []
        valor_total = Decimal("0.00")

        for produto_id, quantidade in self._agregar_itens(data.itens):
            produto = await self._produto_repo.get_by_id_for_update(produto_id)
            if produto is None:
                raise NotFound(f"Produto {produto_id} não encontrado")
            self._validar_produto_para_venda(produto, quantidade, tz)

            preco_total = produto.preco * quantidade
            valor_total += preco_total
            itens_processados.append((produto, quantidade, preco_total))

        if wallet.saldo < valor_total:
            raise ValidationError(
                "Saldo insuficiente para realizar o pedido. "
                f"Saldo disponível: {wallet.saldo}, valor do pedido: {valor_total}"
            )

        pedido = Pedido(
            aluno_id=data.aluno_id,
            responsavel_id=responsavel_id,
            origem=OrigemPedido.RESPONSAVEL,
            data_referencia=hoje,
            status=StatusPedido.PENDENTE,
            valor_total=valor_total,
            saldo_debitado=Decimal("0.00"),
            observacoes=data.observacoes,
        )
        try:
            async with self._session.begin_nested():
                pedido = await self._pedido_repo.create(pedido)

                for produto, quantidade, preco_total in itens_processados:
                    self._session.add(ItemPedido(
                        pedido_id=pedido.id,
                        produto_id=produto.id,
                        quantidade=quantidade,
                        preco_unitario=produto.preco,
                        preco_total=preco_total,
                    ))
                await self._session.flush()
        except IntegrityError:
            raise Conflict("Já existe um pedido para este aluno hoje")

        for produto, quantidade, _ in itens_processados:
            await self._baixar_estoque(
                produto, quantidade, responsavel_id, f"Pedido #{str(pedido.id)[:8]}",
            )

        self._session.add(PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=None,
            status_novo=StatusPedido.PENDENTE,
            usuario_id=responsavel_id,
            observacao="Pedido criado",
        ))

        pedido = await self._pedido_repo.get_by_id(pedido.id)
        await self._notificar_staff_cantina(
            pedido,
            "Novo pedido recebido",
            f"{aluno.nome}: R$ {valor_total} — aguardando aprovação",
            "criado",
        )
        return pedido

    async def obter_pedido(
        self,
        pedido_id: uuid.UUID,
        responsavel_id: uuid.UUID | None = None,
    ) -> Pedido:
        if responsavel_id is not None:
            pedido = await self._pedido_repo.get_by_aluno_and_responsavel(
                pedido_id, responsavel_id,
            )
        else:
            pedido = await self._pedido_repo.get_by_id(pedido_id)

        if pedido is None:
            raise NotFound("Pedido não encontrado")
        return pedido

    async def listar_pedidos_do_responsavel(
        self,
        responsavel_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        aluno_id: uuid.UUID | None = None,
    ) -> tuple[list[Pedido], int]:
        if aluno_id is not None:
            vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
                aluno_id, responsavel_id,
            )
            if vinculo is None:
                raise Forbidden("Você não possui acesso a este aluno")

        return await self._pedido_repo.listar_por_responsavel(
            responsavel_id=responsavel_id,
            page=page,
            size=size,
            aluno_id=aluno_id,
        )

    async def obter_pedido_do_dia(
        self,
        responsavel_id: uuid.UUID,
        aluno_id: uuid.UUID,
    ) -> Pedido | None:
        vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
            aluno_id, responsavel_id,
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a este aluno")

        config = await self._get_config()
        return await self._pedido_repo.obter_pedido_do_dia(
            responsavel_id=responsavel_id,
            aluno_id=aluno_id,
            hoje=agora_local(config.timezone).date(),
        )

    async def obter_historico_status(
        self, pedido_id: uuid.UUID,
    ) -> list[PedidoStatusHistorico]:
        return await self._pedido_repo.listar_historico_status(pedido_id)

    async def listar_pedidos_cantina(
        self,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Pedido], int]:
        return await self._pedido_repo.listar_todos(
            status=status,
            page=page,
            size=size,
        )

    async def aprovar_pedido(
        self,
        pedido_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> Pedido:
        pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
        if pedido is None:
            raise NotFound("Pedido não encontrado")

        self._validar_transicao_status(pedido.status, StatusPedido.APROVADO)

        mov = await self._financial_service.realizar_consumo_cantina(
            aluno_id=pedido.aluno_id,
            valor=pedido.valor_total,
            descricao=f"Cantina - Pedido #{str(pedido.id)[:8]}",
            usuario_id=usuario_id,
        )

        self._registrar_status(
            pedido, StatusPedido.APROVADO, usuario_id, "Pedido aprovado e saldo debitado",
        )
        pedido.saldo_debitado = pedido.valor_total
        pedido.movimentacao_id = mov.id
        pedido = await self._pedido_repo.update(pedido)
        await self._notificar_responsavel_pedido(
            pedido,
            "Pedido aprovado",
            f"O pedido de {pedido.aluno.nome if pedido.aluno else 'seu filho'} "
            f"foi aprovado. Valor: R$ {pedido.valor_total}",
            "aprovado",
        )

        return pedido

    async def rejeitar_pedido(
        self, pedido_id: uuid.UUID, usuario_id: uuid.UUID | None = None,
    ) -> Pedido:
        pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
        if pedido is None:
            raise NotFound("Pedido não encontrado")

        self._validar_transicao_status(pedido.status, StatusPedido.CANCELADO)

        if pedido.saldo_debitado > Decimal("0.00") and pedido.movimentacao_id is not None:
            await self._financial_service.realizar_estorno_cantina(
                consumo_id=pedido.movimentacao_id,
                usuario_id=usuario_id,
            )

        for item in pedido.itens:
            produto = await self._produto_repo.get_by_id_for_update(item.produto_id)
            if produto is not None:
                await self._devolver_estoque(
                    produto, item.quantidade, usuario_id,
                    f"Rejeição do pedido #{str(pedido.id)[:8]}",
                )

        self._registrar_status(pedido, StatusPedido.CANCELADO, usuario_id, "Pedido rejeitado")
        pedido.cancelado_em = datetime.now(timezone.utc)
        pedido = await self._pedido_repo.update(pedido)
        await self._notificar_responsavel_pedido(
            pedido,
            "Pedido cancelado pela cantina",
            f"O pedido de {pedido.aluno.nome if pedido.aluno else 'seu filho'} foi cancelado.",
            "cancelado",
        )

        return pedido

    async def cancelar_pedido(
        self,
        pedido_id: uuid.UUID,
        usuario_id: uuid.UUID,
        responsavel_id: uuid.UUID | None = None,
    ) -> Pedido:
        if responsavel_id is not None:
            pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
            if pedido is None:
                raise NotFound("Pedido não encontrado")
            if pedido.responsavel_id != responsavel_id:
                raise Forbidden("Você não possui acesso a este pedido")
        else:
            pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
            if pedido is None:
                raise NotFound("Pedido não encontrado")

        self._validar_transicao_status(pedido.status, StatusPedido.CANCELADO)

        await self.validar_config_para_cancelamento(pedido)

        if pedido.saldo_debitado > Decimal("0.00") and pedido.movimentacao_id is not None:
            await self._financial_service.realizar_estorno_cantina(
                consumo_id=pedido.movimentacao_id,
                usuario_id=usuario_id,
            )

        for item in pedido.itens:
            produto = await self._produto_repo.get_by_id_for_update(item.produto_id)
            if produto is not None:
                await self._devolver_estoque(
                    produto, item.quantidade, usuario_id,
                    f"Cancelamento do pedido #{str(pedido.id)[:8]}",
                )

        self._registrar_status(pedido, StatusPedido.CANCELADO, usuario_id, "Pedido cancelado")
        pedido.cancelado_em = datetime.now(timezone.utc)
        pedido = await self._pedido_repo.update(pedido)
        await self._notificar_responsavel_pedido(
            pedido,
            "Pedido cancelado",
            f"O pedido de {pedido.aluno.nome if pedido.aluno else 'seu filho'} foi cancelado.",
            "cancelado",
        )

        return pedido

    async def iniciar_producao(
        self, pedido_id: uuid.UUID, usuario_id: uuid.UUID | None = None,
    ) -> Pedido:
        pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
        if pedido is None:
            raise NotFound("Pedido não encontrado")

        self._validar_transicao_status(pedido.status, StatusPedido.EM_PRODUCAO)

        self._registrar_status(pedido, StatusPedido.EM_PRODUCAO, usuario_id)
        pedido = await self._pedido_repo.update(pedido)

        return pedido

    async def marcar_pronto(
        self, pedido_id: uuid.UUID, usuario_id: uuid.UUID | None = None,
    ) -> Pedido:
        pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
        if pedido is None:
            raise NotFound("Pedido não encontrado")

        self._validar_transicao_status(pedido.status, StatusPedido.PRONTO)

        self._registrar_status(pedido, StatusPedido.PRONTO, usuario_id)
        pedido = await self._pedido_repo.update(pedido)
        await self._notificar_responsavel_pedido(
            pedido,
            "Pedido pronto para retirada",
            f"O pedido de {pedido.aluno.nome if pedido.aluno else 'seu filho'} "
            "está pronto para retirada na cantina.",
            "pronto",
        )

        return pedido

    async def marcar_retirado(
        self, pedido_id: uuid.UUID, usuario_id: uuid.UUID | None = None,
    ) -> Pedido:
        pedido = await self._pedido_repo.get_by_id_for_update(pedido_id)
        if pedido is None:
            raise NotFound("Pedido não encontrado")

        self._validar_transicao_status(pedido.status, StatusPedido.RETIRADO)

        self._registrar_status(pedido, StatusPedido.RETIRADO, usuario_id)
        pedido = await self._pedido_repo.update(pedido)
        await self._notificar_responsavel_pedido(
            pedido,
            "Pedido retirado",
            f"O pedido de {pedido.aluno.nome if pedido.aluno else 'seu filho'} "
            "foi retirado na cantina.",
            "retirado",
        )

        return pedido

    # ── Consumo Direto ────────────────────────────────────────────

    async def registrar_consumo_direto(
        self,
        data: ConsumoDiretoRequest,
        operador_id: uuid.UUID,
    ) -> ConsumoDiretoResponse:
        # Idempotência: o mesmo `idempotency_key` nunca debita duas vezes.
        if data.idempotency_key:
            existente = await self._financial_service._mov_repo.get_by_idempotency_key(
                data.idempotency_key,
            )
            if existente is not None:
                pedido_existente = await self._pedido_repo.get_by_movimentacao_id(existente.id)
                if pedido_existente is not None:
                    return self._consumo_direto_response(pedido_existente, existente)

        config = await self._get_config()
        await self.validar_config_para_pedido()
        tz = config.timezone

        aluno = await self._aluno_repo.get_by_id(data.aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if not aluno.ativo:
            raise ValidationError("Aluno inativo não pode consumir na cantina")
        await self._validar_matricula_ativa(aluno)

        if not aluno.autonomia_cantina:
            raise Forbidden(
                "Este aluno não possui autorização para consumir na cantina. "
                "O responsável deve habilitar a autonomia."
            )

        wallet = await self._financial_service._wallet_repo.get_by_aluno_id_for_update(
            data.aluno_id,
        )
        if wallet is None:
            raise ValidationError("Este aluno não possui carteira ativa")
        self._financial_service._validar_wallet_ativa(wallet)

        valor_total = Decimal("0.00")
        itens_processados: list[tuple[Produto, int, Decimal]] = []

        for produto_id, quantidade in self._agregar_itens(data.itens):
            produto = await self._produto_repo.get_by_id_for_update(produto_id)
            if produto is None:
                raise NotFound(f"Produto {produto_id} não encontrado")
            self._validar_produto_para_venda(produto, quantidade, tz)

            preco_total = produto.preco * quantidade
            valor_total += preco_total
            itens_processados.append((produto, quantidade, preco_total))

        # Débito e baixa de estoque ocorrem na mesma transação.
        mov = await self._financial_service.realizar_consumo_cantina(
            aluno_id=data.aluno_id,
            valor=valor_total,
            descricao="Consumo direto na cantina",
            usuario_id=operador_id,
            idempotency_key=data.idempotency_key,
        )

        for produto, quantidade, _ in itens_processados:
            await self._baixar_estoque(
                produto, quantidade, operador_id, "Consumo direto na cantina",
            )

        pedido = Pedido(
            aluno_id=data.aluno_id,
            responsavel_id=operador_id,
            origem=OrigemPedido.CONSUMO_DIRETO,
            data_referencia=agora_local(tz).date(),
            status=StatusPedido.RETIRADO,
            valor_total=valor_total,
            saldo_debitado=valor_total,
            movimentacao_id=mov.id,
            observacoes="Consumo direto na cantina",
        )
        pedido = await self._pedido_repo.create(pedido)

        self._session.add(PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=None,
            status_novo=StatusPedido.RETIRADO,
            usuario_id=operador_id,
            observacao="Consumo direto registrado no balcão",
        ))

        for produto, quantidade, preco_total in itens_processados:
            self._session.add(ItemPedido(
                pedido_id=pedido.id,
                produto_id=produto.id,
                quantidade=quantidade,
                preco_unitario=produto.preco,
                preco_total=preco_total,
            ))
        await self._session.flush()

        pedido = await self._pedido_repo.get_by_id(pedido.id)
        vinculos = await self._vinculo_repo.get_by_aluno(aluno.id)
        for vinculo in vinculos:
            await self._notificar(
                destinatario_id=vinculo.responsavel_id,
                titulo="Consumo na cantina",
                mensagem=f"{aluno.nome} consumiu R$ {valor_total} na cantina.",
                evento_key=f"consumo-direto:{mov.id}:{vinculo.responsavel_id}",
                pedido_id=pedido.id,
            )

        return self._consumo_direto_response(pedido, mov)

    def _consumo_direto_response(self, pedido: Pedido, mov) -> ConsumoDiretoResponse:
        return ConsumoDiretoResponse(
            consumo_id=pedido.id,
            aluno_id=pedido.aluno_id,
            aluno_nome=pedido.aluno.nome if pedido.aluno else None,
            valor_total=pedido.valor_total,
            saldo_anterior=mov.saldo_anterior,
            saldo_atual=mov.saldo_posterior,
            movimentacao_id=mov.id,
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
        )

    # ── Cancelamento automático (estoque reservado) ───────────────

    async def cancelar_pedidos_pendentes_expirados(self) -> int:
        config = await self._get_config()
        if not config.prazo_pedido_minutos or config.prazo_pedido_minutos <= 0:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.prazo_pedido_minutos)
        pedidos_expirados = await self._pedido_repo.listar_pendentes_expirados(cutoff)

        cancelados = 0
        for pedido in pedidos_expirados:
            pedido_lock = await self._pedido_repo.get_by_id_for_update(pedido.id)
            if pedido_lock is None or pedido_lock.status != StatusPedido.PENDENTE:
                continue

            if pedido_lock.saldo_debitado > Decimal("0.00") or pedido_lock.movimentacao_id is not None:
                continue

            for item in pedido_lock.itens:
                produto = await self._produto_repo.get_by_id_for_update(item.produto_id)
                if produto is not None:
                    await self._devolver_estoque(
                        produto, item.quantidade, None,
                        f"Cancelamento automático do pedido #{str(pedido_lock.id)[:8]}",
                    )

            self._registrar_status(
                pedido_lock, StatusPedido.CANCELADO, None,
                "Cancelado automaticamente — prazo expirado",
            )
            pedido_lock.cancelado_em = datetime.now(timezone.utc)
            pedido_lock.observacoes = (pedido_lock.observacoes or "") + " [Cancelado automaticamente — prazo expirado]"
            await self._pedido_repo.update(pedido_lock)
            await self._notificar_responsavel_pedido(
                pedido_lock,
                "Pedido cancelado automaticamente",
                f"O pedido de {pedido_lock.aluno.nome if pedido_lock.aluno else 'seu filho'} "
                "não foi aprovado a tempo e foi cancelado automaticamente.",
                "cancelado-auto",
            )
            cancelados += 1

        return cancelados

    async def _criar_pedido_de_programacao_manual(
        self, programacao,
    ) -> Pedido:
        config = await self._get_config()
        tz = config.timezone
        hoje = agora_local(tz).date()

        aluno = await self._aluno_repo.get_by_id(programacao.aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if not aluno.ativo:
            raise ValidationError("Aluno inativo não pode receber pedidos")
        await self._validar_matricula_ativa(aluno)

        if await self._pedido_repo.existe_pedido_hoje_para_aluno(programacao.aluno_id, hoje):
            raise Conflict("Já existe um pedido para este aluno hoje")

        wallet = await self._financial_service._wallet_repo.get_by_aluno_id_for_update(
            programacao.aluno_id,
        )
        if wallet is None:
            raise ValidationError("Este aluno não possui carteira ativa")
        self._financial_service._validar_wallet_ativa(wallet)

        valor_total = Decimal("0.00")
        itens_processados: list[tuple[Produto, int, Decimal]] = []

        for produto_id, quantidade in self._agregar_itens(programacao.itens):
            produto = await self._produto_repo.get_by_id_for_update(produto_id)
            if produto is None or not produto.ativo or produto_vencido(produto, tz):
                continue

            if produto.estoque_atual < quantidade:
                raise ValidationError(
                    f"Estoque insuficiente para '{produto.nome}'. "
                    f"Disponível: {produto.estoque_atual}, solicitado: {quantidade}"
                )

            preco_total = produto.preco * quantidade
            valor_total += preco_total
            itens_processados.append((produto, quantidade, preco_total))

        if not itens_processados:
            raise ValidationError("Nenhum produto válido na programação")

        if wallet.saldo < valor_total:
            raise ValidationError("Saldo insuficiente para efetivar esta programação")

        pedido = Pedido(
            aluno_id=programacao.aluno_id,
            responsavel_id=programacao.responsavel_id,
            origem=OrigemPedido.PROGRAMACAO,
            data_referencia=hoje,
            status=StatusPedido.PENDENTE,
            valor_total=valor_total,
            saldo_debitado=Decimal("0.00"),
            observacoes=f"Gerado a partir da programação manual ({programacao.tipo.value})",
        )
        try:
            async with self._session.begin_nested():
                pedido = await self._pedido_repo.create(pedido)

                for produto, quantidade, preco_total in itens_processados:
                    self._session.add(ItemPedido(
                        pedido_id=pedido.id,
                        produto_id=produto.id,
                        quantidade=quantidade,
                        preco_unitario=produto.preco,
                        preco_total=preco_total,
                    ))
                await self._session.flush()
        except IntegrityError:
            raise Conflict("Já existe um pedido para este aluno hoje")

        for produto, quantidade, _ in itens_processados:
            await self._baixar_estoque(
                produto, quantidade, programacao.responsavel_id,
                f"Programação convertida no pedido #{str(pedido.id)[:8]}",
            )

        self._session.add(PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=None,
            status_novo=StatusPedido.PENDENTE,
            usuario_id=programacao.responsavel_id,
            observacao=f"Pedido gerado da programação {programacao.tipo.value}",
        ))

        pedido = await self._pedido_repo.get_by_id(pedido.id)
        await self._notificar_staff_cantina(
            pedido,
            "Novo pedido da programação",
            f"{aluno.nome}: R$ {valor_total} — aguardando aprovação",
            "criado",
        )
        return pedido

    async def obter_dashboard(self, dias: int = 7) -> dict:
        """Return dashboard data for the cantina."""
        from sqlalchemy import select as sa_select, func, and_
        from app.modules.cantina.models import Produto, Pedido, ItemPedido

        config = await self._get_config()
        tz = get_timezone(config.timezone)
        agora = datetime.now(tz)
        hoje = agora.date()
        inicio_local = datetime.combine(hoje, time.min, tzinfo=tz)
        fim_local = datetime.combine(hoje, time.max, tzinfo=tz)
        inicio_hoje = inicio_local.astimezone(timezone.utc)
        fim_hoje = fim_local.astimezone(timezone.utc)
        inicio_periodo = (
            inicio_local - timedelta(days=dias)
        ).astimezone(timezone.utc)

        vendas_query = await self._session.execute(
            sa_select(
                func.coalesce(func.sum(Pedido.valor_total), 0),
                func.count(Pedido.id),
                func.count(func.distinct(Pedido.aluno_id)),
            ).where(
                and_(
                    Pedido.created_at >= inicio_hoje,
                    Pedido.created_at <= fim_hoje,
                    Pedido.status.notin_([StatusPedido.PENDENTE, StatusPedido.CANCELADO]),
                )
            )
        )
        vendas_row = vendas_query.one()
        vendas_do_dia = Decimal(str(vendas_row[0]))
        quantidade_vendas = vendas_row[1]
        alunos_atendidos = vendas_row[2]

        estoque_baixo_query = await self._session.execute(
            sa_select(Produto).where(
                and_(
                    Produto.ativo == True,
                    Produto.estoque_atual <= Produto.estoque_minimo,
                    Produto.estoque_minimo > 0,
                )
            )
        )
        estoque_baixo = list(estoque_baixo_query.scalars().all())

        sem_estoque_query = await self._session.execute(
            sa_select(Produto).where(
                and_(Produto.ativo == True, Produto.estoque_atual == 0)
            )
        )
        sem_estoque = list(sem_estoque_query.scalars().all())

        alertas = []
        for p in sem_estoque:
            alertas.append({
                "produto_id": p.id,
                "produto_nome": p.nome,
                "estoque_atual": p.estoque_atual,
                "estoque_minimo": p.estoque_minimo,
                "tipo": "sem_estoque",
            })
        for p in estoque_baixo:
            if p.estoque_atual > 0:
                alertas.append({
                    "produto_id": p.id,
                    "produto_nome": p.nome,
                    "estoque_atual": p.estoque_atual,
                    "estoque_minimo": p.estoque_minimo,
                    "tipo": "estoque_baixo",
                })

        # Alertas de perecíveis (vencidos e próximos do vencimento).
        pereciveis_query = await self._session.execute(
            sa_select(Produto).where(
                and_(Produto.ativo == True, Produto.perecivel == True)  # noqa: E712
            )
        )
        for p in pereciveis_query.scalars().all():
            dias_restantes = dias_para_vencer(p, config.timezone)
            if dias_restantes is None:
                continue
            if dias_restantes < 0:
                alertas.append({
                    "produto_id": p.id,
                    "produto_nome": p.nome,
                    "estoque_atual": p.estoque_atual,
                    "estoque_minimo": p.estoque_minimo,
                    "tipo": "perecivel_vencido",
                    "dias_para_vencer": dias_restantes,
                })
            elif dias_restantes <= DIAS_PARA_ALERTA_VENCIMENTO:
                alertas.append({
                    "produto_id": p.id,
                    "produto_nome": p.nome,
                    "estoque_atual": p.estoque_atual,
                    "estoque_minimo": p.estoque_minimo,
                    "tipo": "perecivel_proximo_vencimento",
                    "dias_para_vencer": dias_restantes,
                })

        top_produtos_query = await self._session.execute(
            sa_select(
                ItemPedido.produto_id,
                Produto.nome,
                func.sum(ItemPedido.quantidade).label("qtd_vendida"),
                func.sum(ItemPedido.preco_total).label("receita"),
            )
            .join(Pedido, Pedido.id == ItemPedido.pedido_id)
            .join(Produto, Produto.id == ItemPedido.produto_id)
            .where(
                and_(
                    Pedido.created_at >= inicio_periodo,
                    Pedido.status.notin_([StatusPedido.PENDENTE, StatusPedido.CANCELADO]),
                )
            )
            .group_by(ItemPedido.produto_id, Produto.nome)
            .order_by(func.sum(ItemPedido.quantidade).desc())
            .limit(10)
        )
        produtos_mais_vendidos = [
            {
                "produto_id": row[0],
                "produto_nome": row[1],
                "quantidade_vendida": row[2],
                "receita_total": Decimal(str(row[3])),
            }
            for row in top_produtos_query.all()
        ]

        vendas_por_periodo = []
        for i in range(dias, -1, -1):
            dia = hoje - timedelta(days=i)
            inicio_dia = datetime.combine(dia, time.min, tzinfo=tz).astimezone(timezone.utc)
            fim_dia = datetime.combine(dia, time.max, tzinfo=tz).astimezone(timezone.utc)
            result = await self._session.execute(
                sa_select(
                    func.coalesce(func.sum(Pedido.valor_total), 0),
                    func.count(Pedido.id),
                ).where(
                    and_(
                        Pedido.created_at >= inicio_dia,
                        Pedido.created_at <= fim_dia,
                        Pedido.status.notin_([StatusPedido.PENDENTE, StatusPedido.CANCELADO]),
                    )
                )
            )
            row = result.one()
            vendas_por_periodo.append({
                "data": dia.isoformat(),
                "vendas": Decimal(str(row[0])),
                "quantidade": row[1],
            })

        ultimas_query = await self._session.execute(
            sa_select(Pedido)
            .where(
                and_(
                    Pedido.status.notin_([StatusPedido.PENDENTE, StatusPedido.CANCELADO]),
                )
            )
            .order_by(Pedido.created_at.desc())
            .limit(20)
        )
        pedidos_recentes = list(ultimas_query.scalars().all())

        turmas_map: dict[uuid.UUID, str | None] = {}
        aluno_ids = list({p.aluno_id for p in pedidos_recentes})
        if aluno_ids:
            from app.modules.enrollments.repository import MatriculaRepository
            matricula_repo = MatriculaRepository(self._session)
            matriculas_result, _ = await matricula_repo.search(
                aluno_ids=aluno_ids, size=len(aluno_ids),
            )
            for matricula, _nome, codigo in matriculas_result:
                turmas_map[matricula.aluno_id] = codigo

        ultimas_vendas = []
        for p in pedidos_recentes:
            tipo = (
                "consumo_direto"
                if p.origem == OrigemPedido.CONSUMO_DIRETO
                else "pedido"
            )
            produtos_venda = [
                {
                    "nome": item.produto.nome if item.produto else None,
                    "quantidade": item.quantidade,
                }
                for item in p.itens
            ]
            ultimas_vendas.append({
                "id": p.id,
                "aluno_nome": p.aluno.nome if p.aluno else None,
                "aluno_turma": turmas_map.get(p.aluno_id),
                "valor_total": p.valor_total,
                "status": p.status.value if hasattr(p.status, 'value') else p.status,
                "tipo": tipo,
                "produtos": produtos_venda,
                "created_at": p.created_at,
            })

        return {
            "vendas_do_dia": vendas_do_dia,
            "quantidade_vendas": quantidade_vendas,
            "alunos_atendidos": alunos_atendidos,
            "produtos_estoque_baixo": len(alertas),
            "vendas_por_periodo": vendas_por_periodo,
            "produtos_mais_vendidos": produtos_mais_vendidos,
            "alertas_estoque": alertas,
            "ultimas_vendas": ultimas_vendas,
        }
