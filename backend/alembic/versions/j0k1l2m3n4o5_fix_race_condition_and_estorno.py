"""fix race condition and estorno

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE OR REPLACE FUNCTION immut_date(tstz TIMESTAMPTZ) "
        "RETURNS DATE AS $$ SELECT tstz::DATE $$ LANGUAGE SQL IMMUTABLE"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_pedido_aluno_dia "
        "ON pedidos (aluno_id, immut_date(created_at)) "
        "WHERE status != 'CANCELADO'"
    )

    op.add_column(
        "movimentacoes",
        sa.Column("consumo_original_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_movimentacao_consumo_original",
        "movimentacoes",
        "movimentacoes",
        ["consumo_original_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_movimentacao_consumo_original",
        "movimentacoes",
        ["consumo_original_id"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_pedido_aluno_dia")
    op.execute("DROP FUNCTION IF EXISTS immut_date(tstz TIMESTAMPTZ)")
    op.drop_index("ix_movimentacao_consumo_original", table_name="movimentacoes")
    op.drop_constraint("fk_movimentacao_consumo_original", "movimentacoes", type_="foreignkey")
    op.drop_column("movimentacoes", "consumo_original_id")
