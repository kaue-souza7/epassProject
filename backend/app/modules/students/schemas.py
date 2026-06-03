import uuid
from datetime import date

from pydantic import BaseModel

from app.shared.enums import Parentesco, SituacaoAluno


class AlunoRequest(BaseModel):
    nome: str
    data_nascimento: date
    cpf: str | None = None
    rg: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    email: str | None = None
    data_entrada: date


class AlunoUpdateRequest(BaseModel):
    nome: str | None = None
    data_nascimento: date | None = None
    cpf: str | None = None
    rg: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    email: str | None = None
    ativo: bool | None = None


class AlunoResponse(BaseModel):
    id: uuid.UUID
    nome: str
    data_nascimento: date
    cpf: str | None
    rg: str | None
    endereco: str | None
    telefone: str | None
    email: str | None
    data_entrada: date
    ativo: bool

    model_config = {"from_attributes": True}


class MyChildrenResponse(BaseModel):
    id: uuid.UUID
    nome: str
    ativo: bool

    model_config = {"from_attributes": True}


class ResponsavelAlunoCreate(BaseModel):
    responsavel_id: uuid.UUID
    parentesco: Parentesco
    responsavel_financeiro: bool = False


class ResponsavelAlunoResponse(BaseModel):
    aluno_id: uuid.UUID
    responsavel_id: uuid.UUID
    parentesco: Parentesco
    responsavel_financeiro: bool

    model_config = {"from_attributes": True}


class HistoricoItem(BaseModel):
    matricula_id: uuid.UUID
    ano_letivo: int
    turma_codigo: str
    serie_nome: str
    data_matricula: date
    data_saida: date | None = None
    status: str
    situacao_final: SituacaoAluno | None = None
    media_final: float | None = None
    frequencia_final: float | None = None


class HistoricoEscolarResponse(BaseModel):
    aluno_id: uuid.UUID
    aluno_nome: str
    historico: list[HistoricoItem]
