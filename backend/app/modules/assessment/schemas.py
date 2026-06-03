import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.shared.enums import TipoAvaliacao


class AvaliacaoCreate(BaseModel):
    alocacao_id: uuid.UUID
    titulo: str = Field(..., max_length=200)
    tipo: TipoAvaliacao
    peso: int = Field(..., gt=0)
    nota_maxima: Decimal = Field(default=Decimal("10"), gt=0, decimal_places=2)
    bimestre: int = Field(..., ge=1, le=4)
    data_aplicacao: date
    observacoes: str | None = Field(None, max_length=500)


class AvaliacaoUpdate(BaseModel):
    titulo: str | None = Field(None, max_length=200)
    data_aplicacao: date | None = None
    observacoes: str | None = Field(None, max_length=500)


class NotaLancar(BaseModel):
    matricula_id: uuid.UUID
    valor: Decimal = Field(..., ge=0, decimal_places=2)
    observacoes: str | None = Field(None, max_length=255)


class NotaCorrigir(BaseModel):
    valor: Decimal = Field(..., ge=0, decimal_places=2)
    observacoes: str | None = Field(None, max_length=255)


class NotaResponse(BaseModel):
    id: uuid.UUID
    avaliacao_id: uuid.UUID
    matricula_id: uuid.UUID
    valor: Decimal
    observacoes: str | None

    model_config = {"from_attributes": True}


class NotaComAlunoResponse(BaseModel):
    id: uuid.UUID
    avaliacao_id: uuid.UUID
    matricula_id: uuid.UUID
    aluno_nome: str | None = None
    valor: Decimal
    observacoes: str | None


class AvaliacaoResponse(BaseModel):
    id: uuid.UUID
    alocacao_id: uuid.UUID
    titulo: str
    tipo: TipoAvaliacao
    peso: int
    nota_maxima: Decimal
    bimestre: int
    data_aplicacao: date
    observacoes: str | None

    model_config = {"from_attributes": True}


class AvaliacaoComNotas(BaseModel):
    avaliacao: AvaliacaoResponse
    notas: list[NotaResponse]

    model_config = {"from_attributes": True}


class AvaliacaoGradesResponse(BaseModel):
    avaliacao: AvaliacaoResponse
    notas: list[NotaComAlunoResponse]
