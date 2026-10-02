from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.core.realtime import RealtimeBroker
from app.database import get_session
from app.modules.communication.schemas import (
    AvisoCreate,
    AvisoDestinatarioResponse,
    AvisoDetalheResponse,
    AvisoMensagemCreate,
    AvisoMensagemResponse,
    AvisoResponse,
    AvisoUpdate,
    AusenciaCreate,
    AusenciaResponse,
    NotificacaoNaoLidasResponse,
    NotificacaoResponse,
    OcorrenciaCreate,
    OcorrenciaDetalheResponse,
    OcorrenciaHistoricoResponse,
    OcorrenciaResponse,
    OcorrenciaStatusUpdate,
    OcorrenciaUpdate,
    PreferenciaNotificacaoListResponse,
    PreferenciaNotificacaoResponse,
    PreferenciaNotificacaoUpdate,
    PublicoDisponivelResponse,
    PushTokenRequest,
    PushTokenResponse,
)
from app.modules.communication.service import (
    AvisoService,
    NotificationService,
    OcorrenciaService,
)
from app.shared.enums import (
    LeituraAviso,
    OrdemAviso,
    Perfil,
    PrioridadeAviso,
    StatusAviso,
    StatusOcorrencia,
    TipoAviso,
    TipoNotificacao,
)
from app.shared.schemas import PaginatedResponse

router = APIRouter(tags=["communication"])

TODOS_PERFIS = (
    Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA,
    Perfil.PROFESSOR, Perfil.RESPONSAVEL, Perfil.CANTINEIRO,
)
REMETENTES_AVISO = (
    Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA, Perfil.PROFESSOR,
)


# ── Ocorrências ────────────────────────────────────────────────────

@router.post(
    "/ocorrencias",
    response_model=OcorrenciaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA, Perfil.PROFESSOR,
    ))],
)
async def criar_ocorrencia(
    body: OcorrenciaCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> OcorrenciaResponse:
    service = OcorrenciaService(session)
    ocorrencia = await service.criar(
        body,
        criado_por=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
    )
    return _ocorrencia_response(ocorrencia)


@router.get(
    "/ocorrencias",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def listar_ocorrencias(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    aluno_id: uuid.UUID | None = Query(None),
    status: StatusOcorrencia | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse:
    service = OcorrenciaService(session)
    items, total = await service.listar(
        current_user_id=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
        aluno_id=aluno_id,
        status=status,
        page=page,
        size=size,
    )
    return PaginatedResponse(
        items=[_ocorrencia_response(o).model_dump() for o in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/ocorrencias/{ocorrencia_id}",
    response_model=OcorrenciaDetalheResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def obter_ocorrencia(
    ocorrencia_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> OcorrenciaDetalheResponse:
    service = OcorrenciaService(session)
    ocorrencia = await service.obter(
        ocorrencia_id,
        current_user_id=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
    )
    historico = await service.listar_historico(
        ocorrencia_id,
        current_user_id=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
    )
    return OcorrenciaDetalheResponse(
        ocorrencia=_ocorrencia_response(ocorrencia),
        historico=[OcorrenciaHistoricoResponse.model_validate(h) for h in historico],
    )


@router.put(
    "/ocorrencias/{ocorrencia_id}",
    response_model=OcorrenciaResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA,
    ))],
)
async def atualizar_ocorrencia(
    ocorrencia_id: uuid.UUID,
    body: OcorrenciaUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> OcorrenciaResponse:
    service = OcorrenciaService(session)
    ocorrencia = await service.atualizar(
        ocorrencia_id,
        body,
        current_user_id=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
    )
    return _ocorrencia_response(ocorrencia)


@router.patch(
    "/ocorrencias/{ocorrencia_id}/status",
    response_model=OcorrenciaResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA,
    ))],
)
async def mudar_status_ocorrencia(
    ocorrencia_id: uuid.UUID,
    body: OcorrenciaStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> OcorrenciaResponse:
    service = OcorrenciaService(session)
    ocorrencia = await service.mudar_status(
        ocorrencia_id,
        body,
        current_user_id=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
    )
    return _ocorrencia_response(ocorrencia)


# ── Avisos ─────────────────────────────────────────────────────────

@router.get(
    "/avisos/publico",
    response_model=PublicoDisponivelResponse,
    dependencies=[Depends(require_roles(*REMETENTES_AVISO))],
)
async def publico_disponivel(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PublicoDisponivelResponse:
    service = AvisoService(session)
    return await service.publico_disponivel(
        uuid.UUID(current_user["sub"]), Perfil(current_user["perfil"]),
    )


@router.post(
    "/avisos",
    response_model=AvisoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(*REMETENTES_AVISO))],
)
async def criar_aviso(
    body: AvisoCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    aviso = await service.criar(
        body, criado_por=usuario_id, perfil=Perfil(current_user["perfil"]),
    )
    return _aviso_response(aviso, lido=False, sou_autor=True)


@router.post(
    "/avisos/ausencia",
    response_model=AusenciaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.RESPONSAVEL))],
)
async def registrar_ausencia(
    body: AusenciaCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AusenciaResponse:
    """Responsável avisa que o filho não vem hoje.

    Única rota de criação de aviso acessível ao responsável, e a única em que ele não
    escolhe destinatários: a secretaria e os professores da turma no dia são resolvidos
    pela grade horária. Idempotente por (aluno, data) — clicar duas vezes não gera dois
    avisos.
    """
    service = AvisoService(session)
    return await service.registrar_ausencia(
        body, responsavel_id=uuid.UUID(current_user["sub"]),
    )


@router.get(
    "/avisos",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def listar_avisos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: StatusAviso | None = Query(None),
    caixa: str | None = Query(None, description="recebidos | enviados | todos | global (admin)"),
    busca: str | None = Query(None, max_length=120),
    prioridade: PrioridadeAviso | None = Query(None, description="baixa | media | alta"),
    tipo: TipoAviso | None = Query(
        None,
        description="geral | comportamento | saude | administrativo | ausencia",
    ),
    data_inicio: date | None = Query(None, description="Data inicial de publicação (inclusive)"),
    data_fim: date | None = Query(None, description="Data final de publicação (inclusive)"),
    turma_id: uuid.UUID | None = Query(None),
    aluno_id: uuid.UUID | None = Query(None, description="Restrito aos filhos, para responsável"),
    leitura: LeituraAviso = Query(LeituraAviso.TODOS, description="todos | nao_lidos | lidos"),
    ordem: OrdemAviso = Query(OrdemAviso.RECENTES, description="recentes | antigos | prioridade"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    items, total, meus = await service.listar(
        current_user_id=usuario_id,
        perfil=perfil,
        caixa=caixa,
        status=status,
        busca=busca,
        prioridade=prioridade,
        tipo=tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        turma_id=turma_id,
        aluno_id=aluno_id,
        leitura=leitura,
        ordem=ordem,
        page=page,
        size=size,
    )
    return PaginatedResponse(
        items=[
            _aviso_response(
                a,
                lido=meus.get(a.id).lido_em is not None if meus.get(a.id) else False,
                sou_autor=a.criado_por == usuario_id,
            ).model_dump()
            for a in items
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/avisos/{aviso_id}",
    response_model=AvisoDetalheResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def obter_aviso(
    aviso_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoDetalheResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    aviso = await service.obter(aviso_id, current_user_id=usuario_id, perfil=perfil)
    sou_autor = aviso.criado_por == usuario_id
    destinatario = await service.obter_destinatario(aviso_id, usuario_id)

    pode_gerenciar = perfil in (Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA) or sou_autor
    if pode_gerenciar:
        destinatarios = await service.listar_destinatarios(aviso_id, usuario_id, perfil)
        estatisticas = service.estatisticas(destinatarios)
        destinatarios_response = [
            _destinatario_response(d) for d in destinatarios
        ]
    else:
        destinatarios_response = []
        estatisticas = service.estatisticas(aviso.destinatarios or [])

    mensagens = await service.listar_mensagens(aviso_id, usuario_id, perfil)
    pode_responder = (
        aviso.permite_respostas
        and aviso.status == StatusAviso.PUBLICADO
        and (sou_autor or destinatario is not None)
    )

    return AvisoDetalheResponse(
        aviso=_aviso_response(
            aviso,
            lido=destinatario.lido_em is not None if destinatario else False,
            sou_autor=sou_autor,
        ),
        destinatarios=destinatarios_response,
        estatisticas=estatisticas,
        pode_responder=pode_responder,
        total_mensagens=len(mensagens),
    )


@router.put(
    "/avisos/{aviso_id}",
    response_model=AvisoResponse,
    dependencies=[Depends(require_roles(*REMETENTES_AVISO))],
)
async def atualizar_aviso(
    aviso_id: uuid.UUID,
    body: AvisoUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    aviso = await service.atualizar(
        aviso_id, body,
        current_user_id=usuario_id,
        perfil=Perfil(current_user["perfil"]),
    )
    return _aviso_response(aviso, lido=False, sou_autor=aviso.criado_por == usuario_id)


@router.patch(
    "/avisos/{aviso_id}/arquivar",
    response_model=AvisoResponse,
    dependencies=[Depends(require_roles(*REMETENTES_AVISO))],
)
async def arquivar_aviso(
    aviso_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    aviso = await service.arquivar(
        aviso_id,
        current_user_id=usuario_id,
        perfil=Perfil(current_user["perfil"]),
    )
    return _aviso_response(aviso, lido=False, sou_autor=aviso.criado_por == usuario_id)


@router.post(
    "/avisos/{aviso_id}/ler",
    response_model=AvisoDestinatarioResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def marcar_aviso_lido(
    aviso_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoDestinatarioResponse:
    service = AvisoService(session)
    registro = await service.marcar_lido(
        aviso_id, usuario_id=uuid.UUID(current_user["sub"]),
    )
    return _destinatario_response(registro)


@router.get(
    "/avisos/{aviso_id}/destinatarios",
    response_model=list[AvisoDestinatarioResponse],
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def listar_destinatarios_aviso(
    aviso_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[AvisoDestinatarioResponse]:
    service = AvisoService(session)
    destinatarios = await service.listar_destinatarios(
        aviso_id,
        current_user_id=uuid.UUID(current_user["sub"]),
        perfil=Perfil(current_user["perfil"]),
    )
    return [_destinatario_response(d) for d in destinatarios]


@router.get(
    "/avisos/{aviso_id}/mensagens",
    response_model=list[AvisoMensagemResponse],
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def listar_mensagens_aviso(
    aviso_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[AvisoMensagemResponse]:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    mensagens = await service.listar_mensagens(
        aviso_id,
        current_user_id=usuario_id,
        perfil=Perfil(current_user["perfil"]),
    )
    return [_mensagem_response(m, usuario_id) for m in mensagens]


@router.post(
    "/avisos/{aviso_id}/respostas",
    response_model=AvisoMensagemResponse,
    status_code=201,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def responder_aviso(
    aviso_id: uuid.UUID,
    body: AvisoMensagemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoMensagemResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    mensagem = await service.responder(
        aviso_id,
        body,
        autor_id=usuario_id,
        perfil=Perfil(current_user["perfil"]),
    )
    return _mensagem_response(mensagem, usuario_id)


@router.patch(
    "/avisos/{aviso_id}/mensagens/{mensagem_id}/ler",
    response_model=AvisoMensagemResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def marcar_mensagem_lida(
    aviso_id: uuid.UUID,
    mensagem_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AvisoMensagemResponse:
    service = AvisoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    mensagem = await service.marcar_mensagem_lida(aviso_id, mensagem_id, usuario_id)
    return _mensagem_response(mensagem, usuario_id)


# ── Notificações ───────────────────────────────────────────────────

@router.get(
    "/notificacoes",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def listar_notificacoes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    apenas_nao_lidas: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse:
    service = NotificationService(session)
    items, total = await service.listar(
        destinatario_id=uuid.UUID(current_user["sub"]),
        apenas_nao_lidas=apenas_nao_lidas,
        page=page,
        size=size,
    )
    return PaginatedResponse(
        items=[NotificacaoResponse.model_validate(n).model_dump() for n in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/notificacoes/nao-lidas",
    response_model=NotificacaoNaoLidasResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def contar_notificacoes_nao_lidas(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> NotificacaoNaoLidasResponse:
    service = NotificationService(session)
    total = await service.contar_nao_lidas(uuid.UUID(current_user["sub"]))
    return NotificacaoNaoLidasResponse(total=total)


@router.get(
    "/notificacoes/stream",
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def stream_notificacoes(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Server-Sent Events de notificações do usuário autenticado."""
    usuario_id = uuid.UUID(current_user["sub"])

    async def gerador():
        fila = await RealtimeBroker.subscribe(usuario_id)
        try:
            yield "retry: 5000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evento = await asyncio.wait_for(fila.get(), timeout=20)
                    yield f"data: {json.dumps(evento, ensure_ascii=False, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            await RealtimeBroker.unsubscribe(usuario_id, fila)

    return StreamingResponse(
        gerador(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/notificacoes/push-tokens",
    response_model=PushTokenResponse,
    status_code=201,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def registrar_push_token(
    body: PushTokenRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PushTokenResponse:
    service = NotificationService(session)
    registro = await service.registrar_push_token(
        usuario_id=uuid.UUID(current_user["sub"]),
        token=body.token,
        plataforma=body.plataforma,
    )
    return PushTokenResponse.model_validate(registro)


@router.delete(
    "/notificacoes/push-tokens",
    status_code=204,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def remover_push_token(
    token: str = Query(..., min_length=8, max_length=255),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> None:
    service = NotificationService(session)
    await service.remover_push_token(uuid.UUID(current_user["sub"]), token)


# ── Preferências de notificação ─────────────────────────────────────

@router.get(
    "/notificacoes/preferencias",
    response_model=PreferenciaNotificacaoListResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def listar_preferencias_notificacao(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PreferenciaNotificacaoListResponse:
    """Preferências de canal do usuário autenticado.

    Devolve todos os tipos de `TipoNotificacao`, com `false` nos que ainda não
    foram configurados — o e-mail é opt-in e nada é enviado por padrão.
    """
    service = NotificationService(session)
    salvo = await service.obter_preferencias(uuid.UUID(current_user["sub"]))
    return PreferenciaNotificacaoListResponse(
        preferencias={tipo: salvo.get(tipo, False) for tipo in TipoNotificacao},
    )


@router.put(
    "/notificacoes/preferencias/{tipo}",
    response_model=PreferenciaNotificacaoResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def definir_preferencia_notificacao(
    tipo: TipoNotificacao,
    body: PreferenciaNotificacaoUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PreferenciaNotificacaoResponse:
    service = NotificationService(session)
    preferencia = await service.definir_preferencia(
        usuario_id=uuid.UUID(current_user["sub"]),
        tipo=tipo,
        email=body.email,
    )
    return PreferenciaNotificacaoResponse.model_validate(preferencia)


@router.patch(
    "/notificacoes/{notificacao_id}/ler",
    response_model=NotificacaoResponse,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def marcar_notificacao_lida(
    notificacao_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> NotificacaoResponse:
    service = NotificationService(session)
    notificacao = await service.marcar_lida(
        notificacao_id, destinatario_id=uuid.UUID(current_user["sub"]),
    )
    return NotificacaoResponse.model_validate(notificacao)


@router.patch(
    "/notificacoes/ler-todas",
    response_model=dict,
    dependencies=[Depends(require_roles(*TODOS_PERFIS))],
)
async def marcar_todas_notificacoes_lidas(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    service = NotificationService(session)
    marcadas = await service.marcar_todas_lidas(uuid.UUID(current_user["sub"]))
    return {"marcadas": marcadas}


# ── Helpers de serialização ────────────────────────────────────────

def _ocorrencia_response(o) -> OcorrenciaResponse:
    return OcorrenciaResponse(
        id=o.id,
        aluno_id=o.aluno_id,
        aluno_nome=o.aluno.nome if o.aluno else None,
        turma_id=o.turma_id,
        turma_codigo=o.turma.codigo if o.turma else None,
        titulo=o.titulo,
        descricao=o.descricao,
        tipo=o.tipo,
        severidade=o.severidade,
        status=o.status,
        criado_por=o.criado_por,
        responsavel_id=o.responsavel_id,
        resolvida_em=o.resolvida_em,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _aviso_response(a, lido: bool = False, sou_autor: bool = False) -> AvisoResponse:
    destinatarios = a.destinatarios or []
    lidos = sum(1 for d in destinatarios if d.lido_em is not None)
    return AvisoResponse(
        id=a.id,
        titulo=a.titulo,
        mensagem=a.mensagem,
        tipo=a.tipo,
        prioridade=a.prioridade,
        permite_respostas=a.permite_respostas,
        destinatario_aluno_id=a.destinatario_aluno_id,
        destinatario_turma_id=a.destinatario_turma_id,
        status=a.status,
        criado_por=a.criado_por,
        autor_nome=a.criador.nome if a.criador else None,
        autor_perfil=a.criador.perfil.value if a.criador and a.criador.perfil else None,
        publicado_em=a.publicado_em,
        created_at=a.created_at,
        lido_por_mim=lido,
        sou_autor=sou_autor,
        total_destinatarios=len(destinatarios),
        lidos=lidos,
        nao_lidos=len(destinatarios) - lidos,
    )


def _destinatario_response(d) -> AvisoDestinatarioResponse:
    return AvisoDestinatarioResponse(
        id=d.id,
        aviso_id=d.aviso_id,
        usuario_id=d.usuario_id,
        usuario_nome=d.usuario.nome if d.usuario else None,
        usuario_perfil=(
            d.usuario.perfil.value if d.usuario and d.usuario.perfil else None
        ),
        aluno_id=d.aluno_id,
        aluno_nome=d.aluno.nome if d.aluno else None,
        lido_em=d.lido_em,
        escalado_em=d.escalado_em,
        created_at=d.created_at,
    )


def _mensagem_response(m, usuario_id: uuid.UUID) -> AvisoMensagemResponse:
    return AvisoMensagemResponse(
        id=m.id,
        aviso_id=m.aviso_id,
        autor_id=m.autor_id,
        autor_nome=m.autor.nome if m.autor else None,
        autor_perfil=m.autor.perfil.value if m.autor and m.autor.perfil else None,
        destinatario_id=m.destinatario_id,
        destinatario_nome=m.destinatario.nome if m.destinatario else None,
        conteudo=m.conteudo,
        lida_em=m.lida_em,
        created_at=m.created_at,
        enviada_por_mim=m.autor_id == usuario_id,
    )
