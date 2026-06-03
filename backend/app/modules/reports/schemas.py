import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.shared.enums import SituacaoAluno


class DisciplinaBoletim(BaseModel):
    disciplina_id: uuid.UUID
    disciplina_nome: str
    nota_maxima: Decimal = Field(default=Decimal("10"), decimal_places=2)
    media: Decimal = Field(decimal_places=2)
    frequencia: float | None = None
    nota_recuperacao: Decimal | None = Field(default=None, decimal_places=2)
    media_pos_recuperacao: Decimal | None = Field(default=None, decimal_places=2)
    situacao: SituacaoAluno | None = None


class BoletimBimestral(BaseModel):
    matricula_id: uuid.UUID
    aluno_nome: str
    turma_codigo: str
    serie_nome: str
    ano_letivo: int
    bimestre: int
    disciplinas: list[DisciplinaBoletim]


class BoletimAnual(BaseModel):
    matricula_id: uuid.UUID
    aluno_nome: str
    turma_codigo: str
    serie_nome: str
    ano_letivo: int
    bimestres: list[BoletimBimestral]
    situacao_final: SituacaoAluno
    media_pre_recuperacao: Decimal | None = Field(default=None, decimal_places=2)
    media_pos_recuperacao: Decimal | None = Field(default=None, decimal_places=2)
