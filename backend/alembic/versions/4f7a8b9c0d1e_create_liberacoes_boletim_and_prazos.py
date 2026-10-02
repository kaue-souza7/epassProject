"""create liberacoes_boletim and prazos_liberacao tables

Revision ID: 4f7a8b9c0d1e
Revises: 5b6464842777
Create Date: 2026-08-31 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f7a8b9c0d1e"
down_revision: Union[str, None] = "5b6464842777"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "liberacoes_boletim",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("professor_id", sa.Uuid(), nullable=False),
        sa.Column("turma_id", sa.Uuid(), nullable=False),
        sa.Column("disciplina_id", sa.Uuid(), nullable=False),
        sa.Column("alocacao_id", sa.Uuid(), nullable=False),
        sa.Column("ano_letivo_id", sa.Uuid(), nullable=False),
        sa.Column("bimestre", sa.Integer(), nullable=False),
        sa.Column("liberado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("bimestre BETWEEN 1 AND 4", name="ck_liberacao_bimestre"),
        sa.ForeignKeyConstraint(["alocacao_id"], ["alocacoes.id"]),
        sa.ForeignKeyConstraint(["ano_letivo_id"], ["anos_letivos.id"]),
        sa.ForeignKeyConstraint(["disciplina_id"], ["disciplinas.id"]),
        sa.ForeignKeyConstraint(["professor_id"], ["professor_profiles.usuario_id"]),
        sa.ForeignKeyConstraint(["turma_id"], ["turmas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_liberacoes_professor_turma_bimestre",
        "liberacoes_boletim",
        ["professor_id", "turma_id", "bimestre"],
    )
    op.create_index(
        "ix_liberacoes_alocacao_bimestre",
        "liberacoes_boletim",
        ["alocacao_id", "bimestre"],
    )

    op.create_table(
        "prazos_liberacao",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ano_letivo_id", sa.Uuid(), nullable=False),
        sa.Column("bimestre", sa.Integer(), nullable=False),
        sa.Column("data_limite", sa.Date(), nullable=False),
        sa.Column("notificado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("bimestre BETWEEN 1 AND 4", name="ck_prazo_bimestre"),
        sa.ForeignKeyConstraint(["ano_letivo_id"], ["anos_letivos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prazos_ano_bimestre",
        "prazos_liberacao",
        ["ano_letivo_id", "bimestre"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("prazos_liberacao")
    op.drop_table("liberacoes_boletim")
