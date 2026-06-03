import uuid
from datetime import datetime

from pydantic import BaseModel

from app.shared.enums import StatusFrequencia


class ChamadaAbrir(BaseModel):
    alocacao_id: uuid.UUID
    data_hora_aula: datetime


class FrequenciaRegistrar(BaseModel):
    matricula_id: uuid.UUID
    status: StatusFrequencia
    observacoes: str | None = None


class FrequenciaResponse(BaseModel):
    id: uuid.UUID
    chamada_id: uuid.UUID
    matricula_id: uuid.UUID
    status: StatusFrequencia
    observacoes: str | None

    model_config = {"from_attributes": True}


class ChamadaResponse(BaseModel):
    id: uuid.UUID
    alocacao_id: uuid.UUID
    data_hora_aula: datetime

    model_config = {"from_attributes": True}


class FrequenciaComMatriculaResponse(BaseModel):
    id: uuid.UUID
    chamada_id: uuid.UUID
    matricula_id: uuid.UUID
    matricula_codigo: str | None = None
    aluno_nome: str | None = None
    status: StatusFrequencia
    observacoes: str | None


class ChamadaDetalheResponse(BaseModel):
    id: uuid.UUID
    alocacao_id: uuid.UUID
    data_hora_aula: datetime
    frequencias: list[FrequenciaComMatriculaResponse]


class ChamadaComFrequencias(BaseModel):
    chamada: ChamadaResponse
    frequencias: list[FrequenciaResponse]
