"""Persistência do histórico de conversas da Atena (Fase 5).

O QUE ISTO É
------------
Guardar o que o usuário já perguntou para dar continuidade ("e a nota de
Matemática?"). Só isso.

O QUE ISTO NÃO É
-----------------
O histórico NÃO é fonte de autorização. Nenhuma consulta de escopo o usa: quem
decide o que o modelo pode ver continua sendo o `usuario_id` do token, o perfil
e os context builders. Guardar a conversa de outra pessoa não dá acesso aos
dados dela — o endpoint de leitura exige `usuario_id` da sessão e o contexto é
montado do zero a cada turno (ver `context/`).

A distinção importa porque é a porta clássica de IDOR: um histórico roubado
vira "conteúdo de outra pessoa" dentro do contexto do modelo. Como o histórico
entra no prompt marcado como dado não confiável e nunca no filtro de escopo, o
vazamento é neutro: no máximo o modelo vê texto antigo que ele mesmo já gerou.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.enums import PapelMensagemIA


def _agora() -> datetime:
    return datetime.now(UTC)


class Conversa(Base):
    """Uma conversa da Atena. Pertence a exatamente um usuário."""

    __tablename__ = "ai_conversas"
    __table_args__ = (
        CheckConstraint("char_length(titulo) <= 200", name="ck_ai_conversas_titulo"),
        Index("ix_ai_conversas_usuario_atualizada", "usuario_id", "atualizada_em"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    # ON DELETE CASCADE: excluir o usuário do SGE leva as conversas junto, e não
    # deixa órfãos com conteúdo pessoal.
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False,
    )
    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora, nullable=False,
    )
    # Serve para ordenar a lista do usuário e para saber se há conversa nova.
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora, onupdate=_agora, nullable=False,
    )


class Mensagem(Base):
    """Uma fala dentro de uma conversa."""

    __tablename__ = "ai_mensagens"
    __table_args__ = (
        Index("ix_ai_mensagens_conversa_criada", "conversa_id", "criado_em"),
        CheckConstraint(
            "char_length(conteudo) BETWEEN 1 AND 8000", name="ck_ai_mensagens_conteudo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    conversa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_conversas.id", ondelete="CASCADE"),
        nullable=False,
    )
    papel: Mapped[PapelMensagemIA] = mapped_column(
        SAEnum(PapelMensagemIA, name="papel_mensagem_ia"), nullable=False,
    )
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    # Metadados de auditoria da resposta. Guardam a intenção classificada e o
    # código do resultado ("ok", "sem_dados", ...). Não guardam dados do aluno:
    # o histórico não é armazenamento de dado escolar.
    intencao: Mapped[str | None] = mapped_column(String(60), nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora, nullable=False,
    )
