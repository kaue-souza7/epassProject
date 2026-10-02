from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import BaseModel, Field, model_validator

from app.shared.enums import DiaSemana


class HorarioAulaCreate(BaseModel):
    turma_id: uuid.UUID
    professor_id: uuid.UUID
    disciplina_id: uuid.UUID | None = None
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fim: time

    @model_validator(mode="after")
    def _validar_janela(self) -> HorarioAulaCreate:
        if self.hora_fim <= self.hora_inicio:
            raise ValueError("A hora de término deve ser depois da hora de início")
        if self.hora_inicio.hour < 6 or self.hora_inicio.hour > 22:
            raise ValueError("Aula deve começar entre 06:00 e 22:00")
        return self


class HorarioAulaUpdate(BaseModel):
    professor_id: uuid.UUID | None = None
    disciplina_id: uuid.UUID | None = None
    dia_semana: DiaSemana | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def _validar_janela(self) -> HorarioAulaUpdate:
        if (
            self.hora_inicio is not None
            and self.hora_fim is not None
            and self.hora_fim <= self.hora_inicio
        ):
            raise ValueError("A hora de término deve ser depois da hora de início")
        return self


class HorarioAulaResponse(BaseModel):
    id: uuid.UUID
    turma_id: uuid.UUID
    turma_codigo: str | None = None
    turma_turno: str | None = None
    professor_id: uuid.UUID
    professor_nome: str | None = None
    disciplina_id: uuid.UUID | None = None
    disciplina_nome: str | None = None
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fim: time
    ativo: bool = True

    model_config = {"from_attributes": True}


class GradeTurmaResponse(BaseModel):
    """Grade de uma turma, agrupada por dia.

    `aulas` vem achatado e ordenado por (dia, hora) — o agrupamento é responsabilidade
    do cliente, que também sabe filtrar por dia sem refazer a consulta.
    """

    turma_id: uuid.UUID
    turma_codigo: str
    turma_turno: str
    aulas: list[HorarioAulaResponse] = Field(default_factory=list)


class GradeGeralResponse(BaseModel):
    turmas: list[GradeTurmaResponse] = Field(default_factory=list)
    dias: list[DiaSemana] = Field(default_factory=list)


class AulaHojeResponse(BaseModel):
    """As janelas de hoje de uma turma — o que o botão de ausência precisa mostrar.

    `em_curso` diz se a janela contém o momento atual, o que permite pintar a aula
    corrente na grade em vez de tratar todas as aulas do dia como iguais.
    """

    horario_id: uuid.UUID
    hora_inicio: time
    hora_fim: time
    professor_id: uuid.UUID
    professor_nome: str | None = None
    disciplina_nome: str | None = None
    em_curso: bool = False


class AulasDoDiaResponse(BaseModel):
    aluno_id: uuid.UUID
    aluno_nome: str | None = None
    data: date
    dia_semana: DiaSemana | None = None
    sem_aula: bool = False
    motivo_sem_aula: str | None = None
    turma_id: uuid.UUID | None = None
    turma_codigo: str | None = None
    turma_turno: str | None = None
    aulas: list[AulaHojeResponse] = Field(default_factory=list)
    # Destinatários que o aviso de ausência vai notificar. Vai no payload para o
    # responsável confirmar "vou avisar a teacher da Maria" antes de confirmar, e para a
    # secretaria saber de antemão quem ficou sabendo.
    professores_ids: list[uuid.UUID] = Field(default_factory=list)
    professores_nomes: list[str] = Field(default_factory=list)
