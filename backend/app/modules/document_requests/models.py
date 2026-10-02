from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.students.models import Aluno
from app.shared.enums import StatusSolicitacaoDocumento, TipoDocumento


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SolicitacaoDocumento(Base):
    """Pedido de um documento escolar feito por um responsável.

    A autorização vive em duas camadas: `responsavel_id` é sempre quem pediu
    (vem do token, nunca do corpo da requisição) e `aluno_id` precisa estar
    entre os alunos vinculados a esse responsável. Sem essa checagem no serviço,
    a rota viraria um IDOR — bastaria trocar o `aluno_id` no payload.
    """

    __tablename__ = "solicitacoes_documento"

    __table_args__ = (
        CheckConstraint(
            "char_length(observacoes) <= 1000",
            name="ck_solicitacao_documento_observacoes",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False,
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=False,
    )
    tipo: Mapped[TipoDocumento] = mapped_column(SAEnum(TipoDocumento), nullable=False)
    status: Mapped[StatusSolicitacaoDocumento] = mapped_column(
        SAEnum(StatusSolicitacaoDocumento),
        default=StatusSolicitacaoDocumento.PENDENTE,
        nullable=False,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Preenchido pela secretaria ao atender o pedido.
    resposta: Mapped[str | None] = mapped_column(Text, nullable=True)
    documento_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    atendido_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True,
    )
    atendido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False,
    )

    aluno: Mapped["Aluno"] = relationship("Aluno", lazy="selectin")
