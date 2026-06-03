from __future__ import annotations

import uuid
from datetime import date, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.allocations.models import Alocacao
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.allocations.schemas import AlocacaoCreate
from app.modules.teachers.service import ProfessorProfileService
from app.modules.classes.service import TurmaService
from app.modules.subjects.service import DisciplinaService


class AlocacaoService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AlocacaoRepository(session)
        self._professor_service = ProfessorProfileService(session)
        self._turma_service = TurmaService(session)
        self._disciplina_service = DisciplinaService(session)

    async def create(self, data: AlocacaoCreate) -> Alocacao:
        profile = await self._professor_service.get_by_usuario(data.professor_id)
        if not profile.ativo:
            raise ValidationError("Perfil de professor inativo")
        await self._turma_service.get_by_id(data.turma_id)
        await self._disciplina_service.get_by_id(data.disciplina_id)

        ativa = await self._repo.get_active_by_turma_disciplina(
            data.turma_id, data.disciplina_id,
        )
        if ativa is not None:
            raise Conflict("Já existe um professor alocado para esta disciplina na turma")

        alocacao = Alocacao(
            professor_id=profile.usuario_id,
            turma_id=data.turma_id,
            disciplina_id=data.disciplina_id,
            data_inicio=data.data_inicio or date.today(),
        )
        return await self._repo.create(alocacao)

    async def encerrar(self, id: uuid.UUID, data_fim: date) -> Alocacao:
        alocacao = await self.get_by_id(id)
        if alocacao.data_fim is not None:
            raise ValidationError("Alocação já encerrada")
        alocacao.data_fim = data_fim
        return await self._repo.update(alocacao)

    async def get_by_id(self, id: uuid.UUID) -> Alocacao:
        alocacao = await self._repo.get_by_id(id)
        if alocacao is None:
            raise NotFound("Alocação não encontrada")
        return alocacao

    async def search(
        self,
        professor_id: uuid.UUID | None = None,
        turma_id: uuid.UUID | None = None,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Alocacao], int]:
        return await self._repo.search(
            professor_id=professor_id,
            turma_id=turma_id,
            only_active=only_active,
            page=page,
            size=size,
        )
