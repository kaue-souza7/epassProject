from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.classes.models import Turma


class TurmaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Turma | None:
        result = await self._session.execute(
            select(Turma).where(Turma.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_codigo_and_ano(
        self, codigo: str, ano_letivo_id: uuid.UUID,
    ) -> Turma | None:
        result = await self._session.execute(
            select(Turma).where(
                and_(
                    Turma.codigo == codigo,
                    Turma.ano_letivo_id == ano_letivo_id,
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def exists_by_serie_turno_ano(
        self, serie_id: uuid.UUID, turno: str, ano_letivo_id: uuid.UUID,
    ) -> bool:
        result = await self._session.execute(
            select(Turma.id).where(
                and_(
                    Turma.serie_id == serie_id,
                    Turma.turno == turno,
                    Turma.ano_letivo_id == ano_letivo_id,
                ),
            ).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_serie(self, serie_id: uuid.UUID) -> list[Turma]:
        result = await self._session.execute(
            select(Turma).where(Turma.serie_id == serie_id).order_by(Turma.codigo),
        )
        return list(result.scalars().all())

    async def get_by_ano_letivo(self, ano_letivo_id: uuid.UUID) -> list[Turma]:
        result = await self._session.execute(
            select(Turma).where(Turma.ano_letivo_id == ano_letivo_id).order_by(Turma.codigo),
        )
        return list(result.scalars().all())

    async def get_all(self, only_active: bool = False) -> list[Turma]:
        query = select(Turma).order_by(Turma.codigo)
        if only_active:
            query = query.where(Turma.ativo.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def search_paginated(
        self,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Turma], int]:
        query = select(Turma)

        if only_active:
            query = query.where(Turma.ativo.is_(True))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Turma.codigo).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create(self, turma: Turma) -> Turma:
        self._session.add(turma)
        await self._session.flush()
        return turma

    async def update(self, turma: Turma) -> Turma:
        turma.updated_at = datetime.now(timezone.utc)
        self._session.add(turma)
        await self._session.flush()
        return turma
