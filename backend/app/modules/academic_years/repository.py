from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic_years.models import AnoLetivo


class AnoLetivoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> AnoLetivo | None:
        result = await self._session.execute(
            select(AnoLetivo).where(AnoLetivo.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_ano(self, ano: int) -> AnoLetivo | None:
        result = await self._session.execute(
            select(AnoLetivo).where(AnoLetivo.ano == ano),
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> AnoLetivo | None:
        result = await self._session.execute(
            select(AnoLetivo).where(AnoLetivo.ativo.is_(True)),
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[AnoLetivo]:
        result = await self._session.execute(
            select(AnoLetivo).order_by(AnoLetivo.ano.desc()),
        )
        return list(result.scalars().all())

    async def exists_by_ano(self, ano: int) -> bool:
        result = await self._session.execute(
            select(AnoLetivo.id).where(AnoLetivo.ano == ano).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def create(self, ano_letivo: AnoLetivo) -> AnoLetivo:
        self._session.add(ano_letivo)
        await self._session.flush()
        return ano_letivo

    async def update(self, ano_letivo: AnoLetivo) -> AnoLetivo:
        ano_letivo.updated_at = datetime.now(timezone.utc)
        self._session.add(ano_letivo)
        await self._session.flush()
        return ano_letivo
