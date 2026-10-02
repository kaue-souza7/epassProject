"""Configuração e teste de envio SMTP.

Cobre o que quebrava em produção:

1. Porta 465 é TLS implícito — conectar em texto puro nela só produz
   "Connection unexpectedly closed", que é a mensagem que o admin viava e que
   não dizia nada. Agora a combinação é corrigida e o erro explica o motivo.
2. A senha comum da conta é recusada pelo Gmail/Outlook com um texto próprio
   (5.7.9) que precisa virar uma instrução útil, não um "Erro SMTP: ...".
3. O teste do painel usa o mesmo transporte do envio real e roda fora do event
   loop.
"""
import smtplib
import socket
import ssl

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.smtp import abrir_conexao, resolver_config, traduzir_erro
from app.modules.system_config.models import ConfiguracaoSistema

DB_SMTP = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_user": "escola@gmail.com",
    "smtp_password": "abcd efgh ijkl mnop",
    "smtp_from": "escola@gmail.com",
    "smtp_use_tls": "true",
}


# ---------------------------------------------------------------------------
# resolver_config
# ---------------------------------------------------------------------------

def test_porta_465_com_starttls_e_corrigida_para_tls_implicito():
    """A combinação que só podia falhar: 465 não aceita STARTTLS."""
    cfg = resolver_config({**DB_SMTP, "smtp_port": "465", "smtp_use_tls": "true"})

    assert cfg.use_ssl is True
    assert cfg.use_tls is False
    assert cfg.modo == "TLS implícito"


def test_ambos_os_tls_ligados_ganha_o_implicito():
    cfg = resolver_config({**DB_SMTP, "smtp_use_tls": "true", "smtp_use_ssl": "true"})

    assert cfg.use_ssl is True
    assert cfg.use_tls is False


def test_porta_587_preserva_starttls():
    cfg = resolver_config({**DB_SMTP, "smtp_port": "587", "smtp_use_tls": "true"})

    assert cfg.use_tls is True
    assert cfg.use_ssl is False
    assert cfg.modo == "STARTTLS"


def test_sem_criptografia_e_mantida():
    cfg = resolver_config({**DB_SMTP, "smtp_use_tls": "false", "smtp_use_ssl": "false"})

    assert cfg.use_tls is False
    assert cfg.use_ssl is False
    assert cfg.modo == "sem criptografia"


def test_valores_booleanos_sao_lidos_como_string_do_banco():
    """O banco guarda tudo como texto — 'false' não pode virar True."""
    cfg = resolver_config({**DB_SMTP, "smtp_use_tls": "false"})

    assert cfg.use_tls is False


def test_banco_tem_prioridade_sobre_o_env(monkeypatch):
    monkeypatch.setattr("app.core.smtp.settings.SMTP_HOST", "do-env.com", raising=False)
    monkeypatch.setattr("app.core.smtp.settings.SMTP_PASSWORD", "env-pass", raising=False)

    cfg = resolver_config(DB_SMTP)

    assert cfg.host == "smtp.gmail.com"
    assert cfg.password == "abcd efgh ijkl mnop"


def test_campo_vazio_no_banco_cai_no_env(monkeypatch):
    monkeypatch.setattr("app.core.smtp.settings.SMTP_HOST", "do-env.com", raising=False)

    cfg = resolver_config({**DB_SMTP, "smtp_host": "   "})

    assert cfg.host == "do-env.com"


def test_config_incompleta_nao_esta_pronta():
    assert resolver_config({"smtp_host": "smtp.gmail.com"}).completo is False
    assert resolver_config(DB_SMTP).completo is True


# ---------------------------------------------------------------------------
# abrir_conexao
# ---------------------------------------------------------------------------

class _ServidorFalso:
    """Servidor SMTP mínimo que registra o que foi pedido."""

    def __init__(self, *, anuncia_starttls: bool = True) -> None:
        self.annuncia_starttls = anuncia_starttls
        self.chamadas: list[str] = []

    def has_extn(self, nome: str) -> bool:
        return nome == "starttls" and self.annuncia_starttls

    def ehlo(self) -> None:
        self.chamadas.append("ehlo")

    def starttls(self, *, context=None) -> None:
        assert isinstance(context, ssl.SSLContext)
        self.chamadas.append("starttls")

    def close(self) -> None:
        self.chamadas.append("close")


def test_tls_implicito_usa_smtp_ssl(monkeypatch):
    """465 tem que falar TLS no primeiro byte — via SMTP_SSL, não starttls."""
    instanciados: list[dict] = []

    def _fake_ssl(host, port, **kwargs):
        instanciados.append({"host": host, "port": port, **kwargs})
        return _ServidorFalso()

    monkeypatch.setattr(smtplib, "SMTP_SSL", _fake_ssl)
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: pytest.fail("SMTP em claro na 465"))

    cfg = resolver_config({**DB_SMTP, "smtp_port": "465", "smtp_use_tls": "true"})
    abrir_conexao(cfg)

    assert instanciados[0]["host"] == "smtp.gmail.com"
    assert instanciados[0]["port"] == 465
    assert isinstance(instanciados[0]["context"], ssl.SSLContext)


def test_starttls_usa_smtp_com_ehlo_antes_e_depois(monkeypatch):
    servidor = _ServidorFalso()
    monkeypatch.setattr(smtplib, "SMTP_SSL", lambda *a, **k: pytest.fail("SMTP_SSL na 587"))
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: servidor)

    cfg = resolver_config({**DB_SMTP, "smtp_port": "587", "smtp_use_tls": "true"})
    abrir_conexao(cfg)

    # O segundo ehlo é obrigatório: sem ele o servidor continua believing
    # que a conexão está em claro e pode recusar o AUTH.
    assert servidor.chamadas == ["ehlo", "starttls", "ehlo"]


def test_servidor_sem_starttls_apoio_e_erro_traduzido(monkeypatch):
    servidor = _ServidorFalso(anuncia_starttls=False)
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: servidor)

    cfg = resolver_config({**DB_SMTP, "smtp_use_tls": "true"})
    with pytest.raises(smtplib.SMTPNotSupportedError):
        abrir_conexao(cfg)

    # A conexão meio-criada não pode ficar pendurada.
    assert servidor.chamadas == ["ehlo", "close"]


# ---------------------------------------------------------------------------
# traduzir_erro
# ---------------------------------------------------------------------------

def test_desconexao_diz_a_qual_porte_pertence():
    """A regressão principal: a mensagem antiga era só 'Connection unexpectedly closed'."""
    cfg = resolver_config({**DB_SMTP, "smtp_port": "465", "smtp_use_tls": "true"})
    erro = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    mensagem = traduzir_erro(cfg, erro)

    assert "Connection unexpectedly closed" not in mensagem
    assert "465" in mensagem
    assert "TLS implícito" in mensagem
    assert "587" in mensagem


def test_senha_comum_do_gmail_vira_instrucao_uteis():
    cfg = resolver_config(DB_SMTP)
    erro = smtplib.SMTPAuthenticationError(
        534,
        b"5.7.9 Application-specific password required. "
        b"For more information, go to https://support.google.com/mail/?p=InvalidSecondFactor",
    )

    mensagem = traduzir_erro(cfg, erro)

    assert "senha de aplicativo" in mensagem
    assert "2 etapas" in mensagem
    assert "Erro SMTP" not in mensagem


def test_credenciais_rejeitadas_gerais():
    cfg = resolver_config(DB_SMTP)
    erro = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted.")

    mensagem = traduzir_erro(cfg, erro)

    assert "senha de aplicativo" in mensagem
    assert "escola@gmail.com" in mensagem


def test_erro_de_rede_nao_vira_erro_smtp_generico():
    cfg = resolver_config(DB_SMTP)
    erro = OSError("Network is unreachable")

    mensagem = traduzir_erro(cfg, erro)

    assert "Falha de rede" in mensagem
    assert "smtp.gmail.com:587" in mensagem


def test_dns_e_traduzido():
    cfg = resolver_config(DB_SMTP)

    mensagem = traduzir_erro(cfg, socket.gaierror(-2, "Name or service not known"))

    assert "DNS" in mensagem


def test_timeout_nao_e_confundido_com_erro_smtp():
    """TimeoutError é OSError, e SMTPException também — a ordem importa."""
    cfg = resolver_config(DB_SMTP)

    mensagem = traduzir_erro(cfg, TimeoutError("timed out"))

    assert "Tempo esgotado" in mensagem


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

async def _salvar_smtp(client: AsyncClient, **overrides):
    corpo = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "escola@gmail.com",
        "smtp_password": "abcd efgh ijkl mnop",
        "smtp_from": "escola@gmail.com",
        "smtp_use_tls": True,
        "smtp_use_ssl": False,
    }
    corpo.update(overrides)
    return await client.put("/system-config/smtp", json=corpo)


async def test_salva_e_devolve_sem_expor_a_senha(admin_client: AsyncClient):
    resp = await _salvar_smtp(admin_client)

    assert resp.status_code == 200
    assert resp.json()["configured"] is True
    assert resp.json()["smtp_use_ssl"] is False
    assert "smtp_password" not in resp.text
    assert "abcd efgh" not in resp.text


async def test_salvar_sem_senha_mantem_a_que_esta_salva(admin_client: AsyncClient, session):
    """A API nunca devolve a senha, então salvar o host não pode apagá-la."""
    await _salvar_smtp(admin_client)

    await _salvar_smtp(admin_client, smtp_host="smtp.outlook.com", smtp_password=None)

    resp = await admin_client.get("/system-config/smtp")
    assert resp.json()["smtp_host"] == "smtp.outlook.com"
    assert resp.json()["configured"] is True

    salva = await session.execute(
        select(ConfiguracaoSistema.valor).where(ConfiguracaoSistema.chave == "smtp_password"),
    )
    assert salva.scalar_one() == "abcd efgh ijkl mnop"


async def test_tls_implicito_volta_para_o_formulario(admin_client: AsyncClient):
    await _salvar_smtp(admin_client, smtp_port=465, smtp_use_tls=False, smtp_use_ssl=True)

    resp = await admin_client.get("/system-config/smtp")

    assert resp.json()["smtp_use_ssl"] is True
    assert resp.json()["smtp_use_tls"] is False


async def test_teste_sem_configuracao_orienta_o_admin(admin_client: AsyncClient):
    resp = await admin_client.post("/system-config/smtp/test", json={"destinatario": "a@b.com"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["success"] is False
    assert "incompleta" in corpo["message"]


async def test_teste_de_envio_tem_sucesso(admin_client: AsyncClient, monkeypatch):
    await _salvar_smtp(admin_client)
    enviados: list[dict] = []

    def _fake_enviar_mensagem(cfg, destinatario, assunto, corpo_html):
        enviados.append({
            "host": cfg.host, "port": cfg.port, "modo": cfg.modo,
            "destinatario": destinatario, "assunto": assunto,
        })

    monkeypatch.setattr(
        "app.modules.system_config.service.enviar_mensagem", _fake_enviar_mensagem,
    )

    resp = await admin_client.post("/system-config/smtp/test", json={"destinatario": "a@b.com"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["success"] is True
    assert "smtp.gmail.com:587" in corpo["message"]
    assert enviados[0]["modo"] == "STARTTLS"
    assert enviados[0]["destinatario"] == "a@b.com"


async def test_teste_nao_derruba_a_api_quando_o_smtp_cai(admin_client: AsyncClient, monkeypatch):
    """Falha de e-mail tem de virar mensagem, não 500 — o painel sempre mostra
    o retorno."""
    await _salvar_smtp(admin_client)

    def _explode(*args, **kwargs):
        raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    monkeypatch.setattr("app.modules.system_config.service.enviar_mensagem", _explode)

    resp = await admin_client.post("/system-config/smtp/test", json={"destinatario": "a@b.com"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["success"] is False
    assert "Erro SMTP: Connection unexpectedly closed" not in corpo["message"]
    assert "465" in corpo["message"]


async def test_teste_usa_o_mesmo_transporte_do_envio_real(admin_client: AsyncClient, monkeypatch):
    """O painel e as notificações precisam falar com o servidor do mesmo jeito —
    foi a divergência entre as duas cópias do smtplib que deixou a 465
    impossível de configurar."""
    await _salvar_smtp(admin_client, smtp_port=465, smtp_use_tls=False, smtp_use_ssl=True)
    modos: list[str] = []

    def _fake(cfg, destinatario, assunto, corpo_html):
        modos.append(cfg.modo)
        abrir_conexao(cfg)

    monkeypatch.setattr("app.modules.system_config.service.enviar_mensagem", _fake)
    monkeypatch.setattr(smtplib, "SMTP_SSL", lambda *a, **k: _ServidorFalso())
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: pytest.fail("SMTP em claro na 465"))

    resp = await admin_client.post("/system-config/smtp/test", json={"destinatario": "a@b.com"})

    assert resp.json()["success"] is True
    assert modos == ["TLS implícito"]


async def test_salvar_tls_implicito_com_starttls_marcado_e_corrigido(admin_client: AsyncClient):
    """Configuração contraditória salva pela tela não pode produzir um erro
    indecifrável."""
    await _salvar_smtp(admin_client, smtp_port=465, smtp_use_tls=True, smtp_use_ssl=False)

    resp = await admin_client.get("/system-config/smtp")

    assert resp.json()["smtp_use_ssl"] is True
    assert resp.json()["smtp_use_tls"] is False
