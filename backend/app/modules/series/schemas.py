import uuid

from pydantic import BaseModel, Field


class SerieRequest(BaseModel):
    numero: int = Field(..., ge=1, le=9)
    nome: str = Field(..., max_length=50)
    descricao: str | None = Field(None, max_length=255)


class SerieUpdateRequest(BaseModel):
    nome: str | None = Field(None, max_length=50)
    descricao: str | None = Field(None, max_length=255)
    ativo: bool | None = None


class SerieResponse(BaseModel):
    id: uuid.UUID
    numero: int
    nome: str
    descricao: str | None
    ativo: bool

    model_config = {"from_attributes": True}
