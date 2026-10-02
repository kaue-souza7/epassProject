from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.allocations.models import Alocacao


class AlocacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Alocacao | None:
        result = await self._session.execute(
            select(Alocacao).where(Alocacao.id == id),
        )
        return result.scalar_one_or_none()

    async def get_active_by_turma_disciplina(
        self, turma_id: uuid.UUID, disciplina_id: uuid.UUID,
    ) -> Alocacao | None:
        result = await self._session.execute(
            select(Alocacao).where(
                and_(
                    Alocacao.turma_id == turma_id,
                    Alocacao.disciplina_id == disciplina_id,
                    Alocacao.data_fim.is_(None),
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        professor_id: uuid.UUID | None = None,
        turma_id: uuid.UUID | None = None,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Alocacao], int]:
        query = select(Alocacao)

        if professor_id:
            query = query.where(Alocacao.professor_id == professor_id)
        if turma_id:
            query = query.where(Alocacao.turma_id == turma_id)
        if only_active:
            query = query.where(Alocacao.data_fim.is_(None))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Alocacao.data_inicio.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)

        return list(result.scalars().all()), total

    async def professor_leciona_turma(
        self, professor_id: uuid.UUID, turma_id: uuid.UUID,
    ) -> bool:
        """Existe alocação ativa do professor para a turma."""
        result = await self._session.execute(
            select(Alocacao.id)
            .where(
                and_(
                    Alocacao.professor_id == professor_id,
                    Alocacao.turma_id == turma_id,
                    Alocacao.data_fim.is_(None),
                ),
            )
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def professor_leciona_aluno(
        self, professor_id: uuid.UUID, aluno_id: uuid.UUID,
    ) -> bool:
        """Aluno possui matrícula ativa em alguma turma ativa do professor."""
        from app.modules.enrollments.models import Matricula
        from app.shared.enums import StatusMatricula

        result = await self._session.execute(
            select(Matricula.id)
            .join(Alocacao, Alocacao.turma_id == Matricula.turma_id)
            .where(
                and_(
                    Matricula.aluno_id == aluno_id,
                    Matricula.status == StatusMatricula.ATIVA,
                    Alocacao.professor_id == professor_id,
                    Alocacao.data_fim.is_(None),
                ),
            )
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_disciplina(self, disciplina_id: uuid.UUID) -> list[Alocacao]:
        result = await self._session.execute(
            select(Alocacao)
            .where(Alocacao.disciplina_id == disciplina_id)
            .order_by(Alocacao.data_inicio.desc()),
        )
        return list(result.scalars().all())

    async def create(self, alocacao: Alocacao) -> Alocacao:
        self._session.add(alocacao)
        await self._session.flush()
        return alocacao

    async def update(self, alocacao: Alocacao) -> Alocacao:
        alocacao.updated_at = datetime.now(timezone.utc)
        self._session.add(alocacao)
        await self._session.flush()
        return alocacao
