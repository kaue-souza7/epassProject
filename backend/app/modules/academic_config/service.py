from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound
from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.academic_config.repository import ConfiguracaoAcademicaRepository
from app.modules.academic_config.schemas import (
    ConfiguracaoAcademicaCreate,
    ConfiguracaoAcademicaUpdate,
)


class ConfiguracaoAcademicaService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ConfiguracaoAcademicaRepository(session)

    async def obter(self, ano_letivo_id: uuid.UUID) -> ConfiguracaoAcademica:
        config = await self._repo.get_by_ano_letivo(ano_letivo_id)
        if config is None:
            config = await self._criar_default(ano_letivo_id)
        return config

    async def obter_por_matricula(
        self, matricula_id: uuid.UUID,
    ) -> ConfiguracaoAcademica:
        config = await self._repo.get_by_matricula(matricula_id)
        if config is None:
            raise NotFound("Configuração acadêmica não encontrada para esta matrícula")
        return config

    async def atualizar(
        self, ano_letivo_id: uuid.UUID, data: ConfiguracaoAcademicaUpdate,
    ) -> ConfiguracaoAcademica:
        config = await self._repo.get_by_ano_letivo(ano_letivo_id)
        if config is None:
            config = await self._criar_default(ano_letivo_id)

        if data.media_aprovacao is not None:
            config.media_aprovacao = float(data.media_aprovacao)
        if data.frequencia_minima is not None:
            config.frequencia_minima = float(data.frequencia_minima)
        if data.possui_recuperacao is not None:
            config.possui_recuperacao = data.possui_recuperacao
        if data.media_minima_recuperacao is not None:
            config.media_minima_recuperacao = float(data.media_minima_recuperacao)
        elif data.possui_recuperacao is False:
            config.media_minima_recuperacao = None
        if data.quantidade_periodos is not None:
            config.quantidade_periodos = data.quantidade_periodos
        if data.ativo is not None:
            config.ativo = data.ativo

        config.updated_at = datetime.now(timezone.utc)
        return await self._repo.update(config)

    async def _criar_default(
        self, ano_letivo_id: uuid.UUID,
    ) -> ConfiguracaoAcademica:
        config = ConfiguracaoAcademica(
            ano_letivo_id=ano_letivo_id,
            media_aprovacao=6.00,
            frequencia_minima=75.00,
            possui_recuperacao=True,
            media_minima_recuperacao=4.00,
            quantidade_periodos=4,
            ativo=True,
        )
        return await self._repo.create(config)
