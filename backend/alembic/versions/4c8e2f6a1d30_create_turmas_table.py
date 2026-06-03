"""create turmas table

Revision ID: 4c8e2f6a1d30
Revises: 2b6e8d4f9017
Create Date: 2026-05-30 03:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c8e2f6a1d30"
down_revision: Union[str, None] = "2b6e8d4f9017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "turmas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(100), nullable=True),
        sa.Column("serie_id", sa.Uuid(), nullable=False),
        sa.Column("ano_letivo_id", sa.Uuid(), nullable=False),
        sa.Column(
            "turno",
            sa.Enum("MANHA", "TARDE", "INTEGRAL", name="turno"),
            nullable=False,
        ),
        sa.Column("vagas_total", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            ["serie_id"], ["series.id"],
            name="fk_turmas_serie_id",
        ),
        sa.ForeignKeyConstraint(
            ["ano_letivo_id"], ["anos_letivos.id"],
            name="fk_turmas_ano_letivo_id",
        ),
        sa.UniqueConstraint(
            "codigo", "ano_letivo_id",
            name="uq_turmas_codigo_ano",
        ),
    )
    op.create_check_constraint(
        "ck_turmas_vagas_positivo",
        "turmas",
        "vagas_total > 0",
    )


def downgrade() -> None:
    op.drop_table("turmas")
