from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.series.models import Serie


class SerieRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Serie | None:
        result = await self._session.execute(
            select(Serie).where(Serie.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_numero(self, numero: int) -> Serie | None:
        result = await self._session.execute(
            select(Serie).where(Serie.numero == numero),
        )
        return result.scalar_one_or_none()

    async def get_all(self, only_active: bool = False) -> list[Serie]:
        query = select(Serie).order_by(Serie.numero)
        if only_active:
            query = query.where(Serie.ativo.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create(self, serie: Serie) -> Serie:
        self._session.add(serie)
        await self._session.flush()
        return serie

    async def update(self, serie: Serie) -> Serie:
        serie.updated_at = datetime.now(timezone.utc)
        self._session.add(serie)
        await self._session.flush()
        return serie
