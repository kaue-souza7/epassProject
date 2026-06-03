from __future__ import annotations

import uuid
from datetime import date, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.enrollments.models import Matricula
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.enrollments.schemas import MatriculaCreate, MatriculaTransfer
from app.modules.students.service import AlunoService
from app.modules.students.repository import ResponsavelAlunoRepository
from app.modules.classes.service import TurmaService
from app.shared.enums import StatusMatricula


class MatriculaService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MatriculaRepository(session)
        self._aluno_service = AlunoService(session)
        self._turma_service = TurmaService(session)
        self._repo_resp = ResponsavelAlunoRepository(session)

    async def create(self, data: MatriculaCreate) -> Matricula:
        aluno = await self._aluno_service.get_by_id(data.aluno_id)
        if not aluno.ativo:
            raise ValidationError("Aluno inativo não pode ser matriculado")

        turma = await self._turma_service.get_by_id(data.turma_id)

        vinculos = await self._repo_resp.get_by_aluno(data.aluno_id)
        if not vinculos:
            raise ValidationError(
                "Aluno deve possuir ao menos um responsável para ser matriculado",
            )

        ativa = await self._repo.get_active_by_aluno(data.aluno_id)
        if ativa is not None:
            raise Conflict("Aluno já possui matrícula ativa")

        vagas = await self._repo.count_active_by_turma(data.turma_id)
        if vagas >= turma.vagas_total:
            raise Conflict("Turma sem vagas disponíveis")

        matricula = Matricula(
            aluno_id=aluno.id,
            turma_id=turma.id,
            data_matricula=date.today(),
            status="ativa",
            observacoes=data.observacoes,
        )
        return await self._repo.create(matricula)

    async def transferir(self, id: uuid.UUID, data: MatriculaTransfer) -> Matricula:
        matricula = await self.get_by_id(id)
        if matricula.status != "ativa":
            raise ValidationError("Apenas matrículas ativas podem ser transferidas")

        nova_turma = await self._turma_service.get_by_id(data.nova_turma_id)

        vagas = await self._repo.count_active_by_turma(data.nova_turma_id)
        if vagas >= nova_turma.vagas_total:
            raise Conflict("Turma de destino sem vagas disponíveis")

        matricula.status = "cancelada"
        matricula.data_saida = data.data_transferencia or date.today()
        matricula.motivo_saida = data.motivo
        await self._repo.update(matricula)

        nova_matricula = Matricula(
            aluno_id=matricula.aluno_id,
            turma_id=nova_turma.id,
            matricula_origem_id=matricula.id,
            data_matricula=data.data_transferencia or date.today(),
            status="ativa",
        )
        return await self._repo.create(nova_matricula)

    async def concluir(self, id: uuid.UUID) -> Matricula:
        matricula = await self.get_by_id(id)
        if matricula.status != "ativa":
            raise ValidationError("Apenas matrículas ativas podem ser concluídas")
        matricula.status = "concluida"
        matricula.data_saida = date.today()
        return await self._repo.update(matricula)

    async def cancelar(self, id: uuid.UUID, motivo: str) -> Matricula:
        matricula = await self.get_by_id(id)
        if matricula.status != "ativa":
            raise ValidationError("Apenas matrículas ativas podem ser canceladas")
        matricula.status = "cancelada"
        matricula.data_saida = date.today()
        matricula.motivo_saida = motivo
        return await self._repo.update(matricula)

    async def get_by_id(self, id: uuid.UUID) -> Matricula:
        matricula = await self._repo.get_by_id(id)
        if matricula is None:
            raise NotFound("Matrícula não encontrada")
        return matricula

    async def search(
        self,
        aluno_id: uuid.UUID | None = None,
        turma_id: uuid.UUID | None = None,
        status: StatusMatricula | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[tuple[Matricula, str, str]], int]:
        return await self._repo.search(
            aluno_id=aluno_id,
            turma_id=turma_id,
            status=status,
            page=page,
            size=size,
        )

    async def get_historico(self, aluno_id: uuid.UUID) -> list[Matricula]:
        return await self._repo.get_by_aluno(aluno_id)

    async def get_by_turma(self, turma_id: uuid.UUID) -> list[Matricula]:
        return await self._repo.get_by_turma(turma_id)
