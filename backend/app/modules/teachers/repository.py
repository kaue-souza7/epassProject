from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.teachers.models import ProfessorProfile
from app.modules.users.models import Usuario


class ProfessorProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_usuario(self, usuario_id: uuid.UUID) -> ProfessorProfile | None:
        result = await self._session.execute(
            select(ProfessorProfile).where(ProfessorProfile.usuario_id == usuario_id),
        )
        return result.scalar_one_or_none()

    async def get_by_matricula(self, matricula: str) -> ProfessorProfile | None:
        result = await self._session.execute(
            select(ProfessorProfile).where(ProfessorProfile.matricula_funcional == matricula),
        )
        return result.scalar_one_or_none()

    async def get_all(self, only_active: bool = False) -> list[ProfessorProfile]:
        query = select(ProfessorProfile).order_by(ProfessorProfile.usuario_id)
        if only_active:
            query = query.where(ProfessorProfile.ativo.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def search(
        self,
        nome: str | None = None,
        matricula_funcional: str | None = None,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ProfessorProfile], int]:
        query = (
            select(ProfessorProfile)
            .join(Usuario, ProfessorProfile.usuario_id == Usuario.id)
        )

        if nome:
            query = query.where(Usuario.nome.ilike(f"%{nome}%"))
        if matricula_funcional:
            query = query.where(ProfessorProfile.matricula_funcional.ilike(f"%{matricula_funcional}%"))
        if only_active:
            query = query.where(ProfessorProfile.ativo.is_(True))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Usuario.nome).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create(self, profile: ProfessorProfile) -> ProfessorProfile:
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def update(self, profile: ProfessorProfile) -> ProfessorProfile:
        profile.updated_at = datetime.now(timezone.utc)
        self._session.add(profile)
        await self._session.flush()
        return profile
