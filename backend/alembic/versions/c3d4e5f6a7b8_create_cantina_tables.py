"""create cantina tables (produtos, pedidos, itens_pedido)

produtos     - Cardapio da cantina (nome, preco, estoque)
pedidos      - Pedidos do responsavel para o aluno
itens_pedido - Itens de cada pedido

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6g7
Create Date: 2026-09-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums (idempotent) ───────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='statuspedido') THEN
                CREATE TYPE statuspedido AS ENUM ('PENDENTE', 'APROVADO', 'EM_PRODUCAO', 'PRONTO', 'RETIRADO', 'CANCELADO');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='statusproduto') THEN
                CREATE TYPE statusproduto AS ENUM ('ATIVO', 'INATIVO');
            END IF;
        END
        $$;
    """)

    # ── Tabela: produtos ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id UUID PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            descricao VARCHAR(500),
            preco NUMERIC(10,2) NOT NULL,
            imagem_url VARCHAR(500),
            estoque_atual INTEGER NOT NULL DEFAULT 0,
            estoque_minimo INTEGER NOT NULL DEFAULT 0,
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_produto_preco CHECK (preco > 0),
            CONSTRAINT ck_produto_estoque_atual CHECK (estoque_atual >= 0),
            CONSTRAINT ck_produto_estoque_minimo CHECK (estoque_minimo >= 0)
        )
    """)

    # ── Tabela: pedidos ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id UUID PRIMARY KEY,
            aluno_id UUID NOT NULL REFERENCES alunos(id),
            responsavel_id UUID NOT NULL REFERENCES usuarios(id),
            status statuspedido NOT NULL DEFAULT 'PENDENTE',
            valor_total NUMERIC(10,2) NOT NULL,
            saldo_debitado NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            observacoes VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pedido_aluno ON pedidos (aluno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pedido_responsavel ON pedidos (responsavel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pedido_status ON pedidos (status)")

    # ── Tabela: itens_pedido ─────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id UUID PRIMARY KEY,
            pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
            produto_id UUID NOT NULL REFERENCES produtos(id),
            quantidade INTEGER NOT NULL,
            preco_unitario NUMERIC(10,2) NOT NULL,
            preco_total NUMERIC(10,2) NOT NULL,
            CONSTRAINT ck_item_pedido_quantidade CHECK (quantidade > 0)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_item_pedido_pedido ON itens_pedido (pedido_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_item_pedido_produto ON itens_pedido (produto_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS itens_pedido CASCADE")
    op.execute("DROP TABLE IF EXISTS pedidos CASCADE")
    op.execute("DROP TABLE IF EXISTS produtos CASCADE")
    op.execute("DROP TYPE IF EXISTS statusproduto")
    op.execute("DROP TYPE IF EXISTS statuspedido")
