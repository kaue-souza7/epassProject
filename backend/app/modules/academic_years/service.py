from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.academic_years.models import AnoLetivo
from app.modules.academic_years.repository import AnoLetivoRepository
from app.modules.academic_years.schemas import AnoLetivoRequest


class AnoLetivoService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AnoLetivoRepository(session)

    async def create(self, data: AnoLetivoRequest) -> AnoLetivo:
        if await self._repo.exists_by_ano(data.ano):
            raise Conflict("Ano letivo já cadastrado")
        if data.data_inicio >= data.data_fim:
            raise ValidationError("data_inicio deve ser menor que data_fim")
        ano_letivo = AnoLetivo(
            ano=data.ano,
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
            ativo=False,
        )
        return await self._repo.create(ano_letivo)

    async def get_by_id(self, id: uuid.UUID) -> AnoLetivo:
        ano_letivo = await self._repo.get_by_id(id)
        if ano_letivo is None:
            raise NotFound("Ano letivo não encontrado")
        return ano_letivo

    async def get_active(self) -> AnoLetivo | None:
        return await self._repo.get_active()

    async def get_all(self) -> list[AnoLetivo]:
        return await self._repo.get_all()

    async def update(self, id: uuid.UUID, data: AnoLetivoRequest) -> AnoLetivo:
        ano_letivo = await self.get_by_id(id)
        if data.ano != ano_letivo.ano and await self._repo.exists_by_ano(data.ano):
            raise Conflict("Ano letivo já cadastrado")
        if data.data_inicio >= data.data_fim:
            raise ValidationError("data_inicio deve ser menor que data_fim")
        ano_letivo.ano = data.ano
        ano_letivo.data_inicio = data.data_inicio
        ano_letivo.data_fim = data.data_fim
        return await self._repo.update(ano_letivo)

    async def activate(self, id: uuid.UUID) -> AnoLetivo:
        ano_letivo = await self.get_by_id(id)
        active = await self._repo.get_active()
        if active is not None and active.id == ano_letivo.id:
            return ano_letivo
        if active is not None:
            active.ativo = False
            await self._repo.update(active)
        ano_letivo.ativo = True
        return await self._repo.update(ano_letivo)

    async def deactivate(self, id: uuid.UUID) -> AnoLetivo:
        ano_letivo = await self.get_by_id(id)
        ano_letivo.ativo = False
        return await self._repo.update(ano_letivo)
