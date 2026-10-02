"""add_movimentacao_id_to_pedidos

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pedidos",
        sa.Column("movimentacao_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_pedidos_movimentacao_id",
        "pedidos",
        ["movimentacao_id"],
    )
    op.create_foreign_key(
        "fk_pedidos_movimentacao_id",
        "pedidos",
        "movimentacoes",
        ["movimentacao_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_pedidos_movimentacao_id", "pedidos", type_="foreignkey")
    op.drop_index("ix_pedidos_movimentacao_id", table_name="pedidos")
    op.drop_column("pedidos", "movimentacao_id")
