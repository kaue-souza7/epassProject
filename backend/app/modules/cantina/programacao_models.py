from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import DiaSemana, TipoProgramacao


class ProgramacaoCantina(Base):
    __tablename__ = "programacao_cantina"

    __table_args__ = (
        # Uma programação GERAL (padrão para todos os dias) por aluno.
        Index(
            "uq_programacao_aluno_geral",
            "aluno_id",
            unique=True,
            postgresql_where=text("tipo = 'GERAL'"),
            sqlite_where=text("tipo = 'GERAL'"),
        ),
        # Uma programação DIÁRIA por aluno/dia (tem prioridade sobre a GERAL).
        Index(
            "uq_programacao_aluno_diaria",
            "aluno_id",
            "dia_semana",
            unique=True,
            postgresql_where=text("tipo = 'DIARIA'"),
            sqlite_where=text("tipo = 'DIARIA'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=False, index=True,
    )
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True,
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(
        SAEnum(DiaSemana), nullable=False,
    )
    tipo: Mapped[TipoProgramacao] = mapped_column(
        SAEnum(TipoProgramacao), nullable=False, default=TipoProgramacao.DIARIA,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aluno: Mapped["Aluno"] = relationship("Aluno", lazy="selectin")
    responsavel: Mapped["Usuario"] = relationship("Usuario", lazy="selectin")
    itens: Mapped[list["ProgramacaoItem"]] = relationship(
        "ProgramacaoItem", back_populates="programacao", lazy="selectin",
        cascade="all, delete-orphan",
    )


class ProgramacaoItem(Base):
    __tablename__ = "programacao_itens"

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_programacao_item_quantidade"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    programacao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programacao_cantina.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False, index=True,
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)

    programacao: Mapped["ProgramacaoCantina"] = relationship(
        "ProgramacaoCantina", back_populates="itens", lazy="selectin",
    )
    produto: Mapped["Produto"] = relationship("Produto", lazy="selectin")
