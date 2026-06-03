from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.series.models import Serie
from app.modules.series.repository import SerieRepository
from app.modules.series.schemas import SerieRequest, SerieUpdateRequest


class SerieService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SerieRepository(session)

    async def create(self, data: SerieRequest) -> Serie:
        if not 1 <= data.numero <= 9:
            raise ValidationError("Série deve estar entre 1 e 9")
        if await self._repo.get_by_numero(data.numero) is not None:
            raise Conflict("Série já cadastrada")
        serie = Serie(
            numero=data.numero,
            nome=data.nome,
            descricao=data.descricao,
            ativo=True,
        )
        return await self._repo.create(serie)

    async def get_by_id(self, id: uuid.UUID) -> Serie:
        serie = await self._repo.get_by_id(id)
        if serie is None:
            raise NotFound("Série não encontrada")
        return serie

    async def get_by_numero(self, numero: int) -> Serie | None:
        return await self._repo.get_by_numero(numero)

    async def get_all(self, only_active: bool = False) -> list[Serie]:
        return await self._repo.get_all(only_active=only_active)

    async def update(self, id: uuid.UUID, data: SerieUpdateRequest) -> Serie:
        serie = await self.get_by_id(id)
        if data.nome is not None:
            serie.nome = data.nome
        if data.descricao is not None:
            serie.descricao = data.descricao
        if data.ativo is not None:
            serie.ativo = data.ativo
        return await self._repo.update(serie)
