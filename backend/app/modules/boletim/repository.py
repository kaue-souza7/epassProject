from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.boletim.models import LiberacaoBoletim, PrazoLiberacao


class LiberacaoBoletimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_professor_turma_bimestre(
        self,
        professor_id: uuid.UUID,
        turma_id: uuid.UUID,
        bimestre: int,
    ) -> list[LiberacaoBoletim]:
        result = await self._session.execute(
            select(LiberacaoBoletim).where(
                and_(
                    LiberacaoBoletim.professor_id == professor_id,
                    LiberacaoBoletim.turma_id == turma_id,
                    LiberacaoBoletim.bimestre == bimestre,
                    LiberacaoBoletim.ativo.is_(True),
                ),
            ),
        )
        return list(result.scalars().all())

    async def get_by_alocacao_bimestre(
        self,
        alocacao_id: uuid.UUID,
        bimestre: int,
    ) -> LiberacaoBoletim | None:
        result = await self._session.execute(
            select(LiberacaoBoletim).where(
                and_(
                    LiberacaoBoletim.alocacao_id == alocacao_id,
                    LiberacaoBoletim.bimestre == bimestre,
                    LiberacaoBoletim.ativo.is_(True),
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def is_alocacao_liberada(
        self,
        alocacao_id: uuid.UUID,
        bimestre: int,
    ) -> bool:
        result = await self.get_by_alocacao_bimestre(alocacao_id, bimestre)
        return result is not None

    async def create(self, liberacao: LiberacaoBoletim) -> LiberacaoBoletim:
        self._session.add(liberacao)
        await self._session.flush()
        return liberacao

    async def bulk_create(self, liberacoes: list[LiberacaoBoletim]) -> None:
        self._session.add_all(liberacoes)
        await self._session.flush()


class PrazoLiberacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_ano_bimestre(
        self,
        ano_letivo_id: uuid.UUID,
        bimestre: int,
    ) -> PrazoLiberacao | None:
        result = await self._session.execute(
            select(PrazoLiberacao).where(
                and_(
                    PrazoLiberacao.ano_letivo_id == ano_letivo_id,
                    PrazoLiberacao.bimestre == bimestre,
                    PrazoLiberacao.ativo.is_(True),
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, prazo_id: uuid.UUID) -> PrazoLiberacao | None:
        result = await self._session.execute(
            select(PrazoLiberacao).where(PrazoLiberacao.id == prazo_id),
        )
        return result.scalar_one_or_none()

    async def get_all_active_unnotified(self) -> list[PrazoLiberacao]:
        result = await self._session.execute(
            select(PrazoLiberacao).where(
                and_(
                    PrazoLiberacao.ativo.is_(True),
                    PrazoLiberacao.notificado_em.is_(None),
                ),
            ),
        )
        return list(result.scalars().all())

    async def get_by_ano_letivo(
        self,
        ano_letivo_id: uuid.UUID,
    ) -> list[PrazoLiberacao]:
        result = await self._session.execute(
            select(PrazoLiberacao).where(
                and_(
                    PrazoLiberacao.ano_letivo_id == ano_letivo_id,
                    PrazoLiberacao.ativo.is_(True),
                ),
            ).order_by(PrazoLiberacao.bimestre),
        )
        return list(result.scalars().all())

    async def get_vencidos_nao_notificados(
        self,
        data_atual: date,
    ) -> list[PrazoLiberacao]:
        result = await self._session.execute(
            select(PrazoLiberacao).where(
                and_(
                    PrazoLiberacao.data_limite < data_atual,
                    PrazoLiberacao.notificado_em.is_(None),
                    PrazoLiberacao.ativo.is_(True),
                ),
            ),
        )
        return list(result.scalars().all())

    async def create(self, prazo: PrazoLiberacao) -> PrazoLiberacao:
        self._session.add(prazo)
        await self._session.flush()
        return prazo

    async def update(self, prazo: PrazoLiberacao) -> PrazoLiberacao:
        prazo.updated_at = datetime.now(timezone.utc)
        self._session.add(prazo)
        await self._session.flush()
        return prazo
