from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.teachers.models import ProfessorProfile
from app.modules.teachers.repository import ProfessorProfileRepository
from app.modules.teachers.schemas import ProfessorProfileCreate, ProfessorProfileUpdate
from app.modules.users.service import UsuarioService
from app.shared.enums import Perfil


class ProfessorProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ProfessorProfileRepository(session)
        self._usuario_service = UsuarioService(session)

    async def create(self, data: ProfessorProfileCreate) -> ProfessorProfile:
        usuario = await self._usuario_service.get_by_id(data.usuario_id)
        if usuario.perfil != Perfil.PROFESSOR:
            raise ValidationError("Usuário não possui perfil de professor")
        if await self._repo.get_by_usuario(data.usuario_id) is not None:
            raise Conflict("Professor já possui perfil cadastrado")
        if data.matricula_funcional is not None:
            existing = await self._repo.get_by_matricula(data.matricula_funcional)
            if existing is not None:
                raise Conflict("Matrícula funcional já cadastrada")
        profile = ProfessorProfile(
            usuario_id=usuario.id,
            formacao_principal=data.formacao_principal,
            matricula_funcional=data.matricula_funcional,
            data_contratacao=data.data_contratacao,
            observacoes=data.observacoes,
            ativo=True,
        )
        return await self._repo.create(profile)

    async def get_by_usuario(self, usuario_id: uuid.UUID) -> ProfessorProfile:
        profile = await self._repo.get_by_usuario(usuario_id)
        if profile is None:
            raise NotFound("Perfil de professor não encontrado")
        return profile

    async def get_all(self, only_active: bool = False) -> list[ProfessorProfile]:
        return await self._repo.get_all(only_active=only_active)

    async def search(
        self,
        nome: str | None = None,
        matricula_funcional: str | None = None,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ProfessorProfile], int]:
        return await self._repo.search(
            nome=nome,
            matricula_funcional=matricula_funcional,
            only_active=only_active,
            page=page,
            size=size,
        )

    async def update(
        self, usuario_id: uuid.UUID, data: ProfessorProfileUpdate,
    ) -> ProfessorProfile:
        profile = await self.get_by_usuario(usuario_id)
        if data.matricula_funcional is not None and data.matricula_funcional != profile.matricula_funcional:
            existing = await self._repo.get_by_matricula(data.matricula_funcional)
            if existing is not None:
                raise Conflict("Matrícula funcional já cadastrada")
            profile.matricula_funcional = data.matricula_funcional
        if data.formacao_principal is not None:
            profile.formacao_principal = data.formacao_principal
        if data.data_contratacao is not None:
            profile.data_contratacao = data.data_contratacao
        if data.observacoes is not None:
            profile.observacoes = data.observacoes
        if data.ativo is not None:
            profile.ativo = data.ativo
        return await self._repo.update(profile)
