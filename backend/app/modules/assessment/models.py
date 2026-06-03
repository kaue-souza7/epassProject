from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import TipoAvaliacao


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    __table_args__ = (
        CheckConstraint("peso > 0", name="ck_avaliacao_peso"),
        CheckConstraint("nota_maxima > 0", name="ck_avaliacao_nota_maxima"),
        CheckConstraint("bimestre BETWEEN 1 AND 4", name="ck_avaliacao_bimestre"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alocacao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alocacoes.id"), nullable=False,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[TipoAvaliacao] = mapped_column(SAEnum(TipoAvaliacao), nullable=False)
    peso: Mapped[int] = mapped_column(Integer, nullable=False)
    nota_maxima: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    bimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    data_aplicacao: Mapped[date] = mapped_column(Date, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    alocacao: Mapped["Alocacao"] = relationship("Alocacao", lazy="selectin")
    notas: Mapped[list["Nota"]] = relationship(
        "Nota", back_populates="avaliacao", lazy="selectin",
        cascade="all, delete-orphan",
    )


class Nota(Base):
    __tablename__ = "notas"

    __table_args__ = (
        CheckConstraint("valor >= 0", name="ck_nota_valor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avaliacao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False,
    )
    matricula_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("matriculas.id"), nullable=False,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    avaliacao: Mapped["Avaliacao"] = relationship("Avaliacao", back_populates="notas")
    matricula: Mapped["Matricula"] = relationship("Matricula", lazy="selectin")
