from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LiberacaoBoletim(Base):
    __tablename__ = "liberacoes_boletim"

    __table_args__ = (
        CheckConstraint("bimestre BETWEEN 1 AND 4", name="ck_liberacao_bimestre"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("professor_profiles.usuario_id"), nullable=False,
    )
    turma_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("turmas.id"), nullable=False,
    )
    disciplina_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("disciplinas.id"), nullable=False,
    )
    alocacao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alocacoes.id"), nullable=False,
    )
    ano_letivo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("anos_letivos.id"), nullable=False,
    )
    bimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    liberado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    alocacao: Mapped["Alocacao"] = relationship("Alocacao", lazy="selectin")


class PrazoLiberacao(Base):
    __tablename__ = "prazos_liberacao"

    __table_args__ = (
        CheckConstraint("bimestre BETWEEN 1 AND 4", name="ck_prazo_bimestre"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ano_letivo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("anos_letivos.id"), nullable=False,
    )
    bimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    data_limite: Mapped[date] = mapped_column(Date, nullable=False)
    hora_limite: Mapped[time] = mapped_column(Time, nullable=False, default=time(23, 59, 59))
    notificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
