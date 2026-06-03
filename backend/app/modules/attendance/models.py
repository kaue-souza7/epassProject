from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import StatusFrequencia


class Chamada(Base):
    __tablename__ = "chamadas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alocacao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alocacoes.id"), nullable=False,
    )
    data_hora_aula: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    alocacao: Mapped["Alocacao"] = relationship("Alocacao", lazy="selectin")
    frequencias: Mapped[list["Frequencia"]] = relationship(
        "Frequencia", back_populates="chamada", lazy="selectin",
        cascade="all, delete-orphan",
    )


class Frequencia(Base):
    __tablename__ = "frequencias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chamada_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chamadas.id", ondelete="CASCADE"), nullable=False,
    )
    matricula_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("matriculas.id"), nullable=False,
    )
    status: Mapped[StatusFrequencia] = mapped_column(SAEnum(StatusFrequencia), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    chamada: Mapped["Chamada"] = relationship("Chamada", back_populates="frequencias")
    matricula: Mapped["Matricula"] = relationship("Matricula", lazy="selectin")
