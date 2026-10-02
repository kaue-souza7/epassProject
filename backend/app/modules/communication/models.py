from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import (
    PrioridadeAviso,
    SeveridadeOcorrencia,
    StatusAviso,
    StatusOcorrencia,
    TipoAviso,
    TipoNotificacao,
    TipoOcorrencia,
)


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=True, index=True,
    )
    turma_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("turmas.id"), nullable=True, index=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[TipoOcorrencia] = mapped_column(
        SAEnum(TipoOcorrencia, native_enum=False, length=20, create_constraint=True, name="ck_ocorrencias_tipo"), nullable=False, default=TipoOcorrencia.COMPORTAMENTO,
    )
    severidade: Mapped[SeveridadeOcorrencia] = mapped_column(
        SAEnum(SeveridadeOcorrencia, native_enum=False, length=10, create_constraint=True, name="ck_ocorrencias_severidade"), nullable=False, default=SeveridadeOcorrencia.MEDIA,
    )
    status: Mapped[StatusOcorrencia] = mapped_column(
        SAEnum(StatusOcorrencia, native_enum=False, length=20, create_constraint=True, name="ck_ocorrencias_status"), nullable=False, default=StatusOcorrencia.ABERTA,
    )
    criado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False,
    )
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True, index=True,
    )
    resolvida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aluno: Mapped["Aluno | None"] = relationship("Aluno", lazy="selectin")
    turma: Mapped["Turma | None"] = relationship("Turma", lazy="selectin")
    criador: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[criado_por], lazy="selectin")
    responsavel: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[responsavel_id], lazy="selectin",
    )
    historico: Mapped[list["OcorrenciaHistorico"]] = relationship(
        "OcorrenciaHistorico", back_populates="ocorrencia", lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OcorrenciaHistorico.created_at",
    )


class OcorrenciaHistorico(Base):
    """Registro de cada alteração da ocorrência (status, descrição, etc.)."""

    __tablename__ = "ocorrencias_historico"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocorrencia_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ocorrencias.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status_anterior: Mapped[StatusOcorrencia | None] = mapped_column(
        SAEnum(StatusOcorrencia, native_enum=False, length=20, create_constraint=True, name="ck_ocorrencias_hist_status_anterior"), nullable=True,
    )
    status_novo: Mapped[StatusOcorrencia | None] = mapped_column(
        SAEnum(StatusOcorrencia, native_enum=False, length=20, create_constraint=True, name="ck_ocorrencias_hist_status_novo"), nullable=True,
    )
    acao: Mapped[str] = mapped_column(String(255), nullable=False)
    autor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    ocorrencia: Mapped["Ocorrencia"] = relationship(
        "Ocorrencia", back_populates="historico", lazy="selectin",
    )


class Aviso(Base):
    __tablename__ = "avisos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    # Enums de verdade (VARCHAR + CHECK), não string livre: o front desenha o cartao
    # com cor a partir da prioridade, e um valor fora do dominio viraria um cartao
    # sem cor nenhuma em vez de um erro visível no cadastro.
    tipo: Mapped[TipoAviso] = mapped_column(
        SAEnum(TipoAviso, native_enum=False, length=20, create_constraint=True, name="ck_avisos_tipo"),
        nullable=False, default=TipoAviso.GERAL,
    )
    prioridade: Mapped[PrioridadeAviso] = mapped_column(
        SAEnum(PrioridadeAviso, native_enum=False, length=20, create_constraint=True, name="ck_avisos_prioridade"),
        nullable=False, default=PrioridadeAviso.MEDIA,
    )
    destinatario_aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=True, index=True,
    )
    destinatario_turma_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("turmas.id"), nullable=True, index=True,
    )
    permite_respostas: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    status: Mapped[StatusAviso] = mapped_column(
        SAEnum(StatusAviso, native_enum=False, length=20, create_constraint=True, name="ck_avisos_status"), nullable=False, default=StatusAviso.PUBLICADO,
    )
    criado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False,
    )
    publicado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    criador: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[criado_por], lazy="selectin")
    aluno: Mapped["Aluno | None"] = relationship("Aluno", lazy="selectin")
    turma: Mapped["Turma | None"] = relationship("Turma", lazy="selectin")
    destinatarios: Mapped[list["AvisoDestinatario"]] = relationship(
        "AvisoDestinatario", back_populates="aviso", lazy="selectin",
        cascade="all, delete-orphan",
    )
    mensagens: Mapped[list["AvisoMensagem"]] = relationship(
        "AvisoMensagem", back_populates="aviso", lazy="selectin",
        cascade="all, delete-orphan",
        order_by="AvisoMensagem.created_at",
    )


class AvisoDestinatario(Base):
    """Destinatário materializado do aviso, com estado de leitura individual.

    O mesmo aviso pode ter vários destinatários (professores e responsáveis).
    Cada linha representa um destinatário e possui seu próprio estado de leitura
    e escalonamento.
    """

    __tablename__ = "avisos_destinatarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aviso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("avisos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True,
    )
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alunos.id"), nullable=True, index=True,
    )
    lido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    __table_args__ = (
        Index("uq_aviso_destinatario", "aviso_id", "usuario_id", unique=True),
    )

    aviso: Mapped["Aviso"] = relationship("Aviso", back_populates="destinatarios", lazy="selectin")
    usuario: Mapped["Usuario"] = relationship("Usuario", lazy="selectin")
    aluno: Mapped["Aluno | None"] = relationship("Aluno", lazy="selectin")


class AvisoMensagem(Base):
    """Mensagem da conversa do aviso (resposta do destinatário ou do autor).

    Cada linha é uma mensagem endereçada a um único destinatário, evitando
    duplicação quando o aviso possui múltiplos destinatários. O status de
    leitura é individual por mensagem.
    """

    __tablename__ = "avisos_mensagens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aviso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("avisos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True,
    )
    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True,
    )
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    aviso: Mapped["Aviso"] = relationship("Aviso", back_populates="mensagens", lazy="selectin")
    autor: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[autor_id], lazy="selectin")
    destinatario: Mapped["Usuario"] = relationship(
        "Usuario", foreign_keys=[destinatario_id], lazy="selectin",
    )


class PushTicket(Base):
    """Ticket de envio retornado pelo Expo Push Service.

    Permite conferir o recibo de entrega (`/push/getReceipts`) depois: erros
    como `DeviceNotRegistered` podem aparecer apenas no recibo, não no ticket.
    """

    __tablename__ = "push_tickets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    verificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sucesso: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    erro: Mapped[str | None] = mapped_column(String(120), nullable=True)


class PushToken(Base):
    """Token de push (Expo) associado a um usuário/dispositivo."""

    __tablename__ = "push_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    plataforma: Mapped[str] = mapped_column(String(20), nullable=False, default="expo")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notificacao(Base):
    """Notificação persistida do sistema central de notificações."""

    __tablename__ = "notificacoes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True,
    )
    tipo: Mapped[TipoNotificacao] = mapped_column(
        SAEnum(TipoNotificacao, native_enum=False, length=20, create_constraint=True, name="ck_notificacoes_tipo"), nullable=False, default=TipoNotificacao.SISTEMA,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    canal: Mapped[str] = mapped_column(String(30), nullable=False, default="inapp")
    entidade_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    evento_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dados: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    __table_args__ = (
        # Idempotência: uma notificação por destinatário/evento (retries não duplicam).
        Index(
            "uq_notificacao_evento",
            "destinatario_id",
            "evento_key",
            unique=True,
            postgresql_where=text("evento_key IS NOT NULL"),
        ),
    )

    destinatario: Mapped["Usuario"] = relationship("Usuario", lazy="selectin")


class PreferenciaNotificacao(Base):
    """Preferência de canal de entrega por tipo de notificação.

    Uma linha por (usuário, tipo). `email` começa desligado: o e-mail é
    opt-in explícito, então cadastrar a conta não passa a disparar mensagens
    para fora da escola. A ausência da linha equivale a "desligado".
    """

    __tablename__ = "preferencias_notificacoes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tipo: Mapped[TipoNotificacao] = mapped_column(
        SAEnum(
            TipoNotificacao, native_enum=False, length=20,
            create_constraint=True, name="ck_preferencias_notificacoes_tipo",
        ),
        nullable=False,
    )
    email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # Uma preferência por tipo; o upsert do repositório depende disso.
        UniqueConstraint("usuario_id", "tipo", name="uq_preferencia_notificacao_tipo"),
    )
