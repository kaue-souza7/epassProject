from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system_config.models import ConfiguracaoSistema


class ConfiguracaoSistemaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    SMTP_KEYS = [
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "smtp_from",
        "smtp_use_tls",
        "smtp_use_ssl",
    ]

    async def get(self, chave: str) -> str | None:
        result = await self._session.execute(
            select(ConfiguracaoSistema).where(ConfiguracaoSistema.chave == chave),
        )
        config = result.scalar_one_or_none()
        return config.valor if config else None

    async def get_all_smtp(self) -> dict[str, str | None]:
        result = await self._session.execute(
            select(ConfiguracaoSistema).where(
                ConfiguracaoSistema.chave.in_(self.SMTP_KEYS),
            ),
        )
        rows = {row.chave: row.valor for row in result.scalars().all()}
        return {k: rows.get(k) for k in self.SMTP_KEYS}

    async def set(self, chave: str, valor: str | None) -> None:
        result = await self._session.execute(
            select(ConfiguracaoSistema).where(ConfiguracaoSistema.chave == chave),
        )
        config = result.scalar_one_or_none()
        now = datetime.now(UTC).replace(tzinfo=None)
        if config:
            config.valor = valor
            config.updated_at = now
        else:
            config = ConfiguracaoSistema(chave=chave, valor=valor, created_at=now, updated_at=now)
            self._session.add(config)
        await self._session.flush()

    async def set_many(self, data: dict[str, str | None]) -> None:
        for chave, valor in data.items():
            await self.set(chave, valor)
