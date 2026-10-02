"""Serviço de orquestração do assistente Atena.

Ordem das etapas (invariante de segurança — não inverter):

    1. autenticação            (feito na dependency do router: get_current_user)
    2. perfil                  (do JWT, já validado)
    3. allowlist do perfil     (intent.classificar só enxerga o que é permitido)
    4. classificação           (determinística, em código)
    5. escopo                  (context builder resolve filho/turma authorized)
    6. contexto mínimo         (fatores formatados e truncados)
    7. inferência              (Ollama, sem ferramentas, sem escrita)
    8. guardrails              (filtro mecânico da resposta)
    9. resposta

O LLM entra apenas no passo 7. Ele não escolhe tabela, coluna, filtro,
usuário, aluno nem turma, e não executa nada.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.ai import mensagens as textos
from app.modules.ai.context import construir_contexto
from app.modules.ai.context.base import ResultadoContexto
from app.modules.ai.conversa import classificar_conversa
from app.modules.ai.exceptions import (
    AIException,
    ContextoVazioErro,
    EscopoNaoResolvidoErro,
    IntencaoNaoPermitidaErro,
    IntencaoNaoReconhecidaErro,
)
from app.modules.ai.guardrails import validar_resposta
from app.modules.ai.intent import ResultadoIntencao, classificar, sugestoes_para
from app.modules.ai.ollama_client import OllamaClient, get_client
from app.modules.ai.prompt import montar_mensagens
from app.shared.enums import Perfil

logger = logging.getLogger(__name__)


@dataclass
class RespostaIA:
    """Resposta canônica do assistente. Mesmo formato em sucesso e em recusa."""

    resposta: str
    intencao: str | None = None
    codigo: str = "ok"
    modelo: str = ""
    perfil: str = ""
    latencia_ms: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    fatos_utilizados: int = 0
    # Metadados de auditoria (sem conteúdo de dados pessoais).
    alunos_autorizados: list[uuid.UUID] = field(default_factory=list)
    alertas_guardrails: list[str] = field(default_factory=list)
    sugestoes: list[str] = field(default_factory=list)


class RespostaDiretaError(Exception):
    """Sinaliza que a resposta é um texto pronto (recusa), sem inferência.

    Definida ANTES de `AIService` porque as etapas o levantam: recusar é o
    caminho normal, não um caso exceptional.
    """

    def __init__(self, resposta: RespostaIA) -> None:
        super().__init__(resposta.resposta)
        self.resposta = resposta


@dataclass
class EventoStream:
    """Evento do fluxo progressivo.

    `tipo` é o contrato com o router SSE e, através dele, com web e mobile:

    - `delta`: mais um pedaço de texto para desenhar na tela;
    - `done`:  resposta final, pós-guardrails, com os metadados;
    - `erro`:  falhou no meio (o texto parcial vai em `parcial`).

    O `done` carrega o texto AUTORITATIVO. O cliente deve desenhá-lo quando
    ele diferir do que foi acumulando nos deltas — é o que acontece quando um
    guardrail corta um número inventado. Ver `guardrails.py`.
    """

    tipo: str
    texto: str = ""
    resposta: RespostaIA | None = None
    erro: str = ""
    parcial: str = ""


class AIService:
    def __init__(self, session: AsyncSession, client: OllamaClient | None = None) -> None:
        self._session = session
        # Cliente compartilhado do processo: o circuit breaker precisa
        # compartilhar as falhas entre requisições para ter efeito.
        self._client = client or get_client()

    async def responder(
        self,
        mensagem: str,
        *,
        usuario_id: uuid.UUID,
        perfil: Perfil,
        nome_usuario: str = "",
        aluno_selecionado_id: uuid.UUID | None = None,
        historico: list[dict[str, str]] | None = None,
    ) -> RespostaIA:
        inicio = time.monotonic()

        # 2.5) cortesia ("olá", "obrigado"): resolvida sem banco e sem modelo.
        self._cortesia(mensagem, perfil)

        # 3 + 4) allowlist do perfil e classificação determinística.
        resultado = self._classificar(mensagem, perfil)

        # 5 + 6) escopo e contexto mínimo.
        contexto = await self._montar_contexto(
            resultado, usuario_id, perfil, aluno_selecionado_id,
        )

        return await self._inferir(
            resultado, contexto, perfil, nome_usuario, inicio, historico,
        )

    # ------------------------------------------------------------------
    # Etapas isoladas (facilitam teste unitário e auditoria)
    # ------------------------------------------------------------------
    def _cortesia(self, mensagem: str, perfil: Perfil) -> None:
        """Corta a cadeia inteira quando a mensagem é só cortesia.

        Vem ANTES da classificação de propósito: uma saudação não é uma
        intenção, e tratá-la como tal só criaria duas formas de gastar uma
        inferência para escrever "Olá!". Aqui não há sessão, não há consulta e
        não há modelo — a resposta é texto pronto, em milissegundos.

        A exceção `RespostaDiretaError` é o mesmo sinal usado pelas recusas: o
        contrato com o router (gravar histórico, devolver `codigo`) continua
        idêntico, e o turno de "olá" aparece no histórico como qualquer outro.
        """
        conversa = classificar_conversa(mensagem)
        if conversa is None:
            return
        categoria, resposta, sugestoes = conversa
        logger.info("AI: conversa (%s) respondida sem inferência", categoria)
        raise RespostaDiretaError(
            RespostaIA(
                resposta=resposta,
                intencao=f"conversa_{categoria}",
                codigo="ok",
                perfil=perfil.value,
                latencia_ms=0,
                # 0 fatos = a auditoria registra que nada do banco foi lido.
                fatos_utilizados=0,
                sugestoes=list(sugestoes),
            )
        )

    def _classificar(self, mensagem: str, perfil: Perfil) -> ResultadoIntencao:
        try:
            return classificar(mensagem, perfil)
        except (IntencaoNaoReconhecidaErro, IntencaoNaoPermitidaErro) as exc:
            # Recusa determinística: responde direto, sem gastar inferência.
            raise RespostaDiretaError(
                RespostaIA(
                    resposta=exc.message,
                    codigo=exc.code,
                    perfil=perfil.value,
                    sugestoes=sugestoes_para(perfil),
                )
            ) from exc

    async def _montar_contexto(
        self,
        resultado: ResultadoIntencao,
        usuario_id: uuid.UUID,
        perfil: Perfil,
        aluno_selecionado_id: uuid.UUID | None,
    ) -> ResultadoContexto:
        try:
            contexto = await construir_contexto(
                self._session,
                resultado,
                usuario_id=usuario_id,
                perfil=perfil,
                aluno_selecionado_id=aluno_selecionado_id,
            )
        except EscopoNaoResolvidoErro as exc:
            raise RespostaDiretaError(
                RespostaIA(
                    resposta=exc.message,
                    codigo=exc.code,
                    intencao=resultado.intencao.nome,
                    perfil=perfil.value,
                    sugestoes=sugestoes_para(perfil),
                )
            ) from exc
        except IntencaoNaoPermitidaErro as exc:
            # Defence in depth do context builder: intenção sem builder para
            # este perfil. Vira recusa, nunca 403 cru vindo de dentro do serviço.
            raise RespostaDiretaError(
                RespostaIA(
                    resposta=exc.message,
                    codigo=exc.code,
                    intencao=resultado.intencao.nome,
                    perfil=perfil.value,
                    sugestoes=sugestoes_para(perfil),
                )
            ) from exc
        except ContextoVazioErro as exc:
            # "Não há dado" NÃO é falha: é uma resposta. Sem esta conversão a
            # exceção subia do `stream()` até o `except Exception` do router e o
            # usuário recebia "erro interno" no lugar de "não encontrei isso".
            raise RespostaDiretaError(
                RespostaIA(
                    resposta=exc.message,
                    codigo=exc.code,
                    intencao=resultado.intencao.nome,
                    perfil=perfil.value,
                    alunos_autorizados=[],
                    sugestoes=sugestoes_para(perfil),
                )
            ) from exc

        if contexto.vazio or not contexto.fatos:
            raise RespostaDiretaError(
                RespostaIA(
                    resposta=contexto.resumo or textos.SEM_DADOS,
                    codigo="sem_dados",
                    intencao=contexto.intencao,
                    perfil=perfil.value,
                    alunos_autorizados=contexto.alunos_autorizados,
                    sugestoes=sugestoes_para(perfil),
                )
            )

        return contexto

    async def _inferir(
        self,
        resultado: ResultadoIntencao,
        contexto: ResultadoContexto,
        perfil: Perfil,
        nome_usuario: str,
        inicio: float,
        historico: list[dict[str, str]] | None = None,
    ) -> RespostaIA:
        mensagens = montar_mensagens(
            perfil=perfil,
            nome_usuario=nome_usuario or "usuário",
            resultado=resultado,
            contexto=contexto,
            historico=historico,
        )

        # 7) inferência. Sem ferramentas: o modelo não executa nada.
        resposta_llm = await self._client.chat(mensagens)

        # 8) guardrails mecânicos sobre a resposta.
        texto_final, alertas = validar_resposta(resposta_llm.conteudo, contexto)
        if alertas:
            logger.warning(
                "AI: guardrail acionado (intencao=%s perfil=%s alertas=%s)",
                contexto.intencao, perfil.value, alertas,
            )

        return RespostaIA(
            resposta=texto_final,
            codigo="ok",
            intencao=contexto.intencao,
            modelo=resposta_llm.modelo,
            perfil=perfil.value,
            latencia_ms=int((time.monotonic() - inicio) * 1000),
            tokens_prompt=resposta_llm.tokens_prompt,
            tokens_completion=resposta_llm.tokens_completion,
            fatos_utilizados=len(contexto.fatos),
            alunos_autorizados=contexto.alunos_autorizados,
            alertas_guardrails=alertas,
            # Sugestões também no caminho feliz: o cliente (web/mobile) mostra
            # atalhos depois de QUALQUER resposta, não só depois de uma recusa.
            sugestoes=sugestoes_para(perfil),
        )

    # ------------------------------------------------------------------
    async def health(self) -> dict:
        """Diagnóstico da IA. Nunca levanta exceção (ver ollama_client.health)."""
        saude = await self._client.health()
        circuito = await self._client.estado_circuito()

        if not settings.AI_ENABLED:
            status = "desabilitado"
        elif not saude.ollama_alive:
            status = "unavailable"
        elif not saude.model_present:
            status = "degraded"
        else:
            status = "ok"

        return {
            "status": status,
            "ai_enabled": settings.AI_ENABLED,
            "ollama_alive": saude.ollama_alive,
            "model": saude.model,
            "model_present": saude.model_present,
            "base_url": self._client.base_url,
            "latency_ms": saude.latency_ms,
            "detalhe": saude.detail,
            "circuito": circuito["circuito"],
            "falhas_consecutivas": circuito["falhas_consecutivas"],
            "reabrir_em_s": circuito["reabrir_em_s"],
        }

    async def stream(
        self,
        mensagem: str,
        *,
        usuario_id: uuid.UUID,
        perfil: Perfil,
        nome_usuario: str = "",
        aluno_selecionado_id: uuid.UUID | None = None,
        historico: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[EventoStream]:
        """Mesma cadeia do `responder()`, porém progressiva.

        A ordem das etapas é idêntica e igualmente invariante: allowlist antes
        de classificação, escopo antes de contexto, guardrails antes de
        entregar o texto. O streaming muda APENAS como o texto chega ao
        cliente.

        Recusas determinísticas (intenção fora da allowlist, aluno ambíguo,
        contexto vazio) não gastam inferência: viram um único evento `done`,
        igual ao caminho não-streaming.
        """
        inicio = time.monotonic()

        try:
            # 2.5) cortesia: sem banco e sem modelo, como no `responder()`.
            self._cortesia(mensagem, perfil)
            resultado = self._classificar(mensagem, perfil)
            contexto = await self._montar_contexto(
                resultado, usuario_id, perfil, aluno_selecionado_id,
            )
        except RespostaDiretaError as direta:
            yield EventoStream("done", resposta=direta.resposta)
            return

        mensagens = montar_mensagens(
            perfil=perfil,
            nome_usuario=nome_usuario or "usuário",
            resultado=resultado,
            contexto=contexto,
            historico=historico,
        )

        acumulado: list[str] = []
        try:
            async for pedaco in self._client.chat_stream(mensagens):
                acumulado.append(pedaco)
                yield EventoStream("delta", texto=pedaco)
        except AIException as exc:
            # Já podem ter saído deltas na tela. Por isso o evento leva o
            # parcial: o cliente pode mostrar que a resposta ficou incompleta
            # em vez de fingir que terminou.
            yield EventoStream(
                "erro", erro=exc.message, parcial="".join(acumulado),
            )
            return

        texto_llm = "".join(acumulado).strip()
        if not texto_llm:
            yield EventoStream(
                "erro",
                erro=textos.RESPOSTA_VAZIA,
                parcial="",
            )
            return

        texto_final, alertas = validar_resposta(texto_llm, contexto)
        if alertas:
            logger.warning(
                "AI: guardrail acionado no stream (intencao=%s perfil=%s alertas=%s)",
                contexto.intencao, perfil.value, alertas,
            )

        yield EventoStream("done", resposta=RespostaIA(
            resposta=texto_final,
            codigo="ok",
            intencao=contexto.intencao,
            modelo=self._client.modelo,
            perfil=perfil.value,
            latencia_ms=int((time.monotonic() - inicio) * 1000),
            fatos_utilizados=len(contexto.fatos),
            alunos_autorizados=contexto.alunos_autorizados,
            alertas_guardrails=alertas,
            sugestoes=sugestoes_para(perfil),
        ))


async def responder(
    session: AsyncSession,
    mensagem: str,
    *,
    usuario_id: uuid.UUID,
    perfil: Perfil,
    nome_usuario: str = "",
    aluno_selecionado_id: uuid.UUID | None = None,
    historico: list[dict[str, str]] | None = None,
    client: OllamaClient | None = None,
) -> RespostaIA:
    """Ponto de entrada único do serviço (usado pelo router e pelos testes)."""
    service = AIService(session, client=client)
    try:
        return await service.responder(
            mensagem,
            usuario_id=usuario_id,
            perfil=perfil,
            nome_usuario=nome_usuario,
            aluno_selecionado_id=aluno_selecionado_id,
            historico=historico,
        )
    except RespostaDiretaError as direta:
        return direta.resposta
