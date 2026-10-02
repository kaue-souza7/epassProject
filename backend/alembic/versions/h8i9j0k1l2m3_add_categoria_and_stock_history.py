"""add_categoria_and_stock_history

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-09-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types with UPPERCASE values matching StrEnum member names
    op.execute("DO $$ BEGIN CREATE TYPE categoriaproduto AS ENUM ('LANCHE', 'BEBIDA', 'ALIMENTO', 'DOCE', 'OUTRO'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE tipomovimentacaoestoque AS ENUM ('ENTRADA', 'SAIDA', 'AJUSTE'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    # Add categoria column to produtos
    op.execute("ALTER TABLE produtos ADD COLUMN categoria categoriaproduto NOT NULL DEFAULT 'LANCHE'")

    # Create movimentacoes_estoque table
    op.execute("""
        CREATE TABLE movimentacoes_estoque (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            produto_id UUID NOT NULL REFERENCES produtos(id),
            tipo tipomovimentacaoestoque NOT NULL,
            quantidade INTEGER NOT NULL,
            estoque_anterior INTEGER NOT NULL,
            estoque_atual INTEGER NOT NULL,
            motivo VARCHAR(255),
            usuario_id UUID REFERENCES usuarios(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_movimentacoes_estoque_produto_id ON movimentacoes_estoque (produto_id)")


def downgrade() -> None:
    op.drop_table("movimentacoes_estoque")
    op.execute("DROP TYPE IF EXISTS tipomovimentacaoestoque")
    op.execute("ALTER TABLE produtos DROP COLUMN IF EXISTS categoria")
    op.execute("DROP TYPE IF EXISTS categoriaproduto")
