import uuid

from pydantic import BaseModel, Field

from app.shared.enums import Turno


class TurmaRequest(BaseModel):
    codigo: str = Field(..., max_length=20)
    nome: str | None = Field(None, max_length=100)
    serie_id: uuid.UUID
    ano_letivo_id: uuid.UUID
    turno: Turno
    vagas_total: int = Field(..., gt=0)


class TurmaUpdateRequest(BaseModel):
    codigo: str | None = Field(None, max_length=20)
    nome: str | None = Field(None, max_length=100)
    turno: Turno | None = None
    vagas_total: int | None = Field(None, gt=0)
    ativo: bool | None = None


class TurmaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nome: str | None
    serie_id: uuid.UUID
    ano_letivo_id: uuid.UUID
    turno: Turno
    vagas_total: int
    ativo: bool

    model_config = {"from_attributes": True}
