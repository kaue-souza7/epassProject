from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.shared.enums import SituacaoAluno


class MatriculaResumo(BaseModel):
    id: uuid.UUID
    aluno_nome: str
    turma_codigo: str
    data_matricula: date
    status: str


class AlocacaoResumo(BaseModel):
    id: uuid.UUID
    professor_nome: str
    turma_codigo: str
    disciplina_nome: str
    data_inicio: date


class OcupacaoTurma(BaseModel):
    turma_id: uuid.UUID
    turma_codigo: str
    vagas_total: int
    matriculas_ativas: int
    taxa_ocupacao: float


class AlunosPorSerie(BaseModel):
    serie_id: uuid.UUID
    serie_nome: str
    quantidade: int


class AdminCards(BaseModel):
    total_alunos_ativos: int
    total_professores_ativos: int
    total_turmas_ativas: int
    total_matriculas_ativas: int


class AdminDashboardResponse(BaseModel):
    cards: AdminCards
    ultimas_matriculas: list[MatriculaResumo]
    ultimas_alocacoes: list[AlocacaoResumo]
    top_ocupacao: list[OcupacaoTurma]
    alunos_por_serie: list[AlunosPorSerie]


class TurmaLotada(BaseModel):
    turma_id: uuid.UUID
    turma_codigo: str
    vagas_total: int
    matriculas_ativas: int


class SecretariaCards(BaseModel):
    matriculas_ativas: int
    matriculas_ano: int
    turmas_ativas: int
    alunos_sem_matricula: int


class SecretariaDashboardResponse(BaseModel):
    cards: SecretariaCards
    matriculas_recentes: list[MatriculaResumo]
    turmas_lotadas: list[TurmaLotada]


class AvaliacaoResumo(BaseModel):
    id: uuid.UUID
    titulo: str
    disciplina_nome: str
    turma_codigo: str
    data_aplicacao: date
    bimestre: int


class ChamadaResumo(BaseModel):
    id: uuid.UUID
    disciplina_nome: str
    turma_codigo: str
    data_hora_aula: datetime


class ProfessorCards(BaseModel):
    minhas_turmas: int
    minhas_disciplinas: int
    chamadas_realizadas: int
    avaliacoes_cadastradas: int


class ProfessorDashboardResponse(BaseModel):
    cards: ProfessorCards
    proximas_avaliacoes: list[AvaliacaoResumo]
    ultimas_chamadas: list[ChamadaResumo]


class FilhoResumo(BaseModel):
    aluno_id: uuid.UUID
    aluno_nome: str
    matricula_id: uuid.UUID | None = None
    turma_codigo: str | None = None
    situacao: SituacaoAluno | None = None
    media_geral: float | None = None
    frequencia_media: float | None = None


class ResponsavelCards(BaseModel):
    quantidade_filhos: int
    matriculas_ativas: int
    media_geral: float | None = None
    frequencia_media: float | None = None


class ResponsavelDashboardResponse(BaseModel):
    cards: ResponsavelCards
    filhos: list[FilhoResumo]
