"""Cliente HTTP do Ollama (IA local "Atena").

SEGURANÇA
---------
Este cliente é a ÚNICA forma de a IA conversar com o modelo. Ele:

  - NUNCA recebe DSN, usuário ou senha de banco. Não importa SQLAlchemy,
    não importa `app.database`, não conhece o PostgreSQL. A IA não tem como
    consultar dados: quem monta o contexto é o backend (ver `context/`).
  - Só faz HTTP contra `OLLAMA_BASE_URL`. O container do Ollama, por sua vez,
    não tem credencial alguma de banco (ver docker-compose.yml).
  - Não envia ferramentas (tool calling) ao modelo. O Ollama é chamado com
    `tools` ausente/inativo de propósito: o LLM redige, ele não executa.

RESILIÊNCIA
-----------
Como o módulo é desacoplado do SGE, o cliente absorve todas as falhas e as
converte em exceções de domínio limpas (ver `exceptions.py`):

  - timeout de conexão curto  -> falha rápido quando o Ollama está desligado
  - timeout de inferência alto -> o modelo precisa ser carregado do volume
  - retry com backoff          -> apenas para transientes e antes de gerar
  - circuit breaker            -> para de martelar uma IA caída
  - semaphore                  -> serializa inferências (RAM de 8 GB não é infinita)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.modules.ai import mensagens as textos
from app.modules.ai.exceptions import (
    IADisponivelErro,
    LimiteConcorrenciaErro,
    ModeloNaoEncontradoErro,
)

logger = logging.getLogger(__name__)


@dataclass
class HealthOllama:
    """Resultado da sondagem de saúde. Nunca levanta exceção."""

    ollama_alive: bool
    model: str
    model_present: bool
    detail: str = ""
    latency_ms: int = 0
    versao: str = ""


@dataclass
class RespostaOllama:
    """Resposta normalizada de uma inferência."""

    conteudo: str
    modelo: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    duracao_ms: int = 0

    @property
    def tokens_total(self) -> int:
        return self.tokens_prompt + self.tokens_completion


@dataclass
class StreamingOllama:
    """Resultado de uma inferência em streaming, montado ao final.

    Os `chunks` são devolvidos em memória para que o chamador possa rodar os
    guardrails sobre o texto completo — sem isso, a validação de número
    alucinado não teria como acontecer. O tamanho é limitado por
    `OLLAMA_MAX_TOKENS`, então o buffer é pequeno e conhecido.
    """

    texto: str
    modelo: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    duracao_ms: int = 0


class _SlotLiberado:
    """Devolve o slot de concorrência exatamente uma vez, aconteça o que acontecer.

    Existe porque o `finally` de um gerador assíncrono NÃO é garantia de
    liberação. Quando o cliente HTTP desconecta, quem é cancelada é a task que
    consome a stream; o gerador fica suspenso no `yield` e o `finally` só roda
    quando o coletor de lixo o fechar — ou nunca. Com
    `OLLAMA_MAX_CONCURRENCY=1`, esse vazamento se traduz em 429 para todos os
    usuários até o GC passar.

    A liberação é atrelada ao fim da task consumidora (`add_done_callback`), que
    é o evento que realmente significa "esse stream acabou, de um jeito ou de
    outro". O `finally` continua existindo para o caminho feliz e para o
    `GeneratorExit`; os dois caminhos convergem no `liberar()` idempotente.
    """

    __slots__ = ("_semaphore", "_liberado", "_tarefa")

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        self._semaphore = semaphore
        self._liberado = False
        self._tarefa: asyncio.Task | None = None

    def __enter__(self) -> _SlotLiberado:
        self._tarefa = asyncio.current_task()
        if self._tarefa is not None:
            self._tarefa.add_done_callback(self._quando_acabar)
        return self

    def __exit__(self, *_exc) -> None:
        self.liberar()

    def liberar(self) -> None:
        if self._liberado:
            return
        self._liberado = True
        self._semaphore.release()

    def _quando_acabar(self, _tarefa: asyncio.Task) -> None:
        self.liberar()


@dataclass
class EstadoCircuito:
    """Estado do circuit breaker (failures consecutivas)."""

    falhas: int = 0
    aberto_em: float | None = None

    @property
    def aberto(self) -> bool:
        return self.aberto_em is not None

    def duracao_aberto(self) -> float:
        return 0.0 if self.aberto_em is None else time.monotonic() - self.aberto_em


class CircuitAbertoErro(IADisponivelErro):
    """Circuito aberto: nem chega a tentar falar com o Ollama."""


# Instância compartilhada do processo. O circuit breaker e o semáforo de
# concorrência só fazem sentido se viverem POR PROCESSO: um cliente novo a cada
# requisição zeraria as falhas a cada request e o breaker nunca abriria.
_CLIENTE: OllamaClient | None = None


def get_client(settings_obj=None) -> OllamaClient:
    """Cliente único do processo (singleton lazy).

    Por que singleton: o estado de resiliência (falhas consecutivas, instante de
    abertura do circuito, trava do semáforo) precisa sobreviver entre requisições.
    O `httpx.AsyncClient`, esse sim, é criado e destruído por chamada — o custo de
    conectar é irrelevante comparado aos segundos de inferência.
    """
    global _CLIENTE
    if settings_obj is not None:
        # Injeção explícita (usada nos testes) não toca no singleton global.
        return OllamaClient(settings_obj)
    if _CLIENTE is None:
        _CLIENTE = OllamaClient()
    return _CLIENTE


def reset_client() -> None:
    """Descarta o singleton (testes e reinício controlado)."""
    global _CLIENTE
    _CLIENTE = None


class OllamaClient:
    """Cliente assíncrono da API HTTP do Ollama.

    Não possui estado de banco, apenas configuração + estado de resiliência.
    Use `get_client()` para obter a instância compartilhada do processo; o
    construtor direto serve para testes com configuração isolada.
    """

    def __init__(self, settings_obj=None) -> None:
        self._s = settings_obj or settings
        self._estado = EstadoCircuito()
        # Um único lock protege o estado do circuito entre requisições.
        self._lock = asyncio.Lock()
        # Semáforo de concorrência criado sob demanda: instanciá-lo no
        # __init__ amarraria o loop de eventos do processo ao de criação.
        self._semaphore: asyncio.Semaphore | None = None

    # ------------------------------------------------------------------
    # Propriedades derivadas
    # ------------------------------------------------------------------
    @property
    def base_url(self) -> str:
        return self._s.OLLAMA_BASE_URL.rstrip("/")

    @property
    def modelo(self) -> str:
        return self._s.OLLAMA_MODEL

    @property
    def habilitado(self) -> bool:
        return bool(self._s.AI_ENABLED)

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(max(1, self._s.OLLAMA_MAX_CONCURRENCY))
        return self._semaphore

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------
    async def _pode_tentar(self) -> bool:
        """True se o circuito permite uma nova tentativa.

        Em estado aberto, só reabre (half-open) depois de
        `OLLAMA_CIRCUIT_RESET_SECONDS`; a próxima chamada real é a sonda.
        """
        async with self._lock:
            if not self._estado.aberto:
                return True
            if self._estado.duracao_aberto() >= self._s.OLLAMA_CIRCUIT_RESET_SECONDS:
                logger.info("OllamaClient: circuito em half-open, liberando nova tentativa")
                self._estado.aberto_em = None
                self._estado.falhas = 0
                return True
            return False

    async def _registrar_falha(self) -> None:
        async with self._lock:
            self._estado.falhas += 1
            if self._estado.falhas >= self._s.OLLAMA_CIRCUIT_FAILURES:
                self._estado.aberto_em = time.monotonic()
                logger.error(
                    "OllamaClient: circuito ABERTO após %d falhas consecutivas. "
                    "Pausando tentativas por %ds.",
                    self._estado.falhas, self._s.OLLAMA_CIRCUIT_RESET_SECONDS,
                )

    async def _registrar_sucesso(self) -> None:
        async with self._lock:
            if self._estado.falhas or self._estado.aberto:
                logger.info("OllamaClient: circuito fechado após sucesso")
            self._estado.falhas = 0
            self._estado.aberto_em = None

    async def estado_circuito(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "circuito": "aberto" if self._estado.aberto else "fechado",
                "falhas_consecutivas": self._estado.falhas,
                "limite_falhas": self._s.OLLAMA_CIRCUIT_FAILURES,
                "reabrir_em_s": (
                    max(
                        0,
                        int(self._s.OLLAMA_CIRCUIT_RESET_SECONDS - self._estado.duracao_aberto()),
                    )
                    if self._estado.aberto
                    else 0
                ),
            }

    # ------------------------------------------------------------------
    # Health (nunca levanta exceção — é um diagnóstico)
    # ------------------------------------------------------------------
    async def health(self) -> HealthOllama:
        """Sonda `/api/tags` com timeout curto.

        Mesmo com o Ollama fora do ar, devolve um HealthOllama com
        `ollama_alive=False` — é isso que permite ao /ai/health responder
        "unavailable" em vez de estourar 500.
        """
        if not self.habilitado:
            return HealthOllama(
                ollama_alive=False,
                model=self.modelo,
                model_present=False,
                detail="IA desabilitada por configuração (AI_ENABLED=false)",
            )

        inicio = time.monotonic()
        try:
            timeout = httpx.Timeout(
                self._s.OLLAMA_HEALTH_TIMEOUT,
                connect=self._s.OLLAMA_HEALTH_TIMEOUT,
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            latencia = int((time.monotonic() - inicio) * 1000)
            logger.warning("OllamaClient: health falhou (%s)", type(exc).__name__)
            return HealthOllama(
                ollama_alive=False,
                model=self.modelo,
                model_present=False,
                detail=f"Ollama inacessível: {type(exc).__name__}",
                latency_ms=latencia,
            )

        latencia = int((time.monotonic() - inicio) * 1000)
        modelos = [m.get("name") for m in payload.get("models", []) if m.get("name")]
        presente = self._model_presente(modelos)

        return HealthOllama(
            ollama_alive=True,
            model=self.modelo,
            model_present=presente,
            detail="ok" if presente else f"modelo '{self.modelo}' ausente",
            latency_ms=latencia,
            versao=payload.get("version", ""),
        )

    def _model_presente(self, modelos: list[str]) -> bool:
        """Compara o nome do modelo tolerando a ausência da tag.

        Ex.: 'qwen3:4b' casa com 'qwen3:4b' e também com 'qwen3:4b-instruct'.
        """
        if not modelos:
            return False
        alvo = self.modelo
        base_alvo = alvo.split(":")[0]
        for nome in modelos:
            if nome == alvo:
                return True
            # `qwen3:4b` considera presente `qwen3:4b-instruct-q4_K_M`
            if nome.split(":")[0] == base_alvo and nome.startswith(alvo):
                return True
        return False

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    async def chat(
        self,
        mensagens: list[dict[str, str]],
        *,
        num_ctx: int | None = None,
    ) -> RespostaOllama:
        """Executa uma inferência não-streaming.

        `mensagens` já vem pronta do `prompt.py`: system prompt com a
        personalidade, contexto autorizado delimitado e a pergunta do usuário.
        Este método não sabe o que há no contexto nem quem é o usuário.
        """
        if not self.habilitado:
            raise IADisponivelErro(textos.IA_DESABILITADA)

        if not await self._pode_tentar():
            estado = await self.estado_circuito()
            logger.info(
                "OllamaClient: circuito aberto, reabre em %ss", estado["reabrir_em_s"],
            )
            raise CircuitAbertoErro(textos.IA_INDISPONIVEL)

        # Serializa inferências: a fila não pode acumular memória esperando.
        # Timeout curto → se já há uma inferência em andamento, o usuário recebe
        # um erro claro em vez de ficar pendurado.
        semaphore = self._get_semaphore()
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=0.5)
        except TimeoutError:
            raise LimiteConcorrenciaErro(textos.IA_SOBRECARREGADA) from None

        try:
            return await self._chat_com_retry(mensagens, num_ctx=num_ctx)
        finally:
            semaphore.release()

    async def _chat_com_retry(
        self,
        mensagens: list[dict[str, str]],
        *,
        num_ctx: int | None = None,
    ) -> RespostaOllama:
        """Retry com backoff apenas para falhas transitórias.

        Não repetimos quando o modelo não existe (erro de configuração, não
        transitório) nem quando o Ollama está desligado em cima de circuito
        aberto — o breaker cuida do resto.
        """
        tentativas = max(1, self._s.OLLAMA_RETRY_ATTEMPTS + 1)
        ultima_excecao: Exception | None = None

        for tentativa in range(1, tentativas + 1):
            try:
                return await self._chat_once(mensagens, num_ctx=num_ctx)
            except ModeloNaoEncontradoErro:
                # Não é transitório: repetir não vai instalar o modelo.
                await self._registrar_sucesso()  # Ollama está vivo, só falta o modelo
                raise
            except IADisponivelErro as exc:
                ultima_excecao = exc
                await self._registrar_falha()
                if tentativa >= tentativas:
                    break
                backoff = self._s.OLLAMA_RETRY_BACKOFF * (2 ** (tentativa - 1))
                logger.warning(
                    "OllamaClient: falha na tentativa %d/%d (%s). Backoff de %.1fs.",
                    tentativa, tentativas, exc, backoff,
                )
                await asyncio.sleep(backoff)

        assert ultima_excecao is not None
        raise ultima_excecao

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------
    async def chat_stream(
        self,
        mensagens: list[dict[str, str]],
        *,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        """Itera uma inferência em streaming, emitindo pedaços de texto.

        O limite de concorrência, o circuit breaker e o timeout valem IGUALMENTE
        para o streaming — é o mesmo recurso caro (RAM do Ollama), então
        deixar o stream escapar do semáforo permitiria várias inferências
        simultâneas e oOOM no container.

        Diferenças em relação a `chat()`:

        - NÃO há retry. Retentar no meio de um stream já emitido duplicaria
          texto na tela do usuário. Falha no meio vira erro para o cliente,
          que sabe que a resposta ficou incompleta.
        - o timeout de LEITURA vale por pedaço, não para a resposta inteira:
          o modelo pode legitimamente ficar quieto entre tokens, mas não pode
          ficar quieto para sempre.
        - o semáforo é liberado em `finally` e TAMBÉM quando a task que consome
          o stream termina (ver `_SlotLiberado`). Um `finally` sozinho não basta:
          se o cliente desconectar, a task morre com `CancelledError` FORA do
          gerador (que fica suspenso no `yield`) e o slot vazaria até o GC
          passar por ele — com `OLLAMA_MAX_CONCURRENCY=1`, isso significa
          "429 para todo mundo" logo depois de um usuário fechar a tela.
        """
        if not self.habilitado:
            raise IADisponivelErro(textos.IA_DESABILITADA)

        if not await self._pode_tentar():
            estado = await self.estado_circuito()
            logger.info(
                "OllamaClient: circuito aberto, reabre em %ss", estado["reabrir_em_s"],
            )
            raise CircuitAbertoErro(textos.IA_INDISPONIVEL)

        semaphore = self._get_semaphore()
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=0.5)
        except TimeoutError:
            raise LimiteConcorrenciaErro(textos.IA_SOBRECARREGADA) from None

        payload = self._payload(mensagens, stream=True, num_ctx=num_ctx)
        # O timeout de LEITURA do httpx é generoso aqui porque ele também cobre a
        # espera pelo PRIMEIRO byte — e o primeiro byte é o instante em que o
        # Ollama carrega o modelo em memória. Medido em produção: a primeira
        # pergunta depois de o container subir leva ~56s (cold) contra ~6s de
        # TTFT com o modelo já carregado. Com um `read` de 30s, essa primeira
        # pergunta morreria com "demorou demais" — justamente a que o usuário
        # fez de cara. O limite curto por pedaço é aplicado à mão, logo abaixo.
        timeout = httpx.Timeout(
            self._s.OLLAMA_TIMEOUT,
            connect=self._s.OLLAMA_CONNECT_TIMEOUT,
            read=self._s.OLLAMA_STREAM_FIRST_TOKEN_TIMEOUT,
        )
        inicio = time.monotonic()
        slot = _SlotLiberado(semaphore)
        slot.__enter__()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload,
                ) as response:
                    if response.status_code == 404:
                        raise ModeloNaoEncontradoErro(self.modelo)
                    if response.status_code >= 500:
                        raise IADisponivelErro(textos.IA_INDISPONIVEL)
                    response.raise_for_status()

                    # Depois do primeiro token, cada pedaço tem prazo curto
                    # (OLLAMA_STREAM_READ_TIMEOUT): entre tokens o modelo pode
                    # ficar quieto legitimamente, mas não pode travar de vez.
                    linhas = response.aiter_lines()
                    primeira = True
                    while True:
                        limite = (
                            self._s.OLLAMA_STREAM_FIRST_TOKEN_TIMEOUT
                            if primeira
                            else self._s.OLLAMA_STREAM_READ_TIMEOUT
                        )
                        try:
                            linha = await asyncio.wait_for(anext(linhas), timeout=limite)
                        except StopAsyncIteration:
                            break
                        except TimeoutError as exc:
                            raise httpx.ReadTimeout(
                                f"sem token por {limite}s",
                            ) from exc
                        primeira = False
                        if not linha:
                            continue
                        try:
                            evento = json.loads(linha)
                        except ValueError:
                            # Linha keep-alive ou lixo: o stream segue.
                            continue
                        if evento.get("error"):
                            raise IADisponivelErro(textos.IA_INDISPONIVEL)
                        pedaco = (evento.get("message") or {}).get("content", "")
                        if pedaco:
                            yield pedaco
                        if evento.get("done"):
                            break

            await self._registrar_sucesso()
        except httpx.TimeoutException as exc:
            duracao = int((time.monotonic() - inicio) * 1000)
            logger.warning("OllamaClient: timeout no stream após %dms", duracao)
            await self._registrar_falha()
            raise IADisponivelErro(textos.IA_INDISPONIVEL) from exc
        except httpx.HTTPError as exc:
            logger.warning("OllamaClient: erro de rede no stream (%s)", type(exc).__name__)
            await self._registrar_falha()
            raise IADisponivelErro(textos.IA_INDISPONIVEL) from exc
        finally:
            slot.liberar()

    async def chat_stream_coletado(
        self,
        mensagens: list[dict[str, str]],
        *,
        num_ctx: int | None = None,
    ) -> StreamingOllama:
        """Streaming consumido por inteiro, devolvendo o texto montado.

        Existe para os testes e para qualquer chamador que queira o resultado
        sem stream — o endpoint SSE usa `chat_stream` diretamente.
        """
        inicio = time.monotonic()
        partes: list[str] = []
        async for pedaco in self.chat_stream(mensagens, num_ctx=num_ctx):
            partes.append(pedaco)
        texto = "".join(partes).strip()
        if not texto:
            raise IADisponivelErro(textos.RESPOSTA_VAZIA)
        return StreamingOllama(
            texto=texto,
            modelo=self.modelo,
            duracao_ms=int((time.monotonic() - inicio) * 1000),
        )

    def _payload(
        self,
        mensagens: list[dict[str, str]],
        *,
        stream: bool,
        num_ctx: int | None = None,
    ) -> dict[str, Any]:
        """Corpo da requisição ao Ollama. Idêntico nos dois modos, exceto `stream`.

        Ficar em um método só garante que streaming e não-streaming não
        divirjam por accidento — se o `think: false` ou o `num_ctx` mudarem em
        um lado, mudam nos dois.
        """
        return {
            "model": self.modelo,
            "messages": mensagens,
            "stream": stream,
            # `think: false` desliga o modo raciocínio do Qwen3. Sem isso, um
            # modelo local quebras a cabeça por minutos para responder "OK"
            # (medido no 1,7 B: 7min39 → 2s com esta flag). A Atena só reescreve
            # fatos já calculados pelo backend; raciocínio estendido não agrega
            # nada e transforma cada pergunta em um timeout.
            "think": bool(self._s.OLLAMA_THINK),
            # Sem `tools` de propósito: a IA não executa nada. Ela apenas
            # reescreve fatos já autorizados em linguagem natural.
            "options": {
                "temperature": self._s.OLLAMA_TEMPERATURE,
                "top_p": self._s.OLLAMA_TOP_P,
                "repeat_penalty": self._s.OLLAMA_REPEAT_PENALTY,
                "num_predict": self._s.OLLAMA_MAX_TOKENS,
                "num_ctx": num_ctx or self._s.OLLAMA_NUM_CTX,
            },
        }

    async def _chat_once(
        self,
        mensagens: list[dict[str, str]],
        *,
        num_ctx: int | None = None,
    ) -> RespostaOllama:
        payload = self._payload(mensagens, stream=False, num_ctx=num_ctx)
        timeout = httpx.Timeout(
            self._s.OLLAMA_TIMEOUT,
            connect=self._s.OLLAMA_CONNECT_TIMEOUT,
        )
        inicio = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            duracao = int((time.monotonic() - inicio) * 1000)
            logger.warning("OllamaClient: timeout de inferência após %dms", duracao)
            raise IADisponivelErro(textos.IA_INDISPONIVEL) from exc
        except httpx.HTTPError as exc:
            logger.warning("OllamaClient: erro de rede (%s)", type(exc).__name__)
            raise IADisponivelErro(textos.IA_INDISPONIVEL) from exc

        if response.status_code == 404:
            # Modelo inexistente no Ollama.
            raise ModeloNaoEncontradoErro(self.modelo)
        if response.status_code >= 500:
            raise IADisponivelErro(textos.IA_INDISPONIVEL)

        try:
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise IADisponivelErro(textos.IA_INDISPONIVEL) from exc

        conteudo = (data.get("message") or {}).get("content", "").strip()
        if not conteudo:
            raise IADisponivelErro(textos.RESPOSTA_VAZIA)

        await self._registrar_sucesso()
        return RespostaOllama(
            conteudo=conteudo,
            modelo=data.get("model", self.modelo),
            tokens_prompt=int(data.get("prompt_eval_count") or 0),
            tokens_completion=int(data.get("eval_count") or 0),
            duracao_ms=int((time.monotonic() - inicio) * 1000),
        )
