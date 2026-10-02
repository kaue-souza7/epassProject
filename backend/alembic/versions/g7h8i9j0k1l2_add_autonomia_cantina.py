"""add autonomia_cantina to alunos

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-04 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alunos",
        sa.Column("autonomia_cantina", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute("UPDATE alunos SET autonomia_cantina = false WHERE autonomia_cantina IS NULL")


def downgrade() -> None:
    op.drop_column("alunos", "autonomia_cantina")
