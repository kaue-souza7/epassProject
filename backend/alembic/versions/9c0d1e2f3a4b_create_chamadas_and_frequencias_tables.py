"""create chamadas and frequencias tables

Revision ID: 9c0d1e2f3a4b
Revises: 8b2c4d6e8f0a
Create Date: 2026-05-30 05:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c0d1e2f3a4b"
down_revision: Union[str, None] = "8b2c4d6e8f0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chamadas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alocacao_id", sa.Uuid(), nullable=False),
        sa.Column("data_hora_aula", sa.DateTime(timezone=True), nullable=False),
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
            "alocacao_id", "data_hora_aula",
            name="uq_chamada_aula",
        ),
        sa.ForeignKeyConstraint(
            ["alocacao_id"], ["alocacoes.id"],
            name="fk_chamada_alocacao",
        ),
    )
    op.create_index("ix_chamadas_data_hora", "chamadas", ["data_hora_aula"])

    op.create_table(
        "frequencias",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chamada_id", sa.Uuid(), nullable=False),
        sa.Column("matricula_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PRESENTE", "FALTA", "FALTA_JUSTIFICADA", name="statusfrequencia"),
            nullable=False,
        ),
        sa.Column("observacoes", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chamada_id", "matricula_id",
            name="uq_frequencia_aluno_chamada",
        ),
        sa.ForeignKeyConstraint(
            ["chamada_id"], ["chamadas.id"],
            name="fk_frequencia_chamada",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["matricula_id"], ["matriculas.id"],
            name="fk_frequencia_matricula",
        ),
    )
    op.create_index("ix_frequencias_chamada", "frequencias", ["chamada_id"])
    op.create_index("ix_frequencias_matricula", "frequencias", ["matricula_id"])


def downgrade() -> None:
    op.drop_table("frequencias")
    op.drop_table("chamadas")
    op.execute("DROP TYPE IF EXISTS statusfrequencia")
