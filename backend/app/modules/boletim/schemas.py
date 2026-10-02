import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field


class LiberacaoBoletimRequest(BaseModel):
    turma_id: uuid.UUID
    bimestre: int = Field(ge=1, le=4)


class DisciplinaLiberacaoStatus(BaseModel):
    disciplina_id: uuid.UUID
    disciplina_nome: str
    liberada: bool
    liberado_em: datetime | None = None


class LiberacaoStatusResponse(BaseModel):
    turma_id: uuid.UUID
    turma_codigo: str
    bimestre: int
    ano_letivo_id: uuid.UUID
    total_disciplinas_professor: int
    disciplinas_liberadas: list[DisciplinaLiberacaoStatus]
    todas_liberadas: bool


class LiberacaoBoletimResponse(BaseModel):
    id: uuid.UUID
    professor_id: uuid.UUID
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
    disciplina_nome: str
    alocacao_id: uuid.UUID
    ano_letivo_id: uuid.UUID
    bimestre: int
    liberado_em: datetime
    ativo: bool

    model_config = {"from_attributes": True}


class PrazoLiberacaoRequest(BaseModel):
    ano_letivo_id: uuid.UUID
    bimestre: int = Field(ge=1, le=4)
    data_limite: date
    hora_limite: time = Field(default=time(23, 59, 59), description="Horário de expiração (UTC)")


class PrazoLiberacaoResponse(BaseModel):
    id: uuid.UUID
    ano_letivo_id: uuid.UUID
    bimestre: int
    data_limite: date
    hora_limite: time
    notificado_em: datetime | None
    ativo: bool

    model_config = {"from_attributes": True}


class PrazoLiberacaoUpdate(BaseModel):
    data_limite: date | None = None
    hora_limite: time | None = None
    ativo: bool | None = None


class EmailCoordenadorRequest(BaseModel):
    email_coordenador: str | None = None
