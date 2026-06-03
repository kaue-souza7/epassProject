from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.classes.models import Turma
from app.modules.classes.repository import TurmaRepository
from app.modules.classes.schemas import TurmaRequest, TurmaUpdateRequest
from app.modules.series.service import SerieService
from app.modules.academic_years.service import AnoLetivoService


class TurmaService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = TurmaRepository(session)
        self._serie_service = SerieService(session)
        self._ano_letivo_service = AnoLetivoService(session)

    async def create(self, data: TurmaRequest) -> Turma:
        serie = await self._serie_service.get_by_id(data.serie_id)
        ano_letivo = await self._ano_letivo_service.get_by_id(data.ano_letivo_id)

        if await self._repo.get_by_codigo_and_ano(data.codigo, data.ano_letivo_id) is not None:
            raise Conflict("Já existe uma turma com este código no mesmo ano letivo")

        if await self._repo.exists_by_serie_turno_ano(
            data.serie_id, data.turno.value, data.ano_letivo_id,
        ):
            raise Conflict("Já existe turma desta série e turno no mesmo ano letivo")

        turma = Turma(
            codigo=data.codigo,
            nome=data.nome,
            serie_id=serie.id,
            ano_letivo_id=ano_letivo.id,
            turno=data.turno,
            vagas_total=data.vagas_total,
            ativo=True,
        )
        return await self._repo.create(turma)

    async def get_by_id(self, id: uuid.UUID) -> Turma:
        turma = await self._repo.get_by_id(id)
        if turma is None:
            raise NotFound("Turma não encontrada")
        return turma

    async def get_by_ano_letivo(self, ano_letivo_id: uuid.UUID) -> list[Turma]:
        return await self._repo.get_by_ano_letivo(ano_letivo_id)

    async def get_all(self, only_active: bool = False) -> list[Turma]:
        return await self._repo.get_all(only_active=only_active)

    async def search_paginated(
        self,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Turma], int]:
        return await self._repo.search_paginated(
            only_active=only_active, page=page, size=size,
        )

    async def update(self, id: uuid.UUID, data: TurmaUpdateRequest) -> Turma:
        turma = await self.get_by_id(id)
        if data.codigo is not None and data.codigo != turma.codigo:
            if await self._repo.get_by_codigo_and_ano(data.codigo, turma.ano_letivo_id) is not None:
                raise Conflict("Já existe uma turma com este código no mesmo ano letivo")
            turma.codigo = data.codigo
        if data.nome is not None:
            turma.nome = data.nome
        if data.turno is not None:
            turma.turno = data.turno
        if data.vagas_total is not None:
            turma.vagas_total = data.vagas_total
        if data.ativo is not None:
            turma.ativo = data.ativo
        return await self._repo.update(turma)
