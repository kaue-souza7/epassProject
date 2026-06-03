import uuid
from datetime import date

from pydantic import BaseModel


class AnoLetivoRequest(BaseModel):
    ano: int
    data_inicio: date
    data_fim: date


class AnoLetivoResponse(BaseModel):
    id: uuid.UUID
    ano: int
    data_inicio: date
    data_fim: date
    ativo: bool

    model_config = {"from_attributes": True}
