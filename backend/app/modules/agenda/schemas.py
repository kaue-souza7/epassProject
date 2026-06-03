import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import Perfil, TipoDestinoEvento


class EventoDestinatarioCreate(BaseModel):
    tipo_destino: TipoDestinoEvento
    destino_id: uuid.UUID


class EventoCreate(BaseModel):
    titulo: str = Field(..., max_length=200)
    descricao: str | None = Field(None, max_length=2000)
    data_inicio: datetime
    data_fim: datetime | None = None
    local: str | None = Field(None, max_length=255)
    destinatarios: list[EventoDestinatarioCreate] = Field(default_factory=list)


class EventoUpdate(BaseModel):
    titulo: str | None = Field(None, max_length=200)
    descricao: str | None = Field(None, max_length=2000)
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    local: str | None = Field(None, max_length=255)
    destinatarios: list[EventoDestinatarioCreate] | None = None


class EventoDestinatarioResponse(BaseModel):
    id: uuid.UUID
    evento_id: uuid.UUID
    tipo_destino: TipoDestinoEvento
    destino_id: uuid.UUID

    model_config = {"from_attributes": True}


class EventoResponse(BaseModel):
    id: uuid.UUID
    titulo: str
    descricao: str | None
    data_inicio: datetime
    data_fim: datetime | None
    local: str | None
    criado_por: uuid.UUID
    perfil_criador: Perfil
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventoDetalheResponse(BaseModel):
    evento: EventoResponse
    destinatarios: list[EventoDestinatarioResponse]
