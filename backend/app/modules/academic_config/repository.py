from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.classes.models import Turma
from app.modules.enrollments.models import Matricula


class ConfiguracaoAcademicaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_ano_letivo(
        self, ano_letivo_id: uuid.UUID,
    ) -> ConfiguracaoAcademica | None:
        result = await self._session.execute(
            select(ConfiguracaoAcademica).where(
                ConfiguracaoAcademica.ano_letivo_id == ano_letivo_id,
            ),
        )
        return result.scalar_one_or_none()

    async def create(self, config: ConfiguracaoAcademica) -> ConfiguracaoAcademica:
        self._session.add(config)
        await self._session.flush()
        return config

    async def update(self, config: ConfiguracaoAcademica) -> ConfiguracaoAcademica:
        self._session.add(config)
        await self._session.flush()
        return config

    async def get_by_matricula(
        self, matricula_id: uuid.UUID,
    ) -> ConfiguracaoAcademica | None:
        result = await self._session.execute(
            select(ConfiguracaoAcademica)
            .join(Turma, Turma.ano_letivo_id == ConfiguracaoAcademica.ano_letivo_id)
            .join(Matricula, Matricula.turma_id == Turma.id)
            .where(Matricula.id == matricula_id),
        )
        return result.scalar_one_or_none()
