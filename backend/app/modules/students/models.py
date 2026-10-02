from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import Parentesco


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True, nullable=True)
    rg: Mapped[str | None] = mapped_column(String(20), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_entrada: Mapped[date] = mapped_column(Date, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    autonomia_cantina: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    responsaveis: Mapped[list["ResponsavelAluno"]] = relationship(
        "ResponsavelAluno", back_populates="aluno", lazy="selectin",
    )


class ResponsavelAluno(Base):
    __tablename__ = "responsavel_aluno"

    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), primary_key=True,
    )
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True,
    )
    parentesco: Mapped[Parentesco] = mapped_column(SAEnum(Parentesco), nullable=False)
    responsavel_financeiro: Mapped[bool] = mapped_column(Boolean, nullable=False)

    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="responsaveis", lazy="selectin")
