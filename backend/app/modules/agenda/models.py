from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import Perfil, TipoDestinoEvento


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    local: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False,
    )
    perfil_criador: Mapped[Perfil] = mapped_column(SAEnum(Perfil), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    destinatarios: Mapped[list["EventoDestinatario"]] = relationship(
        "EventoDestinatario", back_populates="evento", lazy="selectin",
        cascade="all, delete-orphan",
    )
    criador: Mapped["Usuario"] = relationship("Usuario", lazy="selectin")


class EventoDestinatario(Base):
    __tablename__ = "evento_destinatarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("eventos.id", ondelete="CASCADE"), nullable=False,
    )
    tipo_destino: Mapped[TipoDestinoEvento] = mapped_column(SAEnum(TipoDestinoEvento), nullable=False)
    destino_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)

    evento: Mapped["Evento"] = relationship("Evento", back_populates="destinatarios")
