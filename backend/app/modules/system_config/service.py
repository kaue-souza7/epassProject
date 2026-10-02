from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.smtp import enviar_mensagem, resolver_config, traduzir_erro
from app.modules.system_config.repository import ConfiguracaoSistemaRepository
from app.modules.system_config.schemas import (
    AvisoConfigRequest,
    AvisoConfigResponse,
    SmtpConfigRequest,
    SmtpConfigResponse,
    SmtpTestRequest,
    SmtpTestResponse,
)

logger = logging.getLogger(__name__)

AVISO_ESCALONAMENTO_KEY = "aviso_escalonamento_horas"
AVISO_ESCALONAMENTO_PADRAO = 24

CORPO_TESTE_HTML = (
    "<html><body><h2>Configuração SMTP - ePass</h2>"
    "<p>Este é um e-mail de teste. Se você recebeu esta mensagem, "
    "a configuração SMTP está funcionando corretamente.</p></body></html>"
)


class SystemConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ConfiguracaoSistemaRepository(session)

    async def get_smtp_config(self) -> SmtpConfigResponse:
        data = await self._repo.get_all_smtp()
        cfg = resolver_config(data)
        return SmtpConfigResponse(
            smtp_host=cfg.host or None,
            smtp_port=cfg.port or None,
            smtp_user=cfg.user or None,
            smtp_from=cfg.from_addr or None,
            smtp_use_tls=cfg.use_tls,
            smtp_use_ssl=cfg.use_ssl,
            configured=cfg.completo,
        )

    async def save_smtp_config(self, body: SmtpConfigRequest) -> SmtpConfigResponse:
        data: dict[str, str | None] = {
            "smtp_host": body.smtp_host,
            "smtp_port": str(body.smtp_port),
            "smtp_user": body.smtp_user,
            "smtp_from": body.smtp_from,
            "smtp_use_tls": "true" if body.smtp_use_tls else "false",
            "smtp_use_ssl": "true" if body.smtp_use_ssl else "false",
        }
        # A senha não volta da API, então saves seguidos não podem apagá-la.
        if body.smtp_password:
            data["smtp_password"] = body.smtp_password
        await self._repo.set_many(data)
        return await self.get_smtp_config()

    async def get_aviso_config(self) -> AvisoConfigResponse:
        valor = await self._repo.get(AVISO_ESCALONAMENTO_KEY)
        try:
            horas = int(valor) if valor is not None else AVISO_ESCALONAMENTO_PADRAO
        except ValueError:
            horas = AVISO_ESCALONAMENTO_PADRAO
        return AvisoConfigResponse(escalonamento_horas=horas)

    async def save_aviso_config(self, body: AvisoConfigRequest) -> AvisoConfigResponse:
        await self._repo.set(AVISO_ESCALONAMENTO_KEY, str(body.escalonamento_horas))
        return AvisoConfigResponse(escalonamento_horas=body.escalonamento_horas)

    async def test_smtp(self, body: SmtpTestRequest) -> SmtpTestResponse:
        cfg = resolver_config(await self._repo.get_all_smtp())
        if not cfg.completo:
            return SmtpTestResponse(
                success=False,
                message=(
                    "Configuração SMTP incompleta. Preencha servidor, porta, "
                    "usuário, senha e remetente."
                ),
            )

        try:
            # `smtplib` é bloqueante: na thread, o event loop continua
            # respondendo as outras requisições durante o handshake.
            await asyncio.to_thread(
                enviar_mensagem,
                cfg,
                body.destinatario,
                "[ePass] Teste de configuração SMTP",
                CORPO_TESTE_HTML,
            )
        except Exception as erro:
            logger.warning("Teste de SMTP falhou (%s): %s", cfg.endereco, traduzir_erro(cfg, erro))
            logger.debug("Detalhe do erro de SMTP", exc_info=True)
            return SmtpTestResponse(success=False, message=traduzir_erro(cfg, erro))

        logger.info("E-mail de teste enviado para %s via %s", body.destinatario, cfg.endereco)
        return SmtpTestResponse(
            success=True,
            message=(
                f"E-mail de teste enviado com sucesso para {body.destinatario} "
                f"via {cfg.endereco} ({cfg.modo})."
            ),
        )
