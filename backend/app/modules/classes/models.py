from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import Turno


class Turma(Base):
    __tablename__ = "turmas"

    __table_args__ = (
        CheckConstraint("vagas_total > 0", name="ck_turmas_vagas_positivo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serie_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("series.id"), nullable=False,
    )
    ano_letivo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("anos_letivos.id"), nullable=False,
    )
    turno: Mapped[Turno] = mapped_column(SAEnum(Turno), nullable=False)
    vagas_total: Mapped[int] = mapped_column(Integer, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    serie: Mapped["Serie"] = relationship("Serie", lazy="selectin")
    ano_letivo: Mapped["AnoLetivo"] = relationship("AnoLetivo", lazy="selectin")
