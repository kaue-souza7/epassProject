"""create anos_letivos table

Revision ID: 8f4c3a21b5e9
Revises: 3745582af902
Create Date: 2026-05-30 01:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f4c3a21b5e9"
down_revision: Union[str, None] = "3745582af902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anos_letivos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.UniqueConstraint("ano", name="uq_anos_letivos_ano"),
    )
    op.create_check_constraint(
        "ck_ano_letivo_datas",
        "anos_letivos",
        "data_inicio < data_fim",
    )


def downgrade() -> None:
    op.drop_table("anos_letivos")
