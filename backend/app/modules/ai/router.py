"""Router do assistente de IA local "Atena".

BLOCO 2 (Fases 3-5) expõe o chat real, o streaming e o histórico. O pipeline
de segurança continua sendo o do Bloco 1 e não é afrouxado aqui:

    JWT -> perfil -> allowlist -> intenção -> escopo -> contexto -> LLM
                                                             -> guardrails

Regra que vale para todos os endpoints deste módulo: nenhum consulta o
PostgreSQL sem escopo, e nenhum aceita um `usuario_id` da requisição — o
usuário é SEMPRE o do token. O `conversa_id` do cliente entra no filtro junto
com o dono, e um id de outra pessoa devolve 404 (não 403: 403 confirmaria que
o id existe).

ATENÇÃO ao `prefix="/ai"`: sem ele, este router registraria `/api/v1/health` e
COLIDIRIA com o health check do SGE — neste FastAPI a colisão faz a rota
anterior sumir do roteamento, derrubando o healthcheck do container Docker.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limit import chave_por_usuario, limiter
from app.database import get_session
from app.modules.ai import mensagens as textos
from app.modules.ai.context import intencoes_do_perfil, verificar_cobertura
from app.modules.ai.history_repository import ConversaRepository, MensagemRepository
from app.modules.ai.history_service import HistoryService
from app.modules.ai.intent import sugestoes_para
from app.modules.ai.service import AIService, EventoStream, RespostaDiretaError
from app.shared.enums import PapelMensagemIA, Perfil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Cobertura catálogo↔builder verificada no boot: se alguém registrar uma
# intenção sem builder (ou o contrário), o processo não sobe em produção com a
# falha silenciosa "não tenho acesso a essa informação".
verificar_cobertura()


def _usuario_id(current_user: dict) -> uuid.UUID:
    return uuid.UUID(str(current_user["sub"]))


def _perfil(current_user: dict) -> Perfil:
    return Perfil(current_user.get("perfil", ""))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Entrada do chat (idêntica para o modo normal e o streaming)."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Pergunta em linguagem natural, em português.",
    )
    aluno_selecionado_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Aluno selecionado ativamente no app (web/mobile). Só é usado se "
            "pertencer ao escopo do usuário — a validação é do backend."
        ),
    )
    conversa_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Conversa existente para continuar. Se for de outra pessoa, a "
            "resposta é 404 e nada é gravado."
        ),
    )
    salvar: bool = Field(
        default=True,
        description="false responde sem criar/gravar conversa (modo anônimo).",
    )


class FonteIA(BaseModel):
    intencao: str | None = None
    fatos_utilizados: int = 0
    modelo: str = ""
    latencia_ms: int = 0
    tokens: int = 0
    alertas_guardrails: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    resposta: str
    codigo: str = "ok"
    fonte: FonteIA = Field(default_factory=FonteIA)
    sugestoes: list[str] = Field(default_factory=list)
    conversa_id: uuid.UUID | None = None
    mensagem_id: uuid.UUID | None = None


class MensagemOut(BaseModel):
    id: uuid.UUID
    papel: PapelMensagemIA
    conteudo: str
    intencao: str | None = None
    codigo: str | None = None
    criado_em: str


class ConversaOut(BaseModel):
    id: uuid.UUID
    titulo: str | None = None
    criada_em: str
    atualizada_em: str
    total_mensagens: int = 0


class ConversaComMensagensOut(BaseModel):
    conversa: ConversaOut
    mensagens: list[MensagemOut]


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------


@router.get("/health", response_model=dict)
async def health_ia(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Diagnóstico do módulo de IA.

    Autenticado de propósito: revela versão do modelo, latência e estado do
    circuit breaker — informações de infraestrutura que não devem ser públicas.

    IMPORTANTE: este endpoint é INDEPENDENTE de `/api/v1/health`, que nunca
    verifica a IA. Se o Ollama cair, `/health` continua 200 e este endpoint
    responde `unavailable`.
    """
    saude = await AIService(session).health()
    perfil = _perfil(current_user)
    return {
        **saude,
        # O que ESTE usuário pode perguntar (a allowlist é por perfil).
        "intencoes_disponiveis": intencoes_do_perfil(perfil),
        "sugestoes": sugestoes_para(perfil),
        "streaming": True,
        "historico": {
            "turnos_no_prompt": settings.AI_HISTORY_TURNS,
            "max_chars_no_prompt": settings.AI_HISTORY_MAX_CHARS,
            "max_conversas": settings.AI_HISTORY_LIST_LIMIT,
        },
    }


# ---------------------------------------------------------------------------
# Barreira anti-vazamento (último ponto antes do cliente)
# ---------------------------------------------------------------------------


def _texto_ao_usuario(resposta) -> str:
    """Texto que sai do backend, já sem jargão técnico.

    Só recusas e mensagens de falha passam por aqui. A resposta de conteúdo
    (`codigo == "ok"`) NÃO é filtrada: o que ela diz é redigido pelo modelo a
    partir dos fatos autorizados, e trocar o texto inteiro por cair numa palavra
    quebraria a funcionalidade. Nesse caminho, quem protege é o `guardrails.py`,
    que conhece o contexto e distingue dado legítimo de vazamento.
    """
    if resposta.codigo == "ok":
        return resposta.resposta
    return textos.sem_tecnologia(resposta.resposta)


def _erro_ao_usuario(texto: str) -> str:
    """Frame de erro SSE nunca carrega detalhe de infraestrutura."""
    return textos.sem_tecnologia(texto)


# ---------------------------------------------------------------------------
# Helpers de conversa
# ---------------------------------------------------------------------------


async def _preparar_conversa(
    history: HistoryService,
    usuario_id: uuid.UUID,
    conversa_id: uuid.UUID | None,
    salvar: bool,
    *,
    commit_imediato: bool = False,
) -> tuple[uuid.UUID | None, list[dict[str, str]]]:
    """Resolve/cria a conversa e devolve `(conversa_id, historico_para_prompt)`.

    Devolver `conversa_id=None` com `salvar=False` é o modo anônimo: nem cria
    conversa nem consulta histórico.
    """
    if not salvar:
        return None, []

    conversa = await history.obter_ou_criar(usuario_id, conversa_id)
    if conversa is None:
        # id de conversa de outra pessoa: 404 indistinguível de "não existe".
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada.",
        )

    # Captura o id ANTES de qualquer commit: depois do commit o objeto expira e
    # ler atributo dele dispararia um SELECT implícito (inválido em async).
    novo_id = conversa.id
    if commit_imediato:
        # No streaming, grava a conversa já: assim o cliente pode continuar a
        # conversa pelo `meta` mesmo que a inferência falhe, e a transação não
        # fica aberta segurando um INSERT durante todo o stream.
        await history.commit()

    historico = (await history.historico_para_prompt(novo_id)).mensagens
    return novo_id, historico


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.AI_RATE_LIMIT, key_func=chave_por_usuario)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """Chat não-streaming (Fase 3).

    Mesma cadeia de segurança do Bloco 1, agora exposta por HTTP. Se o Ollama
    cair, a exceção de domínio vira 503/429 limpos e o resto do SGE segue no ar.

    Rate limit `AI_RATE_LIMIT` por USUÁRIO (`chave_por_usuario`): o recurso
    protegido é a única vaga de inferência do Ollama, e ela é compartilhada por
    toda a escola. Limitar por IP puniria os usuários honestos que dividem proxy
    com o resto da rede.
    """
    usuario_id = _usuario_id(current_user)
    perfil = _perfil(current_user)
    history = HistoryService(session)

    conversa_id, historico = await _preparar_conversa(
        history, usuario_id, body.conversa_id, body.salvar,
    )

    # `RespostaDiretaError` é a forma interna de dizer "recusa pronta" (sem
    # inferência). Ela NÃO pode escapar para o handler de exceção: viraria 500
    # numa pergunta que a Atena sabe responder de graça. Vira resposta normal,
    # com o mesmo formato de sempre.
    try:
        resultado = await AIService(session).responder(
            body.message,
            usuario_id=usuario_id,
            perfil=perfil,
            nome_usuario=current_user.get("nome", ""),
            aluno_selecionado_id=body.aluno_selecionado_id,
            historico=historico,
        )
    except RespostaDiretaError as direta:
        resultado = direta.resposta

    mensagem_id = None
    if conversa_id is not None:
        _, m_assistente = await history.registrar_turno_do_usuario(
            conversa_id, usuario_id, body.message, resultado.resposta,
            intencao=resultado.intencao, codigo=resultado.codigo,
        )
        await history.commit()
        mensagem_id = m_assistente.id

    return ChatResponse(
        resposta=_texto_ao_usuario(resultado),
        codigo=resultado.codigo,
        fonte=FonteIA(
            intencao=resultado.intencao,
            fatos_utilizados=resultado.fatos_utilizados,
            modelo=resultado.modelo,
            latencia_ms=resultado.latencia_ms,
            tokens=resultado.tokens_prompt + resultado.tokens_completion,
            alertas_guardrails=resultado.alertas_guardrails,
        ),
        sugestoes=resultado.sugestoes,
        conversa_id=conversa_id,
        mensagem_id=mensagem_id,
    )


@router.post("/chat/stream")
@limiter.limit(settings.AI_RATE_LIMIT, key_func=chave_por_usuario)
async def chat_stream(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Chat em streaming SSE (Fase 4).

    Protocolo (um JSON por frame, sempre em `data:`):

    - `{"tipo": "meta", "conversa_id": "..."}`  só quando a conversa é salva;
    - `{"tipo": "delta", "texto": "..."}`        pedaço novo;
    - `{"tipo": "done",  "resposta": {...}}`     final, pós-guardrails;
    - `{"tipo": "erro",  "erro": "...", "parcial": "..."}`  falhou no meio.

    O `done` traz o texto pós-guardrail como campo AUTORITATIVO. O cliente
    desenha o que chega nos deltas para dar sensação de progresso e, no `done`,
    substitui pelo texto final quando ele for diferente — é o que acontece se
    um número inventado foi cortado.

    Cancelamento: se o cliente desconectar, o gerador é fechado, o `finally`
    do cliente libera o semáforo e a stream do httpx é abortada — a
    inferência não fica presa segurando a única vaga de concorrência.
    """
    usuario_id = _usuario_id(current_user)
    perfil = _perfil(current_user)
    history = HistoryService(session)

    # Tudo que precisa do banco acontece ANTES do primeiro byte, para que um
    # erro de autorização saia como HTTP (404) e não como frame SSE de erro.
    conversa_id, historico = await _preparar_conversa(
        history, usuario_id, body.conversa_id, body.salvar,
        commit_imediato=True,
    )

    async def gerar() -> AsyncIterator[str]:
        if conversa_id is not None:
            yield _frame_meta(conversa_id)

        try:
            async for evento in AIService(session).stream(
                body.message,
                usuario_id=usuario_id,
                perfil=perfil,
                nome_usuario=current_user.get("nome", ""),
                aluno_selecionado_id=body.aluno_selecionado_id,
                historico=historico,
            ):
                if evento.tipo == "done" and evento.resposta is not None:
                    # Mesma barreira do `/chat`: uma recusa nunca sai com
                    # jargão. Aplicado ANTES de gravar, para que o histórico
                    # guarde exatamente o texto que o usuário leu.
                    final = replace(
                        evento.resposta,
                        resposta=_texto_ao_usuario(evento.resposta),
                    )
                    # Persiste ANTES de mandar o `done`: se o banco cair, o
                    # cliente recebe `erro` em vez de um "final" que não existe.
                    if conversa_id is not None:
                        await history.registrar_turno_do_usuario(
                            conversa_id, usuario_id, body.message,
                            final.resposta,
                            intencao=final.intencao,
                            codigo=final.codigo,
                        )
                        await history.commit()
                    yield _frame(EventoStream("done", resposta=final))
                    return

                if evento.tipo == "erro":
                    if conversa_id is not None:
                        await history.registrar_turno_do_usuario(
                            conversa_id, usuario_id, body.message, evento.erro,
                            codigo="ia_indisponivel",
                        )
                        await history.commit()
                    yield _frame(
                        EventoStream(
                            "erro", erro=_erro_ao_usuario(evento.erro),
                            parcial=evento.parcial,
                        )
                    )
                    return

                yield _frame(evento)
        except Exception:  # noqa: BLE001
            # Nunca deixa o stream morrer em silêncio: o cliente sempre recebe
            # um frame final, e o log preserva a causa.
            logger.exception("AI: falha inesperada no stream SSE")
            yield _frame(EventoStream("erro", erro=textos.FALHA_INTERNA))

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "Connection": "keep-alive",
            # Sem buffer intermediário: sem isso, o nginx/Uvicorn pode segurar
            # os chunks e o efeito "progressivo" some.
            "X-Accel-Buffering": "no",
        },
    )


def _frame_meta(conversa_id: uuid.UUID) -> str:
    return f"data: {json.dumps({'tipo': 'meta', 'conversa_id': str(conversa_id)})}\n\n"


def _frame(evento: EventoStream) -> str:
    """Serializa um evento no formato SSE. Sempre um frame por evento."""
    if evento.tipo == "delta":
        payload = {"tipo": "delta", "texto": evento.texto}
    elif evento.tipo == "erro":
        payload = {"tipo": "erro", "erro": evento.erro, "parcial": evento.parcial}
    else:
        r = evento.resposta
        payload = {
            "tipo": "done",
            "resposta": {
                "resposta": r.resposta,
                "codigo": r.codigo,
                "intencao": r.intencao,
                "fatos_utilizados": r.fatos_utilizados,
                "modelo": r.modelo,
                "perfil": r.perfil,
                "latencia_ms": r.latencia_ms,
                "alertas_guardrails": r.alertas_guardrails,
                "sugestoes": r.sugestoes,
            },
        }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Histórico (Fase 5)
# ---------------------------------------------------------------------------


def _msg_out(m) -> MensagemOut:
    return MensagemOut(
        id=m.id,
        papel=m.papel,
        conteudo=m.conteudo,
        intencao=m.intencao,
        codigo=m.codigo,
        criado_em=m.criado_em.isoformat(),
    )


@router.get("/conversas", response_model=list[ConversaOut])
async def listar_conversas(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ConversaOut]:
    """Conversas do usuário autenticado. Nunca lista as de outra pessoa."""
    usuario_id = _usuario_id(current_user)
    repo = ConversaRepository(session)
    conversas = await repo.listar(usuario_id, settings.AI_HISTORY_LIST_LIMIT)
    return [
        ConversaOut(
            id=c.id,
            titulo=c.titulo,
            criada_em=c.criada_em.isoformat(),
            atualizada_em=c.atualizada_em.isoformat(),
            total_mensagens=await repo.contar_mensagens(c.id, usuario_id),
        )
        for c in conversas
    ]


@router.post("/conversas", response_model=ConversaOut, status_code=201)
async def criar_conversa(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConversaOut:
    usuario_id = _usuario_id(current_user)
    conversa = await ConversaRepository(session).criar(usuario_id)
    await session.commit()
    return ConversaOut(
        id=conversa.id,
        titulo=conversa.titulo,
        criada_em=conversa.criada_em.isoformat(),
        atualizada_em=conversa.atualizada_em.isoformat(),
    )


@router.get("/conversas/{conversa_id}", response_model=ConversaComMensagensOut)
async def obter_conversa(
    conversa_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConversaComMensagensOut:
    """Conversa + mensagens. 404 se o id não for do usuário (anti-IDOR)."""
    usuario_id = _usuario_id(current_user)
    repo = ConversaRepository(session)
    conversa = await repo.obter(conversa_id, usuario_id)
    if conversa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.",
        )
    mensagens = await MensagemRepository(session).listar(conversa_id)
    return ConversaComMensagensOut(
        conversa=ConversaOut(
            id=conversa.id,
            titulo=conversa.titulo,
            criada_em=conversa.criada_em.isoformat(),
            atualizada_em=conversa.atualizada_em.isoformat(),
            total_mensagens=len(mensagens),
        ),
        mensagens=[_msg_out(m) for m in mensagens],
    )


@router.delete("/conversas/{conversa_id}", status_code=204)
async def excluir_conversa(
    conversa_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Exclusão dura. Mensagens caem por CASCADE. 404 se não for do usuário."""
    usuario_id = _usuario_id(current_user)
    if not await ConversaRepository(session).excluir(conversa_id, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.",
        )
    await session.commit()
