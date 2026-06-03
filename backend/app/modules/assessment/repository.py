from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import Avaliacao, Nota


class AvaliacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Avaliacao | None:
        result = await self._session.execute(
            select(Avaliacao).where(Avaliacao.id == id),
        )
        return result.scalar_one_or_none()

    async def exists_by_alocacao_titulo_bimestre(
        self, alocacao_id: uuid.UUID, titulo: str, bimestre: int,
    ) -> bool:
        result = await self._session.execute(
            select(Avaliacao.id).where(
                and_(
                    Avaliacao.alocacao_id == alocacao_id,
                    Avaliacao.titulo == titulo,
                    Avaliacao.bimestre == bimestre,
                ),
            ).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_alocacao_bimestre(
        self, alocacao_id: uuid.UUID, bimestre: int,
    ) -> list[Avaliacao]:
        result = await self._session.execute(
            select(Avaliacao).where(
                and_(
                    Avaliacao.alocacao_id == alocacao_id,
                    Avaliacao.bimestre == bimestre,
                ),
            ).order_by(Avaliacao.data_aplicacao),
        )
        return list(result.scalars().all())

    async def get_by_alocacao(
        self, alocacao_id: uuid.UUID, bimestre: int | None = None,
        page: int = 1, size: int = 20,
    ) -> tuple[list[Avaliacao], int]:
        query = select(Avaliacao).where(Avaliacao.alocacao_id == alocacao_id)
        if bimestre is not None:
            query = query.where(Avaliacao.bimestre == bimestre)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Avaliacao.data_aplicacao.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create(self, avaliacao: Avaliacao) -> Avaliacao:
        self._session.add(avaliacao)
        await self._session.flush()
        return avaliacao

    async def update(self, avaliacao: Avaliacao) -> Avaliacao:
        avaliacao.updated_at = datetime.now(timezone.utc)
        self._session.add(avaliacao)
        await self._session.flush()
        return avaliacao


class NotaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Nota | None:
        result = await self._session.execute(
            select(Nota).where(Nota.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_avaliacao_matricula(
        self, avaliacao_id: uuid.UUID, matricula_id: uuid.UUID,
    ) -> Nota | None:
        result = await self._session.execute(
            select(Nota).where(
                and_(
                    Nota.avaliacao_id == avaliacao_id,
                    Nota.matricula_id == matricula_id,
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_avaliacao(self, avaliacao_id: uuid.UUID) -> list[Nota]:
        result = await self._session.execute(
            select(Nota).where(Nota.avaliacao_id == avaliacao_id).order_by(Nota.id),
        )
        return list(result.scalars().all())

    async def get_by_matricula_bimestre(
        self, matricula_id: uuid.UUID, bimestre: int,
    ) -> list[Nota]:
        result = await self._session.execute(
            select(Nota)
            .join(Avaliacao, Nota.avaliacao_id == Avaliacao.id)
            .where(
                and_(
                    Nota.matricula_id == matricula_id,
                    Avaliacao.bimestre == bimestre,
                ),
            ),
        )
        return list(result.scalars().all())

    async def get_recuperacao_by_matricula(
        self, matricula_id: uuid.UUID,
    ) -> list[Nota]:
        from app.shared.enums import TipoAvaliacao
        result = await self._session.execute(
            select(Nota)
            .join(Avaliacao, Nota.avaliacao_id == Avaliacao.id)
            .where(
                and_(
                    Nota.matricula_id == matricula_id,
                    Avaliacao.tipo == TipoAvaliacao.RECUPERACAO,
                ),
            ),
        )
        return list(result.scalars().all())

    async def bulk_create(self, notas: list[Nota]) -> list[Nota]:
        self._session.add_all(notas)
        await self._session.flush()
        return notas

    async def update(self, nota: Nota) -> Nota:
        nota.updated_at = datetime.now(timezone.utc)
        self._session.add(nota)
        await self._session.flush()
        return nota
