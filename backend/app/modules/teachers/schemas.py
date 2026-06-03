import uuid
from datetime import date

from pydantic import BaseModel, Field


class ProfessorProfileCreate(BaseModel):
    usuario_id: uuid.UUID
    formacao_principal: str | None = Field(None, max_length=200)
    matricula_funcional: str | None = Field(None, max_length=50)
    data_contratacao: date | None = None
    observacoes: str | None = Field(None, max_length=500)


class ProfessorProfileUpdate(BaseModel):
    formacao_principal: str | None = Field(None, max_length=200)
    matricula_funcional: str | None = Field(None, max_length=50)
    data_contratacao: date | None = None
    observacoes: str | None = Field(None, max_length=500)
    ativo: bool | None = None


class ProfessorProfileResponse(BaseModel):
    usuario_id: uuid.UUID
    nome: str
    formacao_principal: str | None
    matricula_funcional: str | None
    data_contratacao: date | None
    observacoes: str | None
    ativo: bool
