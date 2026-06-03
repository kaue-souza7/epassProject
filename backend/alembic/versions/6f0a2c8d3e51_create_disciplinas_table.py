"""create disciplinas table

Revision ID: 6f0a2c8d3e51
Revises: 5d9e3f7b2a10
Create Date: 2026-05-30 04:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f0a2c8d3e51"
down_revision: Union[str, None] = "5d9e3f7b2a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "disciplinas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
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
        sa.UniqueConstraint("codigo", name="uq_disciplinas_codigo"),
        sa.UniqueConstraint("nome", name="uq_disciplinas_nome"),
    )
    op.create_index("ix_disciplinas_nome", "disciplinas", ["nome"])


def downgrade() -> None:
    op.drop_table("disciplinas")
