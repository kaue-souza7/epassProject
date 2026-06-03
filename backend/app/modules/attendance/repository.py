from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.models import Chamada, Frequencia


class ChamadaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Chamada | None:
        result = await self._session.execute(
            select(Chamada).where(Chamada.id == id),
        )
        return result.scalar_one_or_none()

    async def exists_by_aula(self, alocacao_id: uuid.UUID, data_hora_aula: datetime) -> bool:
        result = await self._session.execute(
            select(Chamada.id).where(
                and_(
                    Chamada.alocacao_id == alocacao_id,
                    Chamada.data_hora_aula == data_hora_aula,
                ),
            ).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_alocacao_periodo(
        self, alocacao_id: uuid.UUID, data_inicio: datetime, data_fim: datetime,
    ) -> list[Chamada]:
        result = await self._session.execute(
            select(Chamada).where(
                and_(
                    Chamada.alocacao_id == alocacao_id,
                    Chamada.data_hora_aula >= data_inicio,
                    Chamada.data_hora_aula <= data_fim,
                ),
            ).order_by(Chamada.data_hora_aula),
        )
        return list(result.scalars().all())

    async def get_by_alocacao(
        self, alocacao_id: uuid.UUID, page: int = 1, size: int = 20,
    ) -> tuple[list[Chamada], int]:
        query = select(Chamada).where(Chamada.alocacao_id == alocacao_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Chamada.data_hora_aula.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create(self, chamada: Chamada) -> Chamada:
        self._session.add(chamada)
        await self._session.flush()
        return chamada


class FrequenciaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Frequencia | None:
        result = await self._session.execute(
            select(Frequencia).where(Frequencia.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_chamada(self, chamada_id: uuid.UUID) -> list[Frequencia]:
        result = await self._session.execute(
            select(Frequencia).where(Frequencia.chamada_id == chamada_id),
        )
        return list(result.scalars().all())

    async def get_by_matricula_and_chamadas(
        self, matricula_id: uuid.UUID, chamada_ids: list[uuid.UUID],
    ) -> list[Frequencia]:
        if not chamada_ids:
            return []
        result = await self._session.execute(
            select(Frequencia).where(
                and_(
                    Frequencia.matricula_id == matricula_id,
                    Frequencia.chamada_id.in_(chamada_ids),
                ),
            ),
        )
        return list(result.scalars().all())

    async def get_by_matricula(self, matricula_id: uuid.UUID) -> list[Frequencia]:
        result = await self._session.execute(
            select(Frequencia)
            .where(Frequencia.matricula_id == matricula_id)
            .order_by(Frequencia.id),
        )
        return list(result.scalars().all())

    async def get_by_matricula_disciplina(
        self, matricula_id: uuid.UUID, alocacao_id: uuid.UUID,
    ) -> list[Frequencia]:
        result = await self._session.execute(
            select(Frequencia)
            .join(Chamada, Frequencia.chamada_id == Chamada.id)
            .where(
                and_(
                    Frequencia.matricula_id == matricula_id,
                    Chamada.alocacao_id == alocacao_id,
                ),
            ),
        )
        return list(result.scalars().all())

    async def bulk_create(self, frequencias: list[Frequencia]) -> list[Frequencia]:
        self._session.add_all(frequencias)
        await self._session.flush()
        return frequencias

    async def update(self, frequencia: Frequencia) -> Frequencia:
        self._session.add(frequencia)
        await self._session.flush()
        return frequencia
