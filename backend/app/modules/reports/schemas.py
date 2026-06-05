import uuid
from decimal import Decimal
from datetime import date

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


class RelatorioFrequencia(BaseModel):
    matricula_id: uuid.UUID
    aluno_nome: str
    turma_codigo: str
    ano_letivo: int
    periodo_inicio: date
    periodo_fim: date
    total_aulas: int
    presencas: int
    faltas: int
    faltas_justificadas: int
    frequencia_media: float


class DisciplinaHistorico(BaseModel):
    disciplina_nome: str
    ano_letivo: int
    serie_nome: str
    situacao: SituacaoAluno
    media_final: Decimal | None = Field(default=None, decimal_places=2)


class HistoricoEscolar(BaseModel):
    aluno_id: uuid.UUID
    aluno_nome: str
    disciplinas: list[DisciplinaHistorico]


class DeclaracaoMatricula(BaseModel):
    matricula_id: uuid.UUID
    aluno_nome: str
    turma_codigo: str
    serie_nome: str
    ano_letivo: int
    data_emissao: date
    situacao: SituacaoAluno


class ComprovantePagamento(BaseModel):
    movimento_id: uuid.UUID
    descricao: str
    valor: Decimal = Field(decimal_places=2)
    data_pagamento: date
    forma_pagamento: str
    aluno_nome: str


class BimestreEvolucao(BaseModel):
    bimestre: int
    media_geral: float
    frequencia: float | None = None


class DadosEvolucao(BaseModel):
    matricula_id: uuid.UUID
    aluno_nome: str
    turma_codigo: str
    serie_nome: str
    ano_letivo: int
    bimestres: list[BimestreEvolucao]


class DocumentoPdf(BaseModel):
    id: str
    tipo: str
    url: str
    nome_arquivo: str
