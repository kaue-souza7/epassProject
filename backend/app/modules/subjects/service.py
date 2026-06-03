from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.subjects.models import Disciplina
from app.modules.subjects.repository import DisciplinaRepository
from app.modules.subjects.schemas import DisciplinaRequest, DisciplinaUpdateRequest


class DisciplinaService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DisciplinaRepository(session)

    async def create(self, data: DisciplinaRequest) -> Disciplina:
        if await self._repo.get_by_codigo(data.codigo) is not None:
            raise Conflict("Código já cadastrado")
        if await self._repo.get_by_nome(data.nome) is not None:
            raise Conflict("Nome já cadastrado")
        disciplina = Disciplina(
            codigo=data.codigo,
            nome=data.nome,
            descricao=data.descricao,
            ativo=True,
        )
        return await self._repo.create(disciplina)

    async def get_by_id(self, id: uuid.UUID) -> Disciplina:
        disciplina = await self._repo.get_by_id(id)
        if disciplina is None:
            raise NotFound("Disciplina não encontrada")
        return disciplina

    async def get_all(self, only_active: bool = False) -> list[Disciplina]:
        return await self._repo.get_all(only_active=only_active)

    async def update(self, id: uuid.UUID, data: DisciplinaUpdateRequest) -> Disciplina:
        disciplina = await self.get_by_id(id)
        if data.nome is not None and data.nome != disciplina.nome:
            if await self._repo.get_by_nome(data.nome) is not None:
                raise Conflict("Nome já cadastrado")
            disciplina.nome = data.nome
        if data.descricao is not None:
            disciplina.descricao = data.descricao
        if data.ativo is not None:
            disciplina.ativo = data.ativo
        return await self._repo.update(disciplina)
