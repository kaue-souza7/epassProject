import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.shared.enums import StatusMatricula


class MatriculaCreate(BaseModel):
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    observacoes: str | None = Field(None, max_length=500)


class MatriculaTransfer(BaseModel):
    nova_turma_id: uuid.UUID
    motivo: str = Field(..., max_length=255)
    data_transferencia: date | None = None


class MatriculaResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    matricula_origem_id: uuid.UUID | None
    data_matricula: date
    status: StatusMatricula
    data_saida: date | None
    motivo_saida: str | None
    observacoes: str | None

    model_config = {"from_attributes": True}


class MatriculaListResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str
    turma_id: uuid.UUID
    turma_codigo: str
    matricula_origem_id: uuid.UUID | None
    data_matricula: date
    status: StatusMatricula
    data_saida: date | None
    motivo_saida: str | None
    observacoes: str | None
