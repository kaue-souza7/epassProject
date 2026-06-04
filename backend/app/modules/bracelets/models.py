from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import StatusPulseira


class Bracelet(Base):
    __tablename__ = "bracelets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uid: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), unique=True, nullable=True,
    )
    status: Mapped[StatusPulseira] = mapped_column(
        SAEnum(StatusPulseira), default=StatusPulseira.ATIVA, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aluno: Mapped["Aluno"] = relationship("Aluno", lazy="selectin")
