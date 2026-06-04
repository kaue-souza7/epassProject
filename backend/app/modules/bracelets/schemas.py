import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import StatusPulseira


class BraceletRequest(BaseModel):
    uid: str = Field(..., max_length=50)
    codigo: str = Field(..., max_length=50)


class BraceletUpdateRequest(BaseModel):
    uid: str | None = Field(None, max_length=50)
    codigo: str | None = Field(None, max_length=50)


class BraceletResponse(BaseModel):
    id: uuid.UUID
    uid: str
    codigo: str
    aluno_id: uuid.UUID | None
    status: StatusPulseira
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BraceletDetailResponse(BraceletResponse):
    aluno_nome: str | None = None


class VincularAlunoRequest(BaseModel):
    aluno_id: uuid.UUID


class StatusBraceletUpdateResponse(BaseModel):
    bracelet_id: uuid.UUID
    status: StatusPulseira
    mensagem: str
