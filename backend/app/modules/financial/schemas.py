import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.shared.enums import StatusCarteira, TipoMovimentacao


class SaldoResponse(BaseModel):
    aluno_id: uuid.UUID
    saldo: Decimal

    model_config = {"from_attributes": True}


class WalletResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    saldo: Decimal
    status: StatusCarteira
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WalletDetailResponse(WalletResponse):
    aluno_nome: str | None = None


class RecargaRequest(BaseModel):
    valor: Decimal = Field(..., gt=0, decimal_places=2)
    aluno_id: uuid.UUID | None = None
    idempotency_key: str | None = Field(None, max_length=120)


class RecargaResponse(BaseModel):
    movimentacao_id: uuid.UUID
    saldo_anterior: Decimal
    valor: Decimal
    saldo_atual: Decimal


class ConsumoRequest(BaseModel):
    uid_pulseira: str = Field(..., max_length=50)
    valor: Decimal = Field(..., gt=0, decimal_places=2)
    descricao: str | None = Field(None, max_length=255)
    idempotency_key: str | None = Field(None, max_length=120)


class ConsumoResponse(BaseModel):
    movimentacao_id: uuid.UUID
    saldo_anterior: Decimal
    valor: Decimal
    saldo_atual: Decimal
    descricao: str | None


class EstornoResponse(BaseModel):
    movimentacao_id: uuid.UUID
    consumo_estornado_id: uuid.UUID
    saldo_anterior: Decimal
    valor: Decimal
    saldo_atual: Decimal


class MovimentacaoItem(BaseModel):
    id: uuid.UUID
    tipo: TipoMovimentacao
    valor: Decimal
    saldo_anterior: Decimal
    saldo_posterior: Decimal
    descricao: str | None
    criado_por: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtratoResponse(BaseModel):
    aluno_id: uuid.UUID
    movimentacoes: list[MovimentacaoItem]
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 0


class MovimentacaoDetailResponse(MovimentacaoItem):
    wallet_id: uuid.UUID
