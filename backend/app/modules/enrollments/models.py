from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import StatusMatricula


class Matricula(Base):
    __tablename__ = "matriculas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=False,
    )
    turma_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("turmas.id"), nullable=False,
    )
    matricula_origem_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("matriculas.id"), nullable=True,
    )
    data_matricula: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StatusMatricula] = mapped_column(SAEnum(StatusMatricula), nullable=False)
    data_saida: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo_saida: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aluno: Mapped["Aluno"] = relationship("Aluno", lazy="selectin")
    turma: Mapped["Turma"] = relationship("Turma", lazy="selectin")
    matricula_origem: Mapped["Matricula | None"] = relationship(
        "Matricula", remote_side="Matricula.id", lazy="selectin",
    )
