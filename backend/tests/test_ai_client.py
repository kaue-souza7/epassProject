"""Testes do OllamaClient — resiliência (Fase 1).

Cobre: Ollama indisponível, modelo ausente, timeout, retry com backoff, circuit
breaker, limite de concorrência, health e ausência de acesso a banco.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.modules.ai.exceptions import (
    IADisponivelErro,
    LimiteConcorrenciaErro,
    ModeloNaoEncontradoErro,
)
from app.modules.ai.ollama_client import CircuitAbertoErro, OllamaClient

BASE = "http://ollama:11434"


def make_config(**overrides) -> SimpleNamespace:
    """Configuração isolada por teste (não depende de .env da máquina)."""
    base = {
        "AI_ENABLED": True,
        "OLLAMA_BASE_URL": BASE,
        "OLLAMA_MODEL": "qwen3:4b",
        "OLLAMA_TIMEOUT": 2,
        "OLLAMA_CONNECT_TIMEOUT": 1,
        "OLLAMA_HEALTH_TIMEOUT": 1,
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
        "OLLAMA_STREAM_READ_TIMEOUT": 2,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def resposta_ok(conteudo: str = "A nota foi 8,50.") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "qwen3:4b",
            "message": {"role": "assistant", "content": conteudo},
            "prompt_eval_count": 120,
            "eval_count": 30,
        },
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@respx.mock
async def test_health_ok_quando_modelo_presente():
    respx.get(f"{BASE}/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "qwen3:4b"}]}),
    )
    saude = await OllamaClient(make_config()).health()
    assert saude.ollama_alive is True
    assert saude.model_present is True
    assert saude.model == "qwen3:4b"


@respx.mock
async def test_health_degraded_quando_modelo_ausente():
    respx.get(f"{BASE}/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "llama3.2:1b"}]}),
    )
    saude = await OllamaClient(make_config()).health()
    assert saude.ollama_alive is True
    assert saude.model_present is False
    assert "ausente" in saude.detail


@respx.mock
async def test_health_unavailable_quando_ollama_fora_do_ar():
    respx.get(f"{BASE}/api/tags").mock(side_effect=httpx.ConnectError("recusado"))
    saude = await OllamaClient(make_config()).health()
    assert saude.ollama_alive is False
    assert saude.model_present is False


async def test_health_quando_ia_desabilitada():
    saude = await OllamaClient(make_config(AI_ENABLED=False)).health()
    assert saude.ollama_alive is False
    assert "desabilitada" in saude.detail


# ---------------------------------------------------------------------------
# Chat: caminho feliz e erros
# ---------------------------------------------------------------------------
@respx.mock
async def test_chat_retorna_conteudo_normalizado():
    rota = respx.post(f"{BASE}/api/chat").mock(return_value=resposta_ok())
    resultado = await OllamaClient(make_config()).chat(
        [{"role": "user", "content": "qual a nota?"}],
    )
    assert resultado.conteudo == "A nota foi 8,50."
    assert resultado.tokens_prompt == 120
    assert resultado.tokens_completion == 30
    assert rota.called


@respx.mock
async def test_chat_nao_envia_tools_ao_modelo():
    """A IA não pode executar nada: nada de tool calling no payload."""
    respx.post(f"{BASE}/api/chat").mock(return_value=resposta_ok())
    await OllamaClient(make_config()).chat([{"role": "user", "content": "oi"}])

    enviado = respx.calls[0].request
    assert b'"tools"' not in enviado.content


@respx.mock
async def test_chat_modelo_ausente_levanta_erro_dedicado():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(404, json={"error": "model not found"}),
    )
    with pytest.raises(ModeloNaoEncontradoErro):
        await OllamaClient(make_config()).chat([{"role": "user", "content": "oi"}])


@respx.mock
async def test_chat_timeout_vira_erro_de_dominio():
    respx.post(f"{BASE}/api/chat").mock(side_effect=httpx.ReadTimeout("estourou"))
    with pytest.raises(IADisponivelErro):
        await OllamaClient(make_config()).chat([{"role": "user", "content": "oi"}])


@respx.mock
async def test_chat_ia_desabilitada_nao_chama_rede():
    with pytest.raises(IADisponivelErro):
        await OllamaClient(make_config(AI_ENABLED=False)).chat(
            [{"role": "user", "content": "oi"}],
        )


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------
@respx.mock
async def test_retry_apos_falha_transitoria():
    rota = respx.post(f"{BASE}/api/chat")
    rota.side_effect = [
        httpx.Response(503, json={"error": "overloaded"}),
        resposta_ok("ok após retry"),
    ]
    resultado = await OllamaClient(make_config()).chat(
        [{"role": "user", "content": "oi"}],
    )
    assert resultado.conteudo == "ok após retry"
    assert rota.call_count == 2


@respx.mock
async def test_retry_esgota_e_propaga_erro():
    rota = respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(503, json={"error": "overloaded"}),
    )
    with pytest.raises(IADisponivelErro):
        await OllamaClient(make_config()).chat([{"role": "user", "content": "oi"}])
    # 1 tentativa inicial + 2 retries
    assert rota.call_count == 3


@respx.mock
async def test_modelo_ausente_nao_gera_retry():
    """404 é erro de configuração, não transitório: repetir não instala o modelo."""
    rota = respx.post(f"{BASE}/api/chat").mock(return_value=httpx.Response(404, json={}))
    with pytest.raises(ModeloNaoEncontradoErro):
        await OllamaClient(make_config()).chat([{"role": "user", "content": "oi"}])
    assert rota.call_count == 1


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
@respx.mock
async def test_circuito_abre_apos_n_falhas_e_bloqueia_tentativas():
    respx.post(f"{BASE}/api/chat").mock(return_value=httpx.Response(503, json={}))
    client = OllamaClient(make_config(OLLAMA_RETRY_ATTEMPTS=0, OLLAMA_CIRCUIT_FAILURES=2))

    for _ in range(2):
        with pytest.raises(IADisponivelErro):
            await client.chat([{"role": "user", "content": "oi"}])

    estado = await client.estado_circuito()
    assert estado["circuito"] == "aberto"
    assert estado["reabrir_em_s"] > 0

    # Com o circuito aberto, NÃO há nova chamada de rede.
    chamadas = respx.calls.call_count
    with pytest.raises(CircuitAbertoErro):
        await client.chat([{"role": "user", "content": "oi"}])
    assert respx.calls.call_count == chamadas


@respx.mock
async def test_circuito_fecha_apos_sucesso():
    rota = respx.post(f"{BASE}/api/chat")
    rota.side_effect = [httpx.Response(503, json={}), resposta_ok("ok")]

    client = OllamaClient(make_config(OLLAMA_RETRY_ATTEMPTS=0, OLLAMA_CIRCUIT_FAILURES=1))
    with pytest.raises(IADisponivelErro):
        await client.chat([{"role": "user", "content": "oi"}])
    assert (await client.estado_circuito())["circuito"] == "aberto"

    # Force a reabertura (half-open) encurtando o reset.
    client._estado.aberto_em -= 999
    resultado = await client.chat([{"role": "user", "content": "oi"}])
    assert resultado.conteudo == "ok"
    assert (await client.estado_circuito())["circuito"] == "fechado"


# ---------------------------------------------------------------------------
# Concorrência
# ---------------------------------------------------------------------------
@respx.mock
async def test_segunda_inferencia_concorrente_e_recusada():
    """Com RAM limitada, a 2ª pergunta simultânea falha rápido em vez de enfileirar."""
    liberado = asyncio.Event()

    async def resposta_lenta(_request):
        await liberado.wait()
        return resposta_ok("ok")

    respx.post(f"{BASE}/api/chat").mock(side_effect=resposta_lenta)
    client = OllamaClient(make_config(OLLAMA_MAX_CONCURRENCY=1))

    primeira = asyncio.create_task(client.chat([{"role": "user", "content": "1"}]))
    await asyncio.sleep(0.05)

    with pytest.raises(LimiteConcorrenciaErro):
        await client.chat([{"role": "user", "content": "2"}])

    liberado.set()
    assert (await primeira).conteudo == "ok"


# ---------------------------------------------------------------------------
# Garantia estrutural de isolamento
# ---------------------------------------------------------------------------
def test_cliente_nao_importa_banco_de_dados():
    """O cliente do Ollama não pode conhecer o PostgreSQL.

    É a garantia estrutural (e não apenas convencional) de que a camada de IA
    não consulta dados: se alguém precisar do banco, o import vai quebrar aqui.
    """
    import ast
    import pathlib

    caminho = pathlib.Path(__file__).resolve().parents[1] / "app/modules/ai/ollama_client.py"
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))

    forbidden = ("app.database", "sqlalchemy", "app.modules.students", "psycopg", "asyncpg")
    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)

    vazamentos = [m for m in importados if any(m.startswith(f) for f in forbidden)]
    assert not vazamentos, f"ollama_client não pode importar: {vazamentos}"
