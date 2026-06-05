import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProfessorTurmaDisciplina(BaseModel):
    alocacao_id: uuid.UUID
    turma_id: uuid.UUID
    turma_codigo: str
    turma_nome: str | None = None
    disciplina_id: uuid.UUID
    disciplina_nome: str
    serie_nome: str
    ano_letivo: int
    turno: str
    total_alunos: int = 0


class ProfessorTurmaAluno(BaseModel):
    matricula_id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str
    numero_chamada: int | None = None
    presente: bool | None = None


class FrequenciaSalvarItem(BaseModel):
    matricula_id: uuid.UUID
    presente: bool


class FrequenciaSalvarRequest(BaseModel):
    turma_id: uuid.UUID
    data: date
    frequencias: list[FrequenciaSalvarItem]


class NotaSalvarItem(BaseModel):
    matricula_id: uuid.UUID
    valor: Decimal = Field(..., ge=0, decimal_places=2)


class NotaSalvarRequest(BaseModel):
    avaliacao_id: uuid.UUID
    notas: list[NotaSalvarItem]


class ProfessorAvaliacao(BaseModel):
    id: uuid.UUID
    alocacao_id: uuid.UUID
    titulo: str
    tipo: str
    peso: int
    nota_maxima: Decimal
    bimestre: int
    data_aplicacao: date


class FrequenciaSalvarResponse(BaseModel):
    chamada_id: uuid.UUID
    message: str = "Frequência salva com sucesso"


class NotaSalvarResponse(BaseModel):
    message: str = "Notas salvas com sucesso"
