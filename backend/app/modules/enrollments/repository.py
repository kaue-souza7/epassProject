from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrollments.models import Matricula
from app.modules.students.models import Aluno
from app.modules.classes.models import Turma
from app.shared.enums import StatusMatricula


class MatriculaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Matricula | None:
        result = await self._session.execute(
            select(Matricula).where(Matricula.id == id),
        )
        return result.scalar_one_or_none()

    async def get_active_by_aluno(self, aluno_id: uuid.UUID) -> Matricula | None:
        result = await self._session.execute(
            select(Matricula).where(
                and_(
                    Matricula.aluno_id == aluno_id,
                    Matricula.status == "ativa",
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_aluno(self, aluno_id: uuid.UUID) -> list[Matricula]:
        result = await self._session.execute(
            select(Matricula)
            .where(Matricula.aluno_id == aluno_id)
            .order_by(Matricula.data_matricula.desc()),
        )
        return list(result.scalars().all())

    async def get_by_turma(self, turma_id: uuid.UUID) -> list[Matricula]:
        result = await self._session.execute(
            select(Matricula)
            .where(Matricula.turma_id == turma_id)
            .order_by(Matricula.data_matricula),
        )
        return list(result.scalars().all())

    async def count_active_by_turma(self, turma_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(Matricula.id)).where(
                and_(
                    Matricula.turma_id == turma_id,
                    Matricula.status == "ativa",
                ),
            ),
        )
        return result.scalar_one()

    async def search(
        self,
        aluno_id: uuid.UUID | None = None,
        turma_id: uuid.UUID | None = None,
        status: StatusMatricula | None = None,
        aluno_ids: list[uuid.UUID] | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[tuple[Matricula, str, str]], int]:
        query = (
            select(Matricula, Aluno.nome, Turma.codigo)
            .join(Aluno, Matricula.aluno_id == Aluno.id)
            .join(Turma, Matricula.turma_id == Turma.id)
        )

        if aluno_id:
            query = query.where(Matricula.aluno_id == aluno_id)
        if aluno_ids is not None:
            query = query.where(Matricula.aluno_id.in_(aluno_ids))
        if turma_id:
            query = query.where(Matricula.turma_id == turma_id)
        if status:
            query = query.where(Matricula.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Matricula.data_matricula.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        rows = result.all()

        return [(row.Matricula, row.nome, row.codigo) for row in rows], total

    async def create(self, matricula: Matricula) -> Matricula:
        self._session.add(matricula)
        await self._session.flush()
        return matricula

    async def update(self, matricula: Matricula) -> Matricula:
        matricula.updated_at = datetime.now(timezone.utc)
        self._session.add(matricula)
        await self._session.flush()
        return matricula
