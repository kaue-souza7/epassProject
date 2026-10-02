"""extend produto and adapt categoria

Revision ID: m1n2o3p4q5r6
Revises: k1l2m3n4o5p6
Create Date: 2026-09-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "m1n2o3p4q5r6"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to produtos
    op.add_column("produtos", sa.Column("codigo", sa.String(50), nullable=True))
    op.add_column("produtos", sa.Column("custo", sa.Numeric(10, 2), nullable=True))
    op.add_column("produtos", sa.Column("unidade_medida", sa.String(20), nullable=True, server_default="un"))
    op.add_column("produtos", sa.Column("perecivel", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("produtos", sa.Column("data_validade", sa.DateTime(timezone=True), nullable=True))

    # Add unique constraint on codigo
    op.create_unique_constraint("uq_produto_codigo", "produtos", ["codigo"])

    # Add new enum values to CategoriaProduto (must be committed before use)
    # ALTER TYPE ADD VALUE exige transação própria → autocommit_block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE categoriaproduto ADD VALUE IF NOT EXISTS 'SALGADO'")
        op.execute("ALTER TYPE categoriaproduto ADD VALUE IF NOT EXISTS 'LANCHE_QUENTE'")
        op.execute("ALTER TYPE categoriaproduto ADD VALUE IF NOT EXISTS 'LANCHE_NATURAL'")
        op.execute("ALTER TYPE categoriaproduto ADD VALUE IF NOT EXISTS 'BOMBONIERE'")


def downgrade() -> None:
    op.drop_constraint("uq_produto_codigo", "produtos", type_="unique")
    op.drop_column("produtos", "data_validade")
    op.drop_column("produtos", "perecivel")
    op.drop_column("produtos", "unidade_medida")
    op.drop_column("produtos", "custo")
    op.drop_column("produtos", "codigo")
