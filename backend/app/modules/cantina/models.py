from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.students.models import Aluno  # noqa: F401
from app.modules.users.models import Usuario  # noqa: F401
from app.shared.enums import (
    CategoriaProduto,
    OrigemPedido,
    StatusPedido,
    TipoMovimentacaoEstoque,
)


class Produto(Base):
    __tablename__ = "produtos"

    __table_args__ = (
        CheckConstraint("preco > 0", name="ck_produto_preco"),
        CheckConstraint("estoque_atual >= 0", name="ck_produto_estoque_atual"),
        CheckConstraint("estoque_minimo >= 0", name="ck_produto_estoque_minimo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    imagem_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    categoria: Mapped[CategoriaProduto] = mapped_column(
        SAEnum(CategoriaProduto), nullable=False, default=CategoriaProduto.SALGADO,
    )
    estoque_atual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estoque_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    codigo: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    custo: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    unidade_medida: Mapped[str | None] = mapped_column(String(20), nullable=True, default="un")
    perecivel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_validade: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    itens_pedido: Mapped[list["ItemPedido"]] = relationship(
        "ItemPedido", back_populates="produto", lazy="selectin",
    )


class Pedido(Base):
    __tablename__ = "pedidos"

    __table_args__ = (
        # Um único pedido agendado (responsável/programação) por aluno e por dia.
        # Consumo direto (venda no balcão) não entra na regra de pedido único.
        Index(
            "uq_pedido_aluno_dia",
            "aluno_id",
            "data_referencia",
            unique=True,
            postgresql_where=text(
                "status != 'CANCELADO' AND origem != 'CONSUMO_DIRETO'"
            ),
            sqlite_where=text(
                "status != 'CANCELADO' AND origem != 'CONSUMO_DIRETO'"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=False, index=True,
    )
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True,
    )
    origem: Mapped[OrigemPedido] = mapped_column(
        SAEnum(OrigemPedido),
        nullable=False,
        default=OrigemPedido.RESPONSAVEL,
        server_default=OrigemPedido.RESPONSAVEL.name,
    )
    data_referencia: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
    )
    status: Mapped[StatusPedido] = mapped_column(
        SAEnum(StatusPedido), nullable=False, default=StatusPedido.PENDENTE,
    )
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    saldo_debitado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    movimentacao_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("movimentacoes.id"), nullable=True, index=True,
    )
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancelado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aluno: Mapped["Aluno"] = relationship("Aluno", lazy="selectin")
    responsavel: Mapped["Usuario"] = relationship("Usuario", lazy="selectin")
    itens: Mapped[list["ItemPedido"]] = relationship(
        "ItemPedido", back_populates="pedido", lazy="selectin",
        cascade="all, delete-orphan",
    )
    historico: Mapped[list["PedidoStatusHistorico"]] = relationship(
        "PedidoStatusHistorico", back_populates="pedido", lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PedidoStatusHistorico.created_at",
    )


class PedidoStatusHistorico(Base):
    """Auditoria das transições de status (quem realizou cada ação)."""

    __tablename__ = "pedido_status_historico"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status_anterior: Mapped[StatusPedido | None] = mapped_column(
        SAEnum(StatusPedido), nullable=True,
    )
    status_novo: Mapped[StatusPedido] = mapped_column(
        SAEnum(StatusPedido), nullable=False,
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True,
    )
    observacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="historico", lazy="selectin")
    usuario: Mapped["Usuario | None"] = relationship("Usuario", lazy="selectin")


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_item_pedido_quantidade"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False, index=True,
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    preco_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="itens", lazy="selectin")
    produto: Mapped["Produto"] = relationship("Produto", back_populates="itens_pedido", lazy="selectin")


class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    produto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False, index=True,
    )
    tipo: Mapped[TipoMovimentacaoEstoque] = mapped_column(
        SAEnum(TipoMovimentacaoEstoque), nullable=False,
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    estoque_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    estoque_atual: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    produto: Mapped["Produto"] = relationship("Produto", lazy="selectin")
    usuario: Mapped["Usuario"] = relationship("Usuario", lazy="selectin")


class CantinaConfig(Base):
    __tablename__ = "cantina_config"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aberta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    horario_abertura: Mapped[str | None] = mapped_column(String(5), nullable=True)
    horario_fechamento: Mapped[str | None] = mapped_column(String(5), nullable=True)
    dias_funcionamento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prazo_pedido_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prazo_cancelamento_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="America/Sao_Paulo",
    )
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
