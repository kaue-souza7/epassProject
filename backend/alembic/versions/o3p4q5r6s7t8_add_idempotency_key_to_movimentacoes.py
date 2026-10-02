"""add idempotency key to movimentacoes

Adiciona `movimentacoes.idempotency_key` com índice único parcial para
garantir que recargas/consumos reenviados (retry, duplo clique) não sejam
aplicados duas vezes.

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "o3p4q5r6s7t8"
down_revision = "n2o3p4q5r6s7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "movimentacoes",
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
    )
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_movimentacao_idempotency_key
        ON movimentacoes (idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_movimentacao_idempotency_key")
    op.drop_column("movimentacoes", "idempotency_key")
