from __future__ import annotations

import uuid
from datetime import date, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.students.models import Aluno, ResponsavelAluno
from app.modules.students.repository import AlunoRepository, ResponsavelAlunoRepository
from app.modules.students.schemas import (
    AlunoRequest,
    AlunoUpdateRequest,
    HistoricoEscolarResponse,
    HistoricoItem,
    ResponsavelAlunoCreate,
)
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.reports.service import BoletimService
from app.modules.reports.schemas import SituacaoAluno
from app.modules.users.service import UsuarioService
from app.shared.enums import Perfil


class AlunoService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AlunoRepository(session)
        self._repo_resp = ResponsavelAlunoRepository(session)
        self._usuario_service = UsuarioService(session)
        self._session = session
        self._matricula_repo = MatriculaRepository(session)

    async def create(self, data: AlunoRequest) -> Aluno:
        if data.cpf is not None and await self._repo.exists_by_cpf(data.cpf):
            raise Conflict("CPF já cadastrado")
        if data.data_nascimento >= date.today():
            raise ValidationError("data_nascimento deve ser anterior à data atual")
        if data.data_entrada > date.today():
            raise ValidationError("data_entrada não pode ser futura")
        aluno = Aluno(
            nome=data.nome,
            data_nascimento=data.data_nascimento,
            cpf=data.cpf,
            rg=data.rg,
            endereco=data.endereco,
            telefone=data.telefone,
            email=data.email,
            data_entrada=data.data_entrada,
            ativo=True,
        )
        return await self._repo.create(aluno)

    async def get_by_id(self, id: uuid.UUID) -> Aluno:
        aluno = await self._repo.get_by_id(id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        return aluno

    async def search(self, nome: str) -> list[Aluno]:
        return await self._repo.search_by_nome(nome)

    async def get_all(self, only_active: bool = False) -> list[Aluno]:
        return await self._repo.get_all(only_active=only_active)

    async def search_paginated(
        self,
        nome: str | None = None,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Aluno], int]:
        return await self._repo.search_paginated(
            nome=nome, only_active=only_active, page=page, size=size,
        )

    async def update(self, id: uuid.UUID, data: AlunoUpdateRequest) -> Aluno:
        aluno = await self.get_by_id(id)
        if data.cpf is not None and data.cpf != aluno.cpf and await self._repo.exists_by_cpf(data.cpf):
            raise Conflict("CPF já cadastrado")
        if data.nome is not None:
            aluno.nome = data.nome
        if data.data_nascimento is not None:
            if data.data_nascimento >= date.today():
                raise ValidationError("data_nascimento deve ser anterior à data atual")
            aluno.data_nascimento = data.data_nascimento
        if data.cpf is not None:
            aluno.cpf = data.cpf
        if data.rg is not None:
            aluno.rg = data.rg
        if data.endereco is not None:
            aluno.endereco = data.endereco
        if data.telefone is not None:
            aluno.telefone = data.telefone
        if data.email is not None:
            aluno.email = data.email
        if data.ativo is not None:
            aluno.ativo = data.ativo
        return await self._repo.update(aluno)

    async def add_responsavel(
        self, aluno_id: uuid.UUID, data: ResponsavelAlunoCreate,
    ) -> ResponsavelAluno:
        aluno = await self.get_by_id(aluno_id)
        responsavel = await self._usuario_service.get_by_id(data.responsavel_id)
        if responsavel is None:
            raise NotFound("Responsável não encontrado")
        if responsavel.perfil != Perfil.RESPONSAVEL:
            raise ValidationError("Usuário não possui perfil de responsável")
        if await self._repo_resp.exists(aluno_id, data.responsavel_id):
            raise Conflict("Vínculo já existe")
        vinculo = ResponsavelAluno(
            aluno_id=aluno.id,
            responsavel_id=data.responsavel_id,
            parentesco=data.parentesco,
            responsavel_financeiro=data.responsavel_financeiro,
        )
        return await self._repo_resp.create(vinculo)

    async def remove_responsavel(self, aluno_id: uuid.UUID, responsavel_id: uuid.UUID) -> None:
        await self.get_by_id(aluno_id)
        vinculo = await self._repo_resp.get_by_aluno_and_responsavel(aluno_id, responsavel_id)
        if vinculo is None:
            raise NotFound("Vínculo não encontrado")
        await self._repo_resp.delete(vinculo)

    async def list_responsaveis(self, aluno_id: uuid.UUID) -> list[ResponsavelAluno]:
        await self.get_by_id(aluno_id)
        return await self._repo_resp.get_by_aluno(aluno_id)

    async def list_alunos_do_responsavel(self, responsavel_id: uuid.UUID) -> list[Aluno]:
        vinculos = await self._repo_resp.get_by_responsavel(responsavel_id)
        alunos = []
        for v in vinculos:
            aluno = await self._repo.get_by_id(v.aluno_id)
            if aluno is not None:
                alunos.append(aluno)
        return alunos

    async def get_history(self, aluno_id: uuid.UUID) -> HistoricoEscolarResponse:
        aluno = await self.get_by_id(aluno_id)
        matriculas = await self._matricula_repo.get_by_aluno(aluno_id)
        boletim_service = BoletimService(self._session)

        historico = []
        for mat in matriculas:
            situacao_final = None
            media_final = None
            frequencia_final = None

            if mat.status in ("ativa", "concluida"):
                try:
                    sit, media_pre, media_pos, freq = await boletim_service._calcular_situacao_final(mat.id)
                    situacao_final = sit
                    media_final = media_pos if media_pos is not None else media_pre
                    frequencia_final = freq
                except Exception:
                    pass

            turma = mat.turma
            historico.append(HistoricoItem(
                matricula_id=mat.id,
                ano_letivo=turma.ano_letivo.ano,
                turma_codigo=turma.codigo,
                serie_nome=turma.serie.nome,
                data_matricula=mat.data_matricula,
                data_saida=mat.data_saida,
                status=mat.status.value if hasattr(mat.status, 'value') else str(mat.status),
                situacao_final=situacao_final,
                media_final=round(media_final, 2) if media_final is not None else None,
                frequencia_final=frequencia_final,
            ))

        return HistoricoEscolarResponse(
            aluno_id=aluno.id,
            aluno_nome=aluno.nome,
            historico=historico,
        )
