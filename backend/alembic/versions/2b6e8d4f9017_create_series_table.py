"""create series table

Revision ID: 2b6e8d4f9017
Revises: 9a1d5c7b3f20
Create Date: 2026-05-30 02:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b6e8d4f9017"
down_revision: Union[str, None] = "9a1d5c7b3f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "series",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(50), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=True),
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
        sa.UniqueConstraint("numero", name="uq_series_numero"),
    )
    op.create_check_constraint(
        "ck_series_numero_positivo",
        "series",
        "numero > 0",
    )


def downgrade() -> None:
    op.drop_table("series")
