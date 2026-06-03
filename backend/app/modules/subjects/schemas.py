import uuid

from pydantic import BaseModel, Field


class DisciplinaRequest(BaseModel):
    codigo: str = Field(..., max_length=20)
    nome: str = Field(..., max_length=100)
    descricao: str | None = Field(None, max_length=255)


class DisciplinaUpdateRequest(BaseModel):
    nome: str | None = Field(None, max_length=100)
    descricao: str | None = Field(None, max_length=255)
    ativo: bool | None = None


class DisciplinaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nome: str
    descricao: str | None
    ativo: bool

    model_config = {"from_attributes": True}
