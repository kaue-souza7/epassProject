from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationError
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.classes.repository import TurmaRepository
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.schedule.models import (
    HorarioAula,
    agora_hora_escuela,
    dia_semana_de,
    horarios_sobrepostos,
)
from app.modules.schedule.repository import HorarioAulaRepository
from app.modules.schedule.schemas import (
    AulaHojeResponse,
    AulasDoDiaResponse,
    HorarioAulaCreate,
    HorarioAulaResponse,
    HorarioAulaUpdate,
)
from app.modules.students.repository import ResponsavelAlunoRepository
from app.shared.enums import DiaSemana, StatusMatricula


class HorarioAulaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = HorarioAulaRepository(session)
        self._alocacao_repo = AlocacaoRepository(session)
        self._turma_repo = TurmaRepository(session)
        self._matricula_repo = MatriculaRepository(session)
        self._vinculo_repo = ResponsavelAlunoRepository(session)

    # ── CRUD ────────────────────────────────────────────────────────

    async def criar(self, data: HorarioAulaCreate) -> HorarioAula:
        await self._validar_professor_alocado(data.turma_id, data.professor_id, data.disciplina_id)
        await self._validar_conflitos(
            turma_id=data.turma_id,
            professor_id=data.professor_id,
            dia_semana=data.dia_semana,
            hora_inicio=data.hora_inicio,
            hora_fim=data.hora_fim,
            excluir_id=None,
        )
        return await self._repo.create(HorarioAula(**data.model_dump()))

    async def atualizar(self, id: uuid.UUID, data: HorarioAulaUpdate) -> HorarioAula:
        horario = await self.get_by_id(id)

        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(horario, campo, valor)

        # Uma janela parcialmente atualizada precisa ser validada como um todo: mudar
        # só a hora de início de 09:00-11:00 para 11:00 com fim em 10:00 é inválido, e
        # a checagem feita só com os campos enviados deixaria passar.
        if horario.hora_fim <= horario.hora_inicio:
            raise ValidationError("A hora de término deve ser depois da hora de início")
        if horario.hora_inicio.hour < 6 or horario.hora_inicio.hour > 22:
            raise ValidationError("Aula deve começar entre 06:00 e 22:00")

        if "professor_id" in data.model_fields_set or "disciplina_id" in data.model_fields_set:
            await self._validar_professor_alocado(
                horario.turma_id, horario.professor_id, horario.disciplina_id,
            )

        if {"professor_id", "dia_semana", "hora_inicio", "hora_fim"} & data.model_fields_set:
            await self._validar_conflitos(
                turma_id=horario.turma_id,
                professor_id=horario.professor_id,
                dia_semana=horario.dia_semana,
                hora_inicio=horario.hora_inicio,
                hora_fim=horario.hora_fim,
                excluir_id=horario.id,
            )

        return await self._repo.update(horario)

    async def desativar(self, id: uuid.UUID) -> HorarioAula:
        horario = await self.get_by_id(id)
        if not horario.ativo:
            raise ValidationError("Janela de aula já está desativada")
        horario.ativo = False
        return await self._repo.update(horario)

    async def reativar(self, id: uuid.UUID) -> HorarioAula:
        horario = await self.get_by_id(id)
        if horario.ativo:
            return horario
        await self._validar_conflitos(
            turma_id=horario.turma_id,
            professor_id=horario.professor_id,
            dia_semana=horario.dia_semana,
            hora_inicio=horario.hora_inicio,
            hora_fim=horario.hora_fim,
            excluir_id=horario.id,
        )
        horario.ativo = True
        return await self._repo.update(horario)

    async def get_by_id(self, id: uuid.UUID) -> HorarioAula:
        horario = await self._repo.get_by_id(id)
        if horario is None:
            raise NotFound("Janela de aula não encontrada")
        return horario

    async def listar(
        self,
        turma_id: uuid.UUID | None = None,
        professor_id: uuid.UUID | None = None,
        dias: list[DiaSemana] | None = None,
        only_active: bool = True,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[HorarioAula], int]:
        return await self._repo.search(
            turma_id=turma_id, professor_id=professor_id, dias=dias,
            only_active=only_active, page=page, size=size,
        )

    async def listar_da_turma(
        self, turma_id: uuid.UUID, only_active: bool = True,
    ) -> list[HorarioAula]:
        await self._turma_repo.get_by_id(turma_id)
        return await self._repo.list_by_turma(turma_id, only_active=only_active)

    # ── Validações ──────────────────────────────────────────────────

    async def _validar_professor_alocado(
        self, turma_id: uuid.UUID, professor_id: uuid.UUID, disciplina_id: uuid.UUID | None,
    ) -> None:
        """O professor da janela tem que ser professor da turma.

        É a única coisa que amarra a agenda à autorização: é a `Alocacao` que dá ao
        professor acesso aos alunos da turma, então uma janela cujo professor não tem
        alocação produziria um aviso de ausência para alguém que nunca dá aula ali.
        """
        turma = await self._turma_repo.get_by_id(turma_id)
        if turma is None:
            raise NotFound("Turma não encontrada")
        if not turma.ativo:
            raise ValidationError("Não é possível montar a grade de uma turma inativa")

        if not await self._alocacao_repo.professor_leciona_turma(professor_id, turma_id):
            raise ValidationError(
                "Este professor não está alocado nesta turma. "
                "Cadastre a alocação antes de incluí-lo na grade.",
            )

        if disciplina_id is not None:
            alocacoes, _ = await self._alocacao_repo.search(
                professor_id=professor_id, turma_id=turma_id, only_active=True, size=100,
            )
            if all(a.disciplina_id != disciplina_id for a in alocacoes):
                raise ValidationError(
                    "Este professor não está alocado nesta disciplina da turma",
                )

    async def _validar_conflitos(
        self,
        turma_id: uuid.UUID,
        professor_id: uuid.UUID,
        dia_semana: DiaSemana,
        hora_inicio: time,
        hora_fim: time,
        excluir_id: uuid.UUID | None,
    ) -> None:
        """Nenhum dos dois lados pode ter janela sobreposta.

        Os dois conflitos são mensagens diferentes de propósito: "a turma já tem aula
        nesse horário" é erro da secretaria corrigindo a grade; "você já está dando aula
        em outra turma" é erro que aponta um professor escalado em dois lugares ao
        mesmo tempo — bem mais grave, e o professor precisa entender qual dos dois é.
        """
        da_turma = await self._repo.list_by_turma_dia(
            turma_id, dia_semana, only_active=True, excluir_id=excluir_id,
        )
        for janela in da_turma:
            if horarios_sobrepostos(hora_inicio, hora_fim, janela.hora_inicio, janela.hora_fim):
                raise Conflict(
                    f"A turma já tem aula das {janela.hora_inicio:%H:%M} às "
                    f"{janela.hora_fim:%H:%M} neste dia",
                )

        do_professor = await self._repo.list_by_professor_dia(
            professor_id, dia_semana, only_active=True, excluir_id=excluir_id,
        )
        for janela in do_professor:
            if horarios_sobrepostos(hora_inicio, hora_fim, janela.hora_inicio, janela.hora_fim):
                raise Conflict(
                    f"Este professor já tem aula das {janela.hora_inicio:%H:%M} às "
                    f"{janela.hora_fim:%H:%M} neste dia, em outra turma",
                )

    # ── Consulta do dia (usada pelo aviso de ausência) ──────────────

    async def aulas_do_dia_para_aluno(
        self,
        aluno_id: uuid.UUID,
        data: date | None = None,
        responsavel_id: uuid.UUID | None = None,
    ) -> AulasDoDiaResponse:
        """Janelas de hoje da turma em que o aluno está matriculado.

        `responsavel_id` só é obrigatório para quem não é staff. Passá-lo é o que
        impede a rota de virar um oráculo de qual turma e qual professor um aluno
        qualquer tem hoje; a secretaria o deixa `None`, porque para ela a informação
        já é autorizada pelo papel.
        """
        alvo = data or date.today()

        if responsavel_id is not None and not await self._vinculo_repo.exists(
            aluno_id, responsavel_id,
        ):
            raise Forbidden("Você não é responsável por este aluno")

        matricula = await self._matricula_repo.get_active_by_aluno(aluno_id)
        if matricula is None or matricula.status != StatusMatricula.ATIVA:
            return AulasDoDiaResponse(
                aluno_id=aluno_id, data=alvo, sem_aula=True,
                motivo_sem_aula="O aluno não possui matrícula ativa",
            )

        turma = await self._turma_repo.get_by_id(matricula.turma_id)
        dia = dia_semana_de(alvo)
        if dia is None:
            return AulasDoDiaResponse(
                aluno_id=aluno_id, data=alvo, sem_aula=True,
                motivo_sem_aula="Não há aula aos domingos",
                turma_id=turma.id, turma_codigo=turma.codigo, turma_turno=turma.turno.value,
            )

        janelas = await self._repo.list_by_turmas_dia([turma.id], dia, only_active=True)
        agora = agora_hora_escuela()

        return AulasDoDiaResponse(
            aluno_id=aluno_id,
            aluno_nome=matricula.aluno.nome if matricula.aluno else None,
            data=alvo,
            dia_semana=dia,
            sem_aula=not janelas,
            motivo_sem_aula=(
                "A turma não possui aulas cadastradas para este dia" if not janelas else None
            ),
            turma_id=turma.id,
            turma_codigo=turma.codigo,
            turma_turno=turma.turno.value,
            aulas=[
                AulaHojeResponse(
                    horario_id=j.id, hora_inicio=j.hora_inicio, hora_fim=j.hora_fim,
                    professor_id=j.professor_id,
                    professor_nome=(
                        j.professor.usuario.nome
                        if j.professor and j.professor.usuario else None
                    ),
                    disciplina_nome=j.disciplina.nome if j.disciplina else None,
                    em_curso=j.hora_inicio <= agora < j.hora_fim,
                )
                for j in janelas
            ],
            # Um professor pode ter duas janelas no mesmo dia (ex.: arte de manhã e
            # educação física à tarde). Notificar duas vezes seria ruído.
            professores_ids=list(dict.fromkeys(j.professor_id for j in janelas)),
            professores_nomes=list(dict.fromkeys(
                j.professor.usuario.nome
                for j in janelas if j.professor and j.professor.usuario
            )),
        )

    async def response_de(self, horario: HorarioAula) -> HorarioAulaResponse:
        return HorarioAulaResponse(
            id=horario.id,
            turma_id=horario.turma_id,
            turma_codigo=horario.turma.codigo if horario.turma else None,
            turma_turno=horario.turma.turno.value if horario.turma else None,
            professor_id=horario.professor_id,
            professor_nome=(
                horario.professor.usuario.nome
                if horario.professor and horario.professor.usuario else None
            ),
            disciplina_id=horario.disciplina_id,
            disciplina_nome=horario.disciplina.nome if horario.disciplina else None,
            dia_semana=horario.dia_semana,
            hora_inicio=horario.hora_inicio,
            hora_fim=horario.hora_fim,
            ativo=horario.ativo,
        )
