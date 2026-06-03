"""create alocacoes table

Revision ID: 8b2c4d6e8f0a
Revises: 7a1b2c3d4e5f
Create Date: 2026-05-30 05:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b2c4d6e8f0a"
down_revision: Union[str, None] = "7a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alocacoes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("professor_id", sa.Uuid(), nullable=False),
        sa.Column("turma_id", sa.Uuid(), nullable=False),
        sa.Column("disciplina_id", sa.Uuid(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "turma_id", "disciplina_id",
            name="uq_alocacao_turma_disciplina",
        ),
        sa.ForeignKeyConstraint(
            ["professor_id"], ["professor_profiles.usuario_id"],
            name="fk_alocacao_professor",
        ),
        sa.ForeignKeyConstraint(
            ["turma_id"], ["turmas.id"],
            name="fk_alocacao_turma",
        ),
        sa.ForeignKeyConstraint(
            ["disciplina_id"], ["disciplinas.id"],
            name="fk_alocacao_disciplina",
        ),
    )
    op.create_index("ix_alocacoes_professor", "alocacoes", ["professor_id"])
    op.create_index("ix_alocacoes_turma", "alocacoes", ["turma_id"])
    op.create_index("ix_alocacoes_disciplina", "alocacoes", ["disciplina_id"])


def downgrade() -> None:
    op.drop_table("alocacoes")
