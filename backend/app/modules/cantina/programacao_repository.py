from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cantina.programacao_models import ProgramacaoCantina, ProgramacaoItem
from app.shared.enums import DiaSemana, TipoProgramacao


class ProgramacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_aluno_and_dia(
        self, aluno_id: uuid.UUID, dia_semana: DiaSemana,
    ) -> ProgramacaoCantina | None:
        result = await self._session.execute(
            select(ProgramacaoCantina).where(
                ProgramacaoCantina.aluno_id == aluno_id,
                ProgramacaoCantina.dia_semana == dia_semana,
                ProgramacaoCantina.ativo.is_(True),
            ).limit(1),
        )
        return result.scalars().first()

    async def get_any_by_aluno_and_dia(
        self, aluno_id: uuid.UUID, dia_semana: DiaSemana,
    ) -> ProgramacaoCantina | None:
        result = await self._session.execute(
            select(ProgramacaoCantina).where(
                ProgramacaoCantina.aluno_id == aluno_id,
                ProgramacaoCantina.dia_semana == dia_semana,
            ).order_by(ProgramacaoCantina.updated_at.desc()).limit(1),
        )
        return result.scalars().first()

    async def get_by_aluno_tipo(
        self, aluno_id: uuid.UUID, tipo: TipoProgramacao,
    ) -> ProgramacaoCantina | None:
        """Busca a programação de um tipo (inclui inativas, para reativação)."""
        result = await self._session.execute(
            select(ProgramacaoCantina).where(
                ProgramacaoCantina.aluno_id == aluno_id,
                ProgramacaoCantina.tipo == tipo,
            ).order_by(ProgramacaoCantina.updated_at.desc()).limit(1),
        )
        return result.scalars().first()

    async def get_by_aluno_tipo_dia(
        self, aluno_id: uuid.UUID, tipo: TipoProgramacao, dia_semana: DiaSemana,
    ) -> ProgramacaoCantina | None:
        """Busca a programação de um tipo/dia (inclui inativas, para reativação)."""
        result = await self._session.execute(
            select(ProgramacaoCantina).where(
                ProgramacaoCantina.aluno_id == aluno_id,
                ProgramacaoCantina.tipo == tipo,
                ProgramacaoCantina.dia_semana == dia_semana,
            ).order_by(ProgramacaoCantina.updated_at.desc()).limit(1),
        )
        return result.scalars().first()

    async def get_by_aluno(
        self, aluno_id: uuid.UUID,
    ) -> list[ProgramacaoCantina]:
        result = await self._session.execute(
            select(ProgramacaoCantina).where(
                ProgramacaoCantina.aluno_id == aluno_id,
                ProgramacaoCantina.ativo.is_(True),
            ).order_by(ProgramacaoCantina.dia_semana),
        )
        return list(result.scalars().all())

    async def get_by_aluno_and_responsavel(
        self, aluno_id: uuid.UUID, responsavel_id: uuid.UUID,
    ) -> list[ProgramacaoCantina]:
        result = await self._session.execute(
            select(ProgramacaoCantina).where(
                ProgramacaoCantina.aluno_id == aluno_id,
                ProgramacaoCantina.responsavel_id == responsavel_id,
                ProgramacaoCantina.ativo.is_(True),
            ).order_by(ProgramacaoCantina.dia_semana),
        )
        return list(result.scalars().all())

    async def get_by_id(self, programacao_id: uuid.UUID) -> ProgramacaoCantina | None:
        result = await self._session.execute(
            select(ProgramacaoCantina).where(ProgramacaoCantina.id == programacao_id),
        )
        return result.scalar_one_or_none()

    async def create(self, programacao: ProgramacaoCantina) -> ProgramacaoCantina:
        self._session.add(programacao)
        await self._session.flush()
        return programacao

    async def update(self, programacao: ProgramacaoCantina) -> ProgramacaoCantina:
        programacao.updated_at = datetime.now(timezone.utc)
        self._session.add(programacao)
        await self._session.flush()
        return programacao

    async def delete(self, programacao: ProgramacaoCantina) -> None:
        programacao.ativo = False
        programacao.updated_at = datetime.now(timezone.utc)
        self._session.add(programacao)
        await self._session.flush()
