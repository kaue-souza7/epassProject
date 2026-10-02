"""Transporte SMTP compartilhado.

Existe um único lugar que sabe falar SMTP. O teste do painel e o envio real
(`boletim/email.py`) usam exatamente o mesmo handshake — antes cada um tinha
uma cópia própria do `smtplib`, e foi por causa dessa duplicação que a porta
465 (TLS implícito) era impossível de configurar: as duas cópias faziam só
`SMTP()` + `starttls()`, que é o modo errado naquela porta.
"""

from __future__ import annotations

import logging
import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

SMTP_TIMEOUT = 30

# 465 é, por definição, TLS implícito: o servidor espera o handshake
# criptográfico já no primeiro byte. Conectar em texto puro e só descobrir
# isso depois é exatamente o que produz "Connection unexpectedly closed".
PORTA_TLS_IMPLICITO = 465

_VERDADEIRO = {"true", "1", "yes", "y", "on", "sim"}
_FALSO = {"false", "0", "no", "n", "off", "nao", "não"}


@dataclass(frozen=True)
class SmtpConfig:
    """Configuração efetiva de saída de e-mail."""

    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    verify_ssl: bool = True
    timeout: int = SMTP_TIMEOUT

    @property
    def completo(self) -> bool:
        return bool(self.host and self.user and self.password and self.from_addr)

    @property
    def endereco(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def modo(self) -> str:
        if self.use_ssl:
            return "TLS implícito"
        if self.use_tls:
            return "STARTTLS"
        return "sem criptografia"


def _texto(valor: str | None) -> str:
    return (valor or "").strip()


def _booleano(valor: str | None, padrao: bool) -> bool:
    normalizado = _texto(valor).lower()
    if normalizado in _VERDADEIRO:
        return True
    if normalizado in _FALSO:
        return False
    return padrao


def _inteiro(valor: str | None, padrao: int) -> int:
    try:
        return int(_texto(valor))
    except (TypeError, ValueError):
        return padrao


def resolver_config(smtp_config: dict[str, str | None] | None) -> SmtpConfig:
    """Monta a config efetiva: o que está salvo no banco tem prioridade e o que
    falta cai no `.env`."""
    dados: dict[str, str | None] = smtp_config or {}

    def do_banco(chave: str) -> str | None:
        return _texto(dados.get(chave)) or None

    host = do_banco("smtp_host") or _texto(settings.SMTP_HOST)
    port = _inteiro(do_banco("smtp_port"), settings.SMTP_PORT)
    user = do_banco("smtp_user") or _texto(settings.SMTP_USER)
    password = do_banco("smtp_password") or _texto(settings.SMTP_PASSWORD)
    from_addr = do_banco("smtp_from") or _texto(settings.SMTP_FROM)
    use_tls = _booleano(do_banco("smtp_use_tls"), settings.SMTP_USE_TLS)
    use_ssl = _booleano(do_banco("smtp_use_ssl"), settings.SMTP_USE_SSL)
    verify_ssl = _booleano(do_banco("smtp_verify_ssl"), settings.SMTP_VERIFY_SSL)

    if use_ssl and use_tls:
        # STARTTLS sobre uma conexão já criptografada não quer dizer nada; o
        # implícito vence porque é o que a porta 465 espera.
        logger.warning("SMTP %s: TLS implícito e STARTTLS juntos — usando TLS implícito.", host)
        use_tls = False

    if use_tls and port == PORTA_TLS_IMPLICITO:
        # Configuração que só podia falhar: 465 não aceita STARTTLS. Vale
        # corrigir em vez de devolver um erro que o admin não consegue
        # decifrar ("Connection unexpectedly closed").
        logger.warning(
            "SMTP %s: a porta %d é TLS implícito, mas a configuração pede STARTTLS — corrigindo.",
            host, port,
        )
        use_tls, use_ssl = False, True

    return SmtpConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        from_addr=from_addr,
        use_tls=use_tls,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
    )


def _contexto_ssl(cfg: SmtpConfig) -> ssl.SSLContext:
    if cfg.verify_ssl:
        return ssl.create_default_context()
    # Escape hatch para servidor on-premise com certificado self-signed. Não é
    # o padrão de propósito: sem isso, qualquer um no caminho da rede lê a
    # senha do SMTP em claro.
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    return contexto


def abrir_conexao(cfg: SmtpConfig) -> smtplib.SMTP:
    """Abre a sessão SMTP já no modo de criptografia pedido."""
    contexto = _contexto_ssl(cfg)

    if cfg.use_ssl:
        # TLS implícito: o handshake acontece antes de qualquer comando SMTP.
        return smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=cfg.timeout, context=contexto)

    server = smtplib.SMTP(cfg.host, cfg.port, timeout=cfg.timeout)
    try:
        server.ehlo()
        if cfg.use_tls:
            if not server.has_extn("starttls"):
                raise smtplib.SMTPNotSupportedError("o servidor não anuncia a extensão STARTTLS")
            server.starttls(context=contexto)
            server.ehlo()
    except BaseException:
        # `starttls` envolve a conexão existente: se ele estoura, o objeto
        # original fica pendurado e o socket vaza.
        server.close()
        raise
    return server


def enviar_mensagem(
    cfg: SmtpConfig,
    destinatario: str,
    assunto: str,
    corpo_html: str,
) -> None:
    """Envia um e-mail. Deixa a exceção propagar — quem chama decide o que fazer
    com ela."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Sistema ePass <{cfg.from_addr}>"
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo_html, "html"))

    with abrir_conexao(cfg) as server:
        if cfg.user:
            server.login(cfg.user, cfg.password)
        server.sendmail(cfg.from_addr, [destinatario], msg.as_string())


def _detalhar_autenticacao(cfg: SmtpConfig, erro: smtplib.SMTPAuthenticationError) -> str:
    detalhe = str(erro).lower()
    if "application-specific password" in detalhe or "5.7.9" in detalhe:
        return (
            f"O servidor recusou '{cfg.user}' e exige senha de aplicativo — a senha comum "
            "da conta não serve. No Gmail/Outlook: ative a verificação em 2 etapas, gere "
            "uma senha de app para o cliente de e-mail, copie sem espaços e salve abaixo."
        )
    return (
        f"Usuário ou senha recusados pelo servidor para '{cfg.user}'. Confira o e-mail em "
        "'Usuário' e use a senha de aplicativo, não a senha da conta."
    )


def traduzir_erro(cfg: SmtpConfig, erro: BaseException) -> str:
    """Converte a exceção do `smtplib` numa mensagem que o admin consegue agir.

    A ordem importa: no CPython `SMTPException` herda de `OSError` e
    `SMTPServerDisconnected` herda de `SMTPException` e `ConnectionError`, então
    um `except` genérico primeiro — ou um `isinstance(..., OSError)` cedo —
    transforma todo erro SMTP em "Erro inesperado".
    """
    if isinstance(erro, smtplib.SMTPAuthenticationError):
        return _detalhar_autenticacao(cfg, erro)

    if isinstance(erro, smtplib.SMTPNotSupportedError):
        return (
            f"O servidor {cfg.endereco} não aceita STARTTLS. Troque a criptografia para "
            "'SSL/TLS implícito' (porta 465) ou 'Sem criptografia'."
        )

    if isinstance(erro, smtplib.SMTPServerDisconnected):
        return (
            f"O servidor {cfg.endereco} encerrou a conexão durante o handshake "
            f"(modo atual: {cfg.modo}). Porta {cfg.port} não combina com esse modo: "
            "use 'SSL/TLS implícito' na 465 e 'TLS/STARTTLS' na 587."
        )

    if isinstance(erro, smtplib.SMTPConnectError):
        return (
            f"Não foi possível conectar em {cfg.endereco}. Verifique o servidor, a porta e "
            "se o container do backend tem acesso à rede externa."
        )

    if isinstance(erro, smtplib.SMTPRecipientsRefused):
        # `recipients` mapeia endereço -> (código, mensagem): quem interessa é a chave.
        return f"O servidor recusou o destinatário {', '.join(erro.recipients)}."

    if isinstance(erro, smtplib.SMTPSenderRefused):
        return (
            f"O servidor recusou o remetente {cfg.from_addr}. O e-mail em 'Remetente' "
            "precisa ser uma conta autorizada no servidor SMTP."
        )

    if isinstance(erro, smtplib.SMTPResponseException):
        return f"O servidor {cfg.endereco} recusou a operação: {erro}"

    if isinstance(erro, socket.gaierror):
        return f"Servidor SMTP '{cfg.host}' não encontrado (falha de DNS)."

    if isinstance(erro, ssl.SSLCertVerificationError):
        return (
            f"Certificado TLS inválido em {cfg.endereco}: {erro.verify_message or erro}. "
            "Instale a CA do servidor no container ou use um servidor com certificado válido."
        )

    if isinstance(erro, ssl.SSLError):
        return f"Falha no TLS com {cfg.endereco}: {erro}."

    if isinstance(erro, smtplib.SMTPException):
        return f"Erro SMTP em {cfg.endereco}: {erro}"

    if isinstance(erro, TimeoutError):
        return f"Tempo esgotado ({cfg.timeout}s) ao falar com {cfg.endereco}."

    # Vem depois de todos os SMTP: `SMTPException` é subclasse de `OSError`.
    if isinstance(erro, OSError):
        return f"Falha de rede ao falar com {cfg.endereco}: {erro}"

    return f"Erro inesperado ao enviar e-mail: {erro}"
