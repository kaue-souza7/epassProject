"""create programacao_cantina tables

programacao_cantina - Programacao semanal de lanches do responsavel
programacao_itens   - Itens de cada programacao

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='diasemana') THEN
                CREATE TYPE diasemana AS ENUM ('SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='tipoprogramacao') THEN
                CREATE TYPE tipoprogramacao AS ENUM ('DIARIA', 'GERAL');
            END IF;
        END
        $$;
    """)

    # ── Tabela: programacao_cantina ───────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS programacao_cantina (
            id UUID PRIMARY KEY,
            aluno_id UUID NOT NULL REFERENCES alunos(id),
            responsavel_id UUID NOT NULL REFERENCES usuarios(id),
            dia_semana diasemana NOT NULL,
            tipo tipoprogramacao NOT NULL DEFAULT 'DIARIA',
            ativo BOOLEAN NOT NULL DEFAULT true,
            observacoes VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_programacao_aluno_dia UNIQUE (aluno_id, dia_semana)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_programacao_aluno ON programacao_cantina (aluno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programacao_responsavel ON programacao_cantina (responsavel_id)")

    # ── Tabela: programacao_itens ─────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS programacao_itens (
            id UUID PRIMARY KEY,
            programacao_id UUID NOT NULL REFERENCES programacao_cantina(id) ON DELETE CASCADE,
            produto_id UUID NOT NULL REFERENCES produtos(id),
            quantidade INTEGER NOT NULL,
            CONSTRAINT ck_programacao_item_quantidade CHECK (quantidade > 0)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_programacao_item_programacao ON programacao_itens (programacao_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programacao_item_produto ON programacao_itens (produto_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS programacao_itens CASCADE")
    op.execute("DROP TABLE IF EXISTS programacao_cantina CASCADE")
    op.execute("DROP TYPE IF EXISTS tipoprogramacao")
    op.execute("DROP TYPE IF EXISTS diasemana")
