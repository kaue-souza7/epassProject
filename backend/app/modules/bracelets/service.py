from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.bracelets.models import Bracelet
from app.modules.bracelets.repository import BraceletRepository
from app.modules.bracelets.schemas import BraceletRequest, BraceletUpdateRequest, VincularAlunoRequest
from app.modules.students.repository import AlunoRepository
from app.shared.enums import StatusPulseira


class BraceletService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = BraceletRepository(session)
        self._aluno_repo = AlunoRepository(session)

    async def create(self, data: BraceletRequest) -> Bracelet:
        if await self._repo.exists_by_uid(data.uid):
            raise Conflict("UID já cadastrado")
        bracelet = Bracelet(
            uid=data.uid,
            codigo=data.codigo,
            status=StatusPulseira.ATIVA,
        )
        return await self._repo.create(bracelet)

    async def get_by_id(self, id: uuid.UUID) -> Bracelet:
        bracelet = await self._repo.get_by_id(id)
        if bracelet is None:
            raise NotFound("Pulseira não encontrada")
        return bracelet

    async def get_by_uid(self, uid: str) -> Bracelet:
        bracelet = await self._repo.get_by_uid(uid)
        if bracelet is None:
            raise NotFound("Pulseira não encontrada")
        return bracelet

    async def get_by_aluno_id(self, aluno_id: uuid.UUID) -> Bracelet:
        bracelet = await self._repo.get_by_aluno_id(aluno_id)
        if bracelet is None:
            raise NotFound("Aluno não possui pulseira vinculada")
        return bracelet

    async def search_paginated(
        self,
        status: str | None = None,
        tem_aluno: bool | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Bracelet], int]:
        return await self._repo.search_paginated(
            status=status, tem_aluno=tem_aluno, page=page, size=size,
        )

    async def update(self, id: uuid.UUID, data: BraceletUpdateRequest) -> Bracelet:
        bracelet = await self.get_by_id(id)
        if data.uid is not None and data.uid != bracelet.uid:
            if await self._repo.exists_by_uid(data.uid):
                raise Conflict("UID já cadastrado")
            bracelet.uid = data.uid
        if data.codigo is not None:
            bracelet.codigo = data.codigo
        return await self._repo.update(bracelet)

    async def vincular_aluno(self, id: uuid.UUID, data: VincularAlunoRequest) -> Bracelet:
        bracelet = await self.get_by_id(id)
        if bracelet.aluno_id is not None:
            raise Conflict("Pulseira já possui aluno vinculado")
        aluno = await self._aluno_repo.get_by_id(data.aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if await self._repo.exists_by_aluno(data.aluno_id):
            raise Conflict("Aluno já possui uma pulseira vinculada")
        bracelet.aluno_id = data.aluno_id
        return await self._repo.update(bracelet)

    async def desvincular_aluno(self, id: uuid.UUID) -> Bracelet:
        bracelet = await self.get_by_id(id)
        if bracelet.aluno_id is None:
            raise Conflict("Pulseira não possui aluno vinculado")
        bracelet.aluno_id = None
        return await self._repo.update(bracelet)

    async def bloquear(self, id: uuid.UUID) -> Bracelet:
        bracelet = await self.get_by_id(id)
        if bracelet.status != StatusPulseira.ATIVA:
            raise Conflict("Apenas pulseiras ativas podem ser bloqueadas")
        bracelet.status = StatusPulseira.BLOQUEADA
        return await self._repo.update(bracelet)

    async def desbloquear(self, id: uuid.UUID) -> Bracelet:
        bracelet = await self.get_by_id(id)
        if bracelet.status != StatusPulseira.BLOQUEADA:
            raise Conflict("Apenas pulseiras bloqueadas podem ser desbloqueadas")
        bracelet.status = StatusPulseira.ATIVA
        return await self._repo.update(bracelet)
