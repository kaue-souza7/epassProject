import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import DiaSemana, TipoProgramacao


class ProgramacaoItemCreate(BaseModel):
    produto_id: uuid.UUID
    quantidade: int = Field(..., gt=0)


class ProgramacaoItemResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: str | None = None
    quantidade: int

    model_config = {"from_attributes": True}


class ProgramacaoCreate(BaseModel):
    aluno_id: uuid.UUID
    dia_semana: DiaSemana
    tipo: TipoProgramacao = TipoProgramacao.DIARIA
    itens: list[ProgramacaoItemCreate] = Field(..., min_length=1)
    observacoes: str | None = Field(None, max_length=500)


class ProgramacaoUpdate(BaseModel):
    itens: list[ProgramacaoItemCreate] | None = None
    tipo: TipoProgramacao | None = None
    observacoes: str | None = Field(None, max_length=500)
    ativo: bool | None = None


class ProgramacaoResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    responsavel_id: uuid.UUID
    dia_semana: DiaSemana
    tipo: TipoProgramacao
    ativo: bool
    observacoes: str | None
    itens: list[ProgramacaoItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProgramacaoSemanaResponse(BaseModel):
    aluno_id: uuid.UUID
    programacoes: list[ProgramacaoResponse]
