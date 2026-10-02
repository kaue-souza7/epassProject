"""Testes do streaming do OllamaClient e do `AIService.stream` (Fase 4).

O que precisa estar garantido aqui:

- o NDJSON do Ollama vira deltas na ordem, sem repetir nem perder pedaço;
- linhas de keep-alive/JSON inválido não quebram o stream;
- o `done` do Ollama encerra a leitura;
- o limite de concorrência vale para o stream (e o semáforo é SEMPRE liberado);
- falha no meio do stream NÃO é retentada (duplicaria texto na tela);
- timeout de leitura vira erro de domínio, não exceção crua;
- modelo ausente (404) e 5xx viram erro de domínio;
- o circuit breaker conta falha do stream;
- cancelar o consumidor (cliente desconectou) libera o semáforo;
- `AIService.stream` aplica os mesmos guardrails do caminho não-streaming e
  entrega o texto final pós-guardrail como autoritativo.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.modules.ai.exceptions import (
    IADisponivelErro,
    LimiteConcorrenciaErro,
    ModeloNaoEncontradoErro,
)
from app.modules.ai.intent import ResultadoIntencao
from app.modules.ai.ollama_client import CircuitAbertoErro, OllamaClient
from app.modules.ai.service import AIService, EventoStream
from app.shared.enums import Perfil

BASE = "http://ollama:11434"
MENSAGEM = [{"role": "user", "content": "qual a nota da Ana?"}]


def make_config(**overrides) -> SimpleNamespace:
    base = {
        "AI_ENABLED": True,
        "OLLAMA_BASE_URL": BASE,
        "OLLAMA_MODEL": "qwen3:4b",
        "OLLAMA_TIMEOUT": 2,
        "OLLAMA_CONNECT_TIMEOUT": 1,
        "OLLAMA_HEALTH_TIMEOUT": 1,
        "OLLAMA_STREAM_READ_TIMEOUT": 2,
        "OLLAMA_STREAM_FIRST_TOKEN_TIMEOUT": 10,
        "OLLAMA_NUM_CTX": 4096,
        "OLLAMA_TEMPERATURE": 0.2,
        "OLLAMA_TOP_P": 0.9,
        "OLLAMA_REPEAT_PENALTY": 1.1,
        "OLLAMA_MAX_TOKENS": 400,
        "OLLAMA_THINK": False,
        "OLLAMA_MAX_CONCURRENCY": 1,
        "OLLAMA_RETRY_ATTEMPTS": 2,
        "OLLAMA_RETRY_BACKOFF": 0.01,
        "OLLAMA_CIRCUIT_FAILURES": 3,
        "OLLAMA_CIRCUIT_RESET_SECONDS": 60,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def ndjson(*eventos: dict) -> bytes:
    """Serializa eventos como linhas NDJSON, como o Ollama faz."""
    return "".join(
        json.dumps(e, ensure_ascii=False) + "\n" for e in eventos
    ).encode("utf-8")


class StreamFake(httpx.AsyncByteStream):
    """Stream assíncrono de verdade: o transporte do httpx exige AsyncByteStream
    (um iterador sync aqui faria o mock nem ser aplicado)."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk


def stream_de(*linhas: bytes) -> httpx.Response:
    """Conteúdo de resposta em streaming, chunk a chunk."""
    return httpx.Response(200, stream=StreamFake(list(linhas)))


# ---------------------------------------------------------------------------
# NDJSON -> deltas
# ---------------------------------------------------------------------------
@respx.mock
async def test_stream_emite_deltas_na_ordem():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(
            ndjson({"message": {"role": "assistant", "content": "A nota "}}),
            ndjson({"message": {"role": "assistant", "content": "da Ana "}}),
            ndjson({"message": {"role": "assistant", "content": "foi 8,50."}}),
            ndjson({"message": {"content": ""}, "done": True}),
        )
    )
    pedacos = [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]
    assert pedacos == ["A nota ", "da Ana ", "foi 8,50."]


@respx.mock
async def test_stream_manda_stream_true_e_pensa_desligado():
    """O payload do stream precisa ser o MESMO do não-streaming, exceto `stream`."""
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(ndjson({"message": {"content": "oi"}, "done": True}))
    )
    cliente = OllamaClient(make_config())
    [p async for p in cliente.chat_stream(MENSAGEM)]

    enviado = json.loads(respx.calls.last.request.content)
    assert enviado["stream"] is True
    assert enviado["think"] is False
    assert "tools" not in enviado, "a IA não pode ganhar ferramentas no stream"
    assert enviado["model"] == cliente.modelo

    nao_stream = cliente._payload(MENSAGEM, stream=False)
    difere = {k for k in nao_stream if nao_stream[k] != enviado[k]}
    assert difere == {"stream"}, f"payloads divergiram em {difere}"


@respx.mock
async def test_stream_ignora_lixo_e_keepalive():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(
            b"\n",
            ndjson({"message": {"content": "Ana "}}),
            b"nao-e-json\n",
            ndjson({"message": {"content": "tinha 8,50."}}),
            ndjson({"message": {"content": ""}, "done": True}),
        )
    )
    pedacos = [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]
    assert "".join(pedacos) == "Ana tinha 8,50."


@respx.mock
async def test_stream_erro_json_vira_erro_de_dominio():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(ndjson({"error": "model requires more system memory"}))
    )
    with pytest.raises(IADisponivelErro):
        [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]


@respx.mock
async def test_stream_modelo_ausente_404():
    respx.post(f"{BASE}/api/chat").mock(return_value=httpx.Response(404, json={}))
    with pytest.raises(ModeloNaoEncontradoErro):
        [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]


@respx.mock
async def test_stream_5xx_vira_503():
    respx.post(f"{BASE}/api/chat").mock(return_value=httpx.Response(503, text="boom"))
    with pytest.raises(IADisponivelErro):
        [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]


@respx.mock
async def test_stream_timeout_de_leitura_vira_erro_de_dominio():
    respx.post(f"{BASE}/api/chat").mock(side_effect=httpx.ReadTimeout("preso"))
    with pytest.raises(IADisponivelErro):
        [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]


@respx.mock
async def test_stream_primeiro_token_lento_passa_pra_cima_do_prazo_curto():
    """Cold start: o primeiro token leva mais que o prazo entre tokens.

    Regressão real: com `read` de 30s para tudo, a primeira pergunta depois de o
    Ollama subir morria com "demorou demais" (medido ~56s de cold start).
    """
    cenario = make_config(OLLAMA_STREAM_READ_TIMEOUT=0.05, OLLAMA_STREAM_FIRST_TOKEN_TIMEOUT=5)

    async def corpo_lento():
        await asyncio.sleep(0.3)  # "carregando o modelo"
        yield (json.dumps({"message": {"content": "A"}}) + "\n").encode()
        yield (json.dumps({"message": {"content": "B"}}) + "\n").encode()
        yield (json.dumps({"done": True}) + "\n").encode()

    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, stream=corpo_lento()),
    )
    pedacos = [p async for p in OllamaClient(cenario).chat_stream(MENSAGEM)]
    assert pedacos == ["A", "B"]


@respx.mock
async def test_stream_travado_no_meio_ainda_derruba():
    """Depois do primeiro token, o prazo curto volta a valer."""
    cenario = make_config(OLLAMA_STREAM_READ_TIMEOUT=0.05, OLLAMA_STREAM_FIRST_TOKEN_TIMEOUT=5)

    async def corpo_preso():
        yield (json.dumps({"message": {"content": "A"}}) + "\n").encode()
        await asyncio.sleep(5)  # trava aqui
        yield (json.dumps({"done": True}) + "\n").encode()

    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, stream=corpo_preso()),
    )
    with pytest.raises(IADisponivelErro):
        [p async for p in OllamaClient(cenario).chat_stream(MENSAGEM)]


@respx.mock
async def test_stream_nao_retenta_para_nao_duplicar_texto():
    """Retry no meio do stream repetiria a resposta na tela do usuário."""
    respx.post(f"{BASE}/api/chat").mock(side_effect=httpx.ReadError("caiu no meio"))
    with pytest.raises(IADisponivelErro):
        [p async for p in OllamaClient(make_config()).chat_stream(MENSAGEM)]
    assert respx.calls.call_count == 1, "streaming não pode repetir a requisição"


# ---------------------------------------------------------------------------
# Semáforo e circuit breaker
# ---------------------------------------------------------------------------
@respx.mock
async def test_stream_respeita_limite_de_concorrencia():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(ndjson({"message": {"content": "x"}, "done": True}))
    )
    cliente = OllamaClient(make_config(OLLAMA_MAX_CONCURRENCY=1))

    # segura o único slot
    await cliente._get_semaphore().acquire()
    with pytest.raises(LimiteConcorrenciaErro):
        [p async for p in cliente.chat_stream(MENSAGEM)]
    cliente._get_semaphore().release()


@respx.mock
async def test_stream_libera_semaphore_no_fim():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(ndjson({"message": {"content": "ok"}, "done": True}))
    )
    cliente = OllamaClient(make_config(OLLAMA_MAX_CONCURRENCY=1))
    [p async for p in cliente.chat_stream(MENSAGEM)]
    assert cliente._get_semaphore().locked() is False


@respx.mock
async def test_stream_libera_semaphore_quando_cliente_desconecta():
    """Cancelamento é o cenário comum (usuário fecha a tela): não pode vazar slot.

    Reproduz o que o uvicorn faz quando a conexão morre: a task que consome a
    stream é cancelada com `CancelledError` dentro do `yield`, o `finally` roda e
    o semáforo volta a ficar livre.
    """
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(
            ndjson({"message": {"content": "começou "}}),
            ndjson({"message": {"content": "e não termina"}}),
        )
    )
    cliente = OllamaClient(make_config(OLLAMA_MAX_CONCURRENCY=1))
    chegou = asyncio.Event()

    async def consumir():
        async for _pedaco in cliente.chat_stream(MENSAGEM):
            chegou.set()
            await asyncio.sleep(10)  # "fica desenhando" até o cliente sumir

    task = asyncio.create_task(consumir())
    await chegou.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert cliente._get_semaphore().locked() is False, "vazou o slot de concorrência"


@respx.mock
async def test_stream_libera_semaphore_com_aclose():
    """Fechar o gerador (`GeneratorExit`) também precisa liberar o slot."""
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(
            ndjson({"message": {"content": "um "}}),
            ndjson({"message": {"content": "dois"}}),
        )
    )
    cliente = OllamaClient(make_config(OLLAMA_MAX_CONCURRENCY=1))
    gerador = cliente.chat_stream(MENSAGEM)
    assert await gerador.__anext__() == "um "
    await gerador.aclose()
    assert cliente._get_semaphore().locked() is False


@respx.mock
async def test_stream_contabiliza_falha_no_circuit_breaker():
    respx.post(f"{BASE}/api/chat").mock(side_effect=httpx.ReadError("caiu"))
    cliente = OllamaClient(make_config(OLLAMA_CIRCUIT_FAILURES=2))
    for _ in range(2):
        with pytest.raises(IADisponivelErro):
            [p async for p in cliente.chat_stream(MENSAGEM)]

    assert (await cliente.estado_circuito())["circuito"] == "aberto"
    with pytest.raises(CircuitAbertoErro):
        [p async for p in cliente.chat_stream(MENSAGEM)]


@respx.mock
async def test_stream_zerar_sucesso_fecha_circuito():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(ndjson({"message": {"content": "ok"}, "done": True}))
    )
    cliente = OllamaClient(make_config())
    [p async for p in cliente.chat_stream(MENSAGEM)]
    assert (await cliente.estado_circuito())["falhas_consecutivas"] == 0


@respx.mock
async def test_stream_desabilitado_nao_chega_ao_ollama():
    respx.post(f"{BASE}/api/chat").mock(return_value=httpx.Response(500))
    cliente = OllamaClient(make_config(AI_ENABLED=False))
    with pytest.raises(IADisponivelErro):
        [p async for p in cliente.chat_stream(MENSAGEM)]
    assert respx.calls.call_count == 0


@respx.mock
async def test_chat_stream_coletado_devolve_texto_completo():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=stream_de(
            ndjson({"message": {"content": "A nota "}}),
            ndjson({"message": {"content": "foi 8,50."}}),
            ndjson({"message": {"content": ""}, "done": True}),
        )
    )
    resultado = await OllamaClient(make_config()).chat_stream_coletado(MENSAGEM)
    assert resultado.texto == "A nota foi 8,50."
    assert resultado.modelo == "qwen3:4b"


# ---------------------------------------------------------------------------
# AIService.stream
# ---------------------------------------------------------------------------
class ClienteFalsoStream:
    """Dublê com a mesma interface de streaming do OllamaClient."""

    def __init__(self, pedacos: list[str], erro: Exception | None = None) -> None:
        self.pedacos = pedacos
        self.erro = erro
        self.base_url = "http://falso"
        self.modelo = "qwen3:4b"
        self.mensagens_recebidas: list[dict[str, str]] = []
        self.estado_circuito_valor = {
            "circuito": "fechado", "falhas_consecutivas": 0,
            "limite_falhas": 5, "reabrir_em_s": 0,
        }

    async def chat_stream(self, mensagens, **_kw):
        self.mensagens_recebidas = mensagens
        for p in self.pedacos:
            yield p
        if self.erro:
            raise self.erro

    async def chat(self, mensagens, **_kw):  # pragma: no cover
        raise AssertionError("o caminho de streaming não pode usar chat()")

    async def health(self):  # pragma: no cover
        raise AssertionError("health não é usado aqui")

    async def estado_circuito(self):
        return self.estado_circuito_valor


class SessaoFalsa:
    """O `AIService.stream` só fala com o banco via `construir_contexto`; aqui
    ele é substituído, então a sessão nunca é usada de verdade."""


async def coletar(stream) -> list[EventoStream]:
    return [e async for e in stream]


async def test_service_stream_entrega_deltas_e_final(monkeypatch):
    from app.modules.ai.context import base as base_ctx
    from app.modules.ai.service import RespostaIA

    contexto = base_ctx.ResultadoContexto(intencao="notas_aluno_ultima")
    contexto.adicionar("Aluno: Ana | Turma: 1A |Ultima nota de Matematica: 8,50")
    contexto.alunos_autorizados = [__import__("uuid").uuid4()]

    async def contexto_falso(*_a, **_k):
        return contexto

    monkeypatch.setattr("app.modules.ai.service.construir_contexto", contexto_falso)
    monkeypatch.setattr(
        "app.modules.ai.service.classificar",
        lambda m, p: ResultadoIntencao(
            intencao="notas_aluno_ultima", mensagem_original=m,
            mensagem_normalizada=m, consulta=m,
        ),
    )

    cliente = ClienteFalsoStream(["A nota ", "da Ana ", "foi 8,50."])
    servico = AIService(SessaoFalsa(), client=cliente)
    eventos = await coletar(servico.stream(
        "nota da Ana?", usuario_id=__import__("uuid").uuid4(), perfil=Perfil.RESPONSAVEL,
    ))

    assert [e.tipo for e in eventos] == ["delta", "delta", "delta", "done"]
    assert "".join(e.texto for e in eventos if e.tipo == "delta") == "A nota da Ana foi 8,50."
    final = eventos[-1].resposta
    assert isinstance(final, RespostaIA)
    assert final.resposta == "A nota da Ana foi 8,50."
    assert final.intencao == "notas_aluno_ultima"
    assert final.perfil == Perfil.RESPONSAVEL.value


async def test_service_stream_guardrail_corta_numero_inventado(monkeypatch):
    """O `done` é pós-guardrail: mesmo que o deltas tenha dito 9,99, o
    autoritativo é o texto validado."""
    from app.modules.ai.context import base as base_ctx

    contexto = base_ctx.ResultadoContexto(intencao="notas_aluno_ultima")
    contexto.adicionar("Aluno: Ana | Turma: 1A |Ultima nota de Matematica: 8,50")
    contexto.alunos_autorizados = [__import__("uuid").uuid4()]

    async def contexto_falso(*_a, **_k):
        return contexto

    monkeypatch.setattr("app.modules.ai.service.construir_contexto", contexto_falso)
    monkeypatch.setattr(
        "app.modules.ai.service.classificar",
        lambda m, p: ResultadoIntencao(
            intencao="notas_aluno_ultima", mensagem_original=m,
            mensagem_normalizada=m, consulta=m,
        ),
    )

    cliente = ClienteFalsoStream(["A nota foi ", "9,99."])
    servico = AIService(SessaoFalsa(), client=cliente)
    eventos = await coletar(servico.stream(
        "nota da Ana?", usuario_id=__import__("uuid").uuid4(), perfil=Perfil.RESPONSAVEL,
    ))

    final = eventos[-1].resposta
    assert "9,99" not in final.resposta, "guardrail não removiu o número inventado"
    assert final.alertas_guardrails, "o corte deveria ser registrado"


async def test_service_stream_erro_no_meio_vem_com_parcial(monkeypatch):
    from app.modules.ai.context import base as base_ctx

    contexto = base_ctx.ResultadoContexto(intencao="notas_aluno_ultima")
    contexto.adicionar("Aluno: Ana")

    async def contexto_falso(*_a, **_k):
        return contexto

    monkeypatch.setattr("app.modules.ai.service.construir_contexto", contexto_falso)
    monkeypatch.setattr(
        "app.modules.ai.service.classificar",
        lambda m, p: ResultadoIntencao(
            intencao="notas_aluno_ultima", mensagem_original=m,
            mensagem_normalizada=m, consulta=m,
        ),
    )

    cliente = ClienteFalsoStream(["A nota foi "], erro=IADisponivelErro("caiu o Ollama"))
    servico = AIService(SessaoFalsa(), client=cliente)
    eventos = await coletar(servico.stream(
        "nota da Ana?", usuario_id=__import__("uuid").uuid4(), perfil=Perfil.RESPONSAVEL,
    ))

    assert [e.tipo for e in eventos] == ["delta", "erro"]
    assert eventos[-1].parcial == "A nota foi "
    assert "Ollama" in eventos[-1].erro


async def test_service_stream_recusa_direta_nao_chama_modelo(monkeypatch):
    """Pergunta fora da allowlist vira `done` único, sem gastar inferência."""
    cliente = ClienteFalsoStream(["não deveria chegar aqui"])
    servico = AIService(SessaoFalsa(), client=cliente)
    eventos = await coletar(servico.stream(
        "qual o salário dos professores?",
        usuario_id=__import__("uuid").uuid4(),
        perfil=Perfil.RESPONSAVEL,
    ))

    assert [e.tipo for e in eventos] == ["done"]
    assert cliente.mensagens_recebidas == [], "o modelo não pode ser chamado na recusa"
    assert eventos[0].resposta.codigo in {
        "intencao_nao_permitida", "intencao_nao_reconhecida",
    }
