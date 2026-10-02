from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import StatusSolicitacaoDocumento, TipoDocumento


class CriarSolicitacaoDocumentoRequest(BaseModel):
    aluno_id: uuid.UUID
    tipo: TipoDocumento
    observacoes: str | None = Field(default=None, max_length=1000)


class AtualizarSolicitacaoDocumentoRequest(BaseModel):
    """Usado pela secretaria para responder a um pedido."""

    status: StatusSolicitacaoDocumento
    resposta: str | None = Field(default=None, max_length=2000)
    documento_url: str | None = Field(default=None, max_length=500)


class SolicitacaoDocumentoResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str | None = None
    tipo: TipoDocumento
    status: StatusSolicitacaoDocumento
    observacoes: str | None = None
    resposta: str | None = None
    documento_url: str | None = None
    atendido_em: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
