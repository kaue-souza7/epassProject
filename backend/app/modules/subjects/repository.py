from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subjects.models import Disciplina


class DisciplinaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Disciplina | None:
        result = await self._session.execute(
            select(Disciplina).where(Disciplina.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_codigo(self, codigo: str) -> Disciplina | None:
        result = await self._session.execute(
            select(Disciplina).where(Disciplina.codigo == codigo),
        )
        return result.scalar_one_or_none()

    async def get_by_nome(self, nome: str) -> Disciplina | None:
        result = await self._session.execute(
            select(Disciplina).where(Disciplina.nome == nome),
        )
        return result.scalar_one_or_none()

    async def get_all(self, only_active: bool = False) -> list[Disciplina]:
        query = select(Disciplina).order_by(Disciplina.nome)
        if only_active:
            query = query.where(Disciplina.ativo.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create(self, disciplina: Disciplina) -> Disciplina:
        self._session.add(disciplina)
        await self._session.flush()
        return disciplina

    async def update(self, disciplina: Disciplina) -> Disciplina:
        disciplina.updated_at = datetime.now(timezone.utc)
        self._session.add(disciplina)
        await self._session.flush()
        return disciplina
