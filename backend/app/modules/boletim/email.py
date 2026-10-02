from __future__ import annotations

import logging

from app.core.smtp import SmtpConfig, enviar_mensagem, resolver_config, traduzir_erro

logger = logging.getLogger(__name__)


def enviar_email(
    destinatario: str,
    assunto: str,
    corpo_html: str,
    smtp_config: dict[str, str | None] | None = None,
) -> bool:
    """Envia um e-mail e devolve `False` em vez de estourar a exceção.

    Os chamadores (notificações, agenda de boletins) precisam que uma falha de
    e-mail não derrube o fluxo que a disparou.
    """
    cfg: SmtpConfig = resolver_config(smtp_config)
    if not cfg.completo:
        logger.warning("SMTP não configurado — e-mail não enviado para %s", destinatario)
        return False

    try:
        enviar_mensagem(cfg, destinatario, assunto, corpo_html)
    except Exception as erro:
        logger.warning(
            "Falha ao enviar e-mail para %s: %s", destinatario, traduzir_erro(cfg, erro),
        )
        logger.debug("Detalhe do erro de SMTP", exc_info=True)
        return False

    logger.info("E-mail enviado para %s: %s", destinatario, assunto)
    return True
