import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class ConfiguracaoAcademicaCreate(BaseModel):
    ano_letivo_id: uuid.UUID
    media_aprovacao: Decimal = Field(decimal_places=2, gt=0)
    frequencia_minima: Decimal = Field(decimal_places=2, ge=0, le=100)
    possui_recuperacao: bool
    media_minima_recuperacao: Decimal | None = Field(default=None, decimal_places=2, ge=0)
    quantidade_periodos: int = Field(default=4, ge=2, le=6)


class ConfiguracaoAcademicaUpdate(BaseModel):
    media_aprovacao: Decimal | None = Field(default=None, decimal_places=2, gt=0)
    frequencia_minima: Decimal | None = Field(default=None, decimal_places=2, ge=0, le=100)
    possui_recuperacao: bool | None = None
    media_minima_recuperacao: Decimal | None = Field(default=None, decimal_places=2, ge=0)
    quantidade_periodos: int | None = Field(default=None, ge=2, le=6)
    ativo: bool | None = None


class ConfiguracaoAcademicaResponse(BaseModel):
    id: uuid.UUID
    ano_letivo_id: uuid.UUID
    media_aprovacao: Decimal
    frequencia_minima: Decimal
    possui_recuperacao: bool
    media_minima_recuperacao: Decimal | None
    quantidade_periodos: int
    ativo: bool

    model_config = {"from_attributes": True}
