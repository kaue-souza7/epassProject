"""create matriculas table

Revision ID: 5d9e3f7b2a10
Revises: 4c8e2f6a1d30
Create Date: 2026-05-30 03:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5d9e3f7b2a10"
down_revision: Union[str, None] = "4c8e2f6a1d30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matriculas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), nullable=False),
        sa.Column("turma_id", sa.Uuid(), nullable=False),
        sa.Column("matricula_origem_id", sa.Uuid(), nullable=True),
        sa.Column("data_matricula", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ATIVA", "CONCLUIDA", "CANCELADA", name="statusmatricula"),
            nullable=False,
        ),
        sa.Column("data_saida", sa.Date(), nullable=True),
        sa.Column("motivo_saida", sa.String(255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["aluno_id"], ["alunos.id"],
            name="fk_matriculas_aluno_id",
        ),
        sa.ForeignKeyConstraint(
            ["turma_id"], ["turmas.id"],
            name="fk_matriculas_turma_id",
        ),
        sa.ForeignKeyConstraint(
            ["matricula_origem_id"], ["matriculas.id"],
            name="fk_matriculas_origem_id",
        ),
    )
    op.create_index("ix_matriculas_aluno_id", "matriculas", ["aluno_id"])
    op.create_index("ix_matriculas_turma_id", "matriculas", ["turma_id"])
    op.create_index("ix_matriculas_status", "matriculas", ["status"])
    op.execute("""
        CREATE UNIQUE INDEX uq_matriculas_ativa_por_aluno
        ON matriculas (aluno_id)
        WHERE status = 'ATIVA'
    """)


def downgrade() -> None:
    op.drop_index("uq_matriculas_ativa_por_aluno", table_name="matriculas")
    op.drop_table("matriculas")
