from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import StatusCarteira, TipoMovimentacao


class Wallet(Base):
    __tablename__ = "wallets"

    __table_args__ = (
        CheckConstraint("saldo >= 0", name="ck_wallet_saldo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), unique=True, nullable=False, index=True,
    )
    saldo: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[StatusCarteira] = mapped_column(
        SAEnum(StatusCarteira), default=StatusCarteira.ATIVA, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aluno: Mapped["Aluno"] = relationship("Aluno", lazy="selectin")
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        "Movimentacao", back_populates="wallet", lazy="selectin",
        cascade="all, delete-orphan",
    )


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_movimentacao_valor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("wallets.id"), nullable=False, index=True,
    )
    tipo: Mapped[TipoMovimentacao] = mapped_column(SAEnum(TipoMovimentacao), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    saldo_anterior: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    saldo_posterior: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="movimentacoes", lazy="selectin")
    criador: Mapped["Usuario | None"] = relationship("Usuario", lazy="selectin")
