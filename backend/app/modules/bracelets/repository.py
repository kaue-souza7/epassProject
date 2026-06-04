from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bracelets.models import Bracelet


class BraceletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Bracelet | None:
        result = await self._session.execute(
            select(Bracelet).where(Bracelet.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_uid(self, uid: str) -> Bracelet | None:
        result = await self._session.execute(
            select(Bracelet).where(Bracelet.uid == uid),
        )
        return result.scalar_one_or_none()

    async def get_by_aluno_id(self, aluno_id: uuid.UUID) -> Bracelet | None:
        result = await self._session.execute(
            select(Bracelet).where(Bracelet.aluno_id == aluno_id),
        )
        return result.scalar_one_or_none()

    async def search_paginated(
        self,
        status: str | None = None,
        tem_aluno: bool | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Bracelet], int]:
        query = select(Bracelet)

        if status:
            query = query.where(Bracelet.status == status)
        if tem_aluno is True:
            query = query.where(Bracelet.aluno_id.isnot(None))
        elif tem_aluno is False:
            query = query.where(Bracelet.aluno_id.is_(None))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Bracelet.created_at.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def exists_by_uid(self, uid: str) -> bool:
        result = await self._session.execute(
            select(Bracelet.id).where(Bracelet.uid == uid).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def exists_by_aluno(self, aluno_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(Bracelet.id).where(Bracelet.aluno_id == aluno_id).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def create(self, bracelet: Bracelet) -> Bracelet:
        self._session.add(bracelet)
        await self._session.flush()
        return bracelet

    async def update(self, bracelet: Bracelet) -> Bracelet:
        bracelet.updated_at = datetime.now(timezone.utc)
        self._session.add(bracelet)
        await self._session.flush()
        return bracelet
