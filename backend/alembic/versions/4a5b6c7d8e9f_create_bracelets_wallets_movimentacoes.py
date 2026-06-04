"""create bracelets, wallets, and movimentacoes tables

bracelets    - Pulseiras RFID/NFC vinculadas a alunos
wallets      - Carteira digital de cada aluno (saldo, status)
movimentacoes- Histórico financeiro (recarga, consumo, estorno)

Revision ID: 4a5b6c7d8e9f
Revises: 3a4b5c6d7e8f
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a5b6c7d8e9f"
down_revision: Union[str, None] = "3a4b5c6d7e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums (idempotent) ───────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='statuspulseira') THEN
                CREATE TYPE statuspulseira AS ENUM ('ATIVA', 'BLOQUEADA', 'CANCELADA');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='statuscarteira') THEN
                CREATE TYPE statuscarteira AS ENUM ('ATIVA', 'BLOQUEADA', 'CANCELADA');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='tipomovimentacao') THEN
                CREATE TYPE tipomovimentacao AS ENUM ('RECARGA', 'CONSUMO', 'ESTORNO');
            END IF;
        END
        $$;
    """)

    # ── Tabela: bracelets ───────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS bracelets (
            id UUID PRIMARY KEY,
            uid VARCHAR(50) NOT NULL,
            codigo VARCHAR(50) NOT NULL,
            aluno_id UUID REFERENCES alunos(id),
            status statuspulseira NOT NULL DEFAULT 'ATIVA',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_bracelet_aluno UNIQUE (aluno_id),
            CONSTRAINT uq_bracelet_uid UNIQUE (uid)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_bracelet_uid ON bracelets (uid)")

    # ── Tabela: wallets ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id UUID PRIMARY KEY,
            aluno_id UUID NOT NULL REFERENCES alunos(id),
            saldo NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            status statuscarteira NOT NULL DEFAULT 'ATIVA',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_wallet_saldo CHECK (saldo >= 0),
            CONSTRAINT uq_wallet_aluno UNIQUE (aluno_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wallet_aluno ON wallets (aluno_id)")

    # ── Tabela: movimentacoes ───────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id UUID PRIMARY KEY,
            wallet_id UUID NOT NULL REFERENCES wallets(id),
            tipo tipomovimentacao NOT NULL,
            valor NUMERIC(10,2) NOT NULL,
            saldo_anterior NUMERIC(10,2) NOT NULL,
            saldo_posterior NUMERIC(10,2) NOT NULL,
            descricao VARCHAR(255),
            criado_por UUID REFERENCES usuarios(id),
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_movimentacao_valor CHECK (valor > 0)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacao_wallet ON movimentacoes (wallet_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacao_wallet_created ON movimentacoes (wallet_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS movimentacoes CASCADE")
    op.execute("DROP TABLE IF EXISTS wallets CASCADE")
    op.execute("DROP TABLE IF EXISTS bracelets CASCADE")
    op.execute("DROP TYPE IF EXISTS tipomovimentacao")
    op.execute("DROP TYPE IF EXISTS statuscarteira")
    op.execute("DROP TYPE IF EXISTS statuspulseira")
