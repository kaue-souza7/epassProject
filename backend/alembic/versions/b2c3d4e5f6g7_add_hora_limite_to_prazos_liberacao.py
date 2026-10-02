"""add hora_limite to prazos_liberacao

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "prazos_liberacao",
        sa.Column("hora_limite", sa.Time(), nullable=False, server_default="23:59:59"),
    )


def downgrade() -> None:
    op.drop_column("prazos_liberacao", "hora_limite")
