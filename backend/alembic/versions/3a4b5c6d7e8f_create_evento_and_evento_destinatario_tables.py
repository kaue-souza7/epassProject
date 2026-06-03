"""create evento and evento_destinatario tables

Revision ID: 3a4b5c6d7e8f
Revises: 2d3e4f5a6b7c
Create Date: 2026-06-01 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a4b5c6d7e8f"
down_revision: Union[str, None] = "2d3e4f5a6b7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eventos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local", sa.String(255), nullable=True),
        sa.Column("criado_por", sa.Uuid(), nullable=False),
        sa.Column(
            "perfil_criador",
            sa.Enum("admin", "secretaria", "professor", "responsavel", name="perfil"),
            nullable=False,
        ),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["criado_por"],
            ["usuarios.id"],
            name="fk_evento_criado_por",
        ),
    )
    op.create_index("ix_eventos_data_inicio", "eventos", ["data_inicio"])
    op.create_index("ix_eventos_criado_por", "eventos", ["criado_por"])
    op.create_index("ix_eventos_ativo", "eventos", ["ativo"])

    op.create_table(
        "evento_destinatarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evento_id", sa.Uuid(), nullable=False),
        sa.Column(
            "tipo_destino",
            sa.Enum("professor", "responsavel", "turma", name="tipodestinoevento"),
            nullable=False,
        ),
        sa.Column("destino_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["evento_id"],
            ["eventos.id"],
            name="fk_destinatario_evento",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_evento_destinatarios_evento_id",
        "evento_destinatarios",
        ["evento_id"],
    )
    op.create_index(
        "ix_evento_destinatarios_tipo_destino",
        "evento_destinatarios",
        ["tipo_destino", "destino_id"],
    )


def downgrade() -> None:
    op.drop_table("evento_destinatarios")
    op.drop_table("eventos")
    op.execute("DROP TYPE IF EXISTS tipodestinoevento")
