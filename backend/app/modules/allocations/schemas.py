import uuid
from datetime import date

from pydantic import BaseModel


class AlocacaoCreate(BaseModel):
    professor_id: uuid.UUID
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
    data_inicio: date | None = None


class AlocacaoEncerrar(BaseModel):
    data_fim: date
    motivo: str | None = None


class AlocacaoResponse(BaseModel):
    id: uuid.UUID
    professor_id: uuid.UUID
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
    data_inicio: date
    data_fim: date | None

    model_config = {"from_attributes": True}
