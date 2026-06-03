from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConfiguracaoAcademica(Base):
    __tablename__ = "configuracoes_academicas"

    __table_args__ = (
        CheckConstraint("media_aprovacao > 0", name="ck_config_media_aprovacao"),
        CheckConstraint(
            "frequencia_minima BETWEEN 0 AND 100",
            name="ck_config_frequencia_minima",
        ),
        CheckConstraint(
            "quantidade_periodos IN (2, 3, 4, 6)",
            name="ck_config_quantidade_periodos",
        ),
        CheckConstraint(
            "CASE WHEN possui_recuperacao = FALSE THEN media_minima_recuperacao IS NULL ELSE media_minima_recuperacao IS NOT NULL END",
            name="ck_config_recuperacao_consistente",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ano_letivo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("anos_letivos.id"), unique=True, nullable=False,
    )
    media_aprovacao: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    frequencia_minima: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    possui_recuperacao: Mapped[bool] = mapped_column(Boolean, nullable=False)
    media_minima_recuperacao: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    quantidade_periodos: Mapped[int] = mapped_column(Integer, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
