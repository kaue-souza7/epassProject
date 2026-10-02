import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.shared.enums import CategoriaProduto, StatusPedido


# ── Produto ────────────────────────────────────────────────────────


class ProdutoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    descricao: str | None = Field(None, max_length=500)
    preco: Decimal = Field(..., gt=0, decimal_places=2)
    imagem_url: str | None = Field(None, max_length=500)
    categoria: CategoriaProduto = Field(CategoriaProduto.SALGADO)
    estoque_atual: int = Field(0, ge=0)
    estoque_minimo: int = Field(0, ge=0)
    codigo: str | None = Field(None, max_length=50)
    custo: Decimal | None = Field(None, ge=0, decimal_places=2)
    unidade_medida: str | None = Field("un", max_length=20)
    perecivel: bool = Field(False)
    data_validade: datetime | None = None


class ProdutoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=200)
    descricao: str | None = Field(None, max_length=500)
    preco: Decimal | None = Field(None, gt=0, decimal_places=2)
    imagem_url: str | None = Field(None, max_length=500)
    categoria: CategoriaProduto | None = None
    estoque_minimo: int | None = Field(None, ge=0)
    codigo: str | None = Field(None, max_length=50)
    custo: Decimal | None = Field(None, ge=0, decimal_places=2)
    unidade_medida: str | None = Field(None, max_length=20)
    perecivel: bool | None = None
    data_validade: datetime | None = None


class ProdutoResponse(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None
    preco: Decimal
    imagem_url: str | None
    categoria: CategoriaProduto
    estoque_atual: int
    estoque_minimo: int
    codigo: str | None = None
    custo: Decimal | None = None
    unidade_medida: str | None = None
    perecivel: bool = False
    data_validade: datetime | None = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Estoque ────────────────────────────────────────────────────────


class EstoqueOperacao(BaseModel):
    quantidade: int = Field(..., description="Quantidade para entrada (positivo) ou saída (negativo)")
    motivo: str | None = Field(None, max_length=255)


class EstoqueResponse(BaseModel):
    produto_id: uuid.UUID
    estoque_anterior: int
    quantidade: int
    estoque_atual: int
    motivo: str | None


# ── Menu público ───────────────────────────────────────────────────


class MenuItem(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None
    preco: Decimal
    imagem_url: str | None
    disponivel: bool
    perecivel: bool = False
    data_validade: datetime | None = None

    model_config = {"from_attributes": True}


class MenuResponse(BaseModel):
    itens: list[MenuItem]


# ── Pedido ─────────────────────────────────────────────────────────


class ItemPedidoCreate(BaseModel):
    produto_id: uuid.UUID
    quantidade: int = Field(..., gt=0)


class PedidoCreate(BaseModel):
    aluno_id: uuid.UUID
    itens: list[ItemPedidoCreate] = Field(..., min_length=1)
    observacoes: str | None = Field(None, max_length=500)


class ItemPedidoResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: str | None = None
    quantidade: int
    preco_unitario: Decimal
    preco_total: Decimal

    model_config = {"from_attributes": True}


class PedidoResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str | None = None
    responsavel_id: uuid.UUID
    status: StatusPedido
    valor_total: Decimal
    saldo_debitado: Decimal
    movimentacao_id: uuid.UUID | None = None
    observacoes: str | None
    itens: list[ItemPedidoResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PedidoListResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str | None = None
    aluno_turma: str | None = None
    status: StatusPedido
    valor_total: Decimal
    observacoes: str | None = None
    itens: list[ItemPedidoResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PedidoStatusResponse(BaseModel):
    id: uuid.UUID
    status: StatusPedido
    mensagem: str


# ── Consulta de Aluno (Cantina) ────────────────────────────────────


class CantinaStudentResponse(BaseModel):
    id: uuid.UUID
    nome: str
    turma: str | None = None
    saldo: Decimal
    autonomia_cantina: bool = False

    model_config = {"from_attributes": True}


# ── Autonomia ──────────────────────────────────────────────────────


class AutonomiaResponse(BaseModel):
    aluno_id: uuid.UUID
    autonomia_cantina: bool


class AutonomiaUpdate(BaseModel):
    autonomia_cantina: bool


# ── Consumo Direto ─────────────────────────────────────────────────


class ConsumoDiretoItem(BaseModel):
    produto_id: uuid.UUID
    quantidade: int = Field(..., gt=0)


class ConsumoDiretoRequest(BaseModel):
    aluno_id: uuid.UUID
    itens: list[ConsumoDiretoItem] = Field(..., min_length=1)
    idempotency_key: str | None = Field(None, max_length=120)


class ConsumoDiretoResponse(BaseModel):
    consumo_id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str | None = None
    valor_total: Decimal
    saldo_anterior: Decimal
    saldo_atual: Decimal
    movimentacao_id: uuid.UUID
    itens: list[ItemPedidoResponse]
    created_at: datetime


# ── Histórico de Estoque ─────────────────────────────────────────


class MovimentacaoEstoqueResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    tipo: str
    quantidade: int
    estoque_anterior: int
    estoque_atual: int
    motivo: str | None
    usuario_nome: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Configuração da Cantina ──────────────────────────────────────


class CantinaConfigResponse(BaseModel):
    id: uuid.UUID
    aberta: bool
    horario_abertura: str | None
    horario_fechamento: str | None
    dias_funcionamento: str | None
    prazo_pedido_minutos: int | None
    prazo_cancelamento_minutos: int | None
    timezone: str | None = None
    observacoes: str | None

    model_config = {"from_attributes": True}


class CantinaConfigUpdate(BaseModel):
    aberta: bool | None = None
    horario_abertura: str | None = Field(None, max_length=5)
    horario_fechamento: str | None = Field(None, max_length=5)
    dias_funcionamento: str | None = Field(None, max_length=100)
    prazo_pedido_minutos: int | None = Field(None, ge=0)
    prazo_cancelamento_minutos: int | None = Field(None, ge=0)
    timezone: str | None = Field(None, max_length=50)
    observacoes: str | None = Field(None, max_length=500)


# ── Dashboard ────────────────────────────────────────────────────


class DashboardVendaItem(BaseModel):
    id: uuid.UUID
    aluno_nome: str | None = None
    aluno_turma: str | None = None
    valor_total: Decimal
    status: StatusPedido
    tipo: str  # "pedido" ou "consumo_direto"
    produtos: list[dict] = []
    created_at: datetime


class DashboardProdutoVendido(BaseModel):
    produto_id: uuid.UUID
    produto_nome: str
    quantidade_vendida: int
    receita_total: Decimal


class DashboardAlertaEstoque(BaseModel):
    produto_id: uuid.UUID
    produto_nome: str
    estoque_atual: int
    estoque_minimo: int
    tipo: str  # "sem_estoque", "estoque_baixo", "perecivel_vencido", "perecivel_proximo_vencimento"
    dias_para_vencer: int | None = None


class DashboardVendaPorPeriodo(BaseModel):
    data: str
    vendas: Decimal
    quantidade: int


class DashboardResponse(BaseModel):
    vendas_do_dia: Decimal
    quantidade_vendas: int
    alunos_atendidos: int
    produtos_estoque_baixo: int
    vendas_por_periodo: list[DashboardVendaPorPeriodo]
    produtos_mais_vendidos: list[DashboardProdutoVendido]
    alertas_estoque: list[DashboardAlertaEstoque]
    ultimas_vendas: list[DashboardVendaItem]
