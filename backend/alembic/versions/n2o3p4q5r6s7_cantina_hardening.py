"""cantina hardening

- pedidos: origem (RESPONSAVEL/PROGRAMACAO/CONSUMO_DIRETO) e data_referencia
  (dia local do pedido), com índice único por aluno/dia ignorando consumo direto
  e pedidos cancelados.
- programacao_cantina: permite GERAL + DIARIA coexistirem (índices parciais).
- cantina_config: timezone configurável + singleton garantido.
- movimentacoes: estorno único por consumo (idempotência sob concorrência).
- pedido_status_historico: auditoria de quem executou cada transição.

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "n2o3p4q5r6s7"
down_revision = "m1n2o3p4q5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum de origem do pedido ──────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='origempedido') THEN
                CREATE TYPE origempedido AS ENUM ('RESPONSAVEL', 'PROGRAMACAO', 'CONSUMO_DIRETO');
            END IF;
        END
        $$;
    """)

    # ── pedidos: origem + data_referencia ─────────────────────────
    op.execute(
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS origem origempedido "
        "NOT NULL DEFAULT 'RESPONSAVEL'"
    )
    op.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_referencia DATE")
    op.execute("""
        UPDATE pedidos
        SET data_referencia = (created_at AT TIME ZONE 'America/Sao_Paulo')::date
        WHERE data_referencia IS NULL
    """)
    op.execute("ALTER TABLE pedidos ALTER COLUMN data_referencia SET NOT NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_data_referencia ON pedidos (data_referencia)"
    )

    # Substitui o índice baseado em immut_date(created_at) por um índice
    # explícito no dia local de referência (consistente com a aplicação).
    op.execute("DROP INDEX IF EXISTS uq_pedido_aluno_dia")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pedido_aluno_dia
        ON pedidos (aluno_id, data_referencia)
        WHERE status != 'CANCELADO' AND origem != 'CONSUMO_DIRETO'
    """)

    # ── programacao_cantina: GERAL e DIARIA coexistem ─────────────
    op.execute(
        "ALTER TABLE programacao_cantina "
        "DROP CONSTRAINT IF EXISTS uq_programacao_aluno_dia"
    )
    # Remove GERAL duplicadas por aluno (mantém a mais recente) antes do índice.
    op.execute("""
        DELETE FROM programacao_cantina p
        USING programacao_cantina q
        WHERE p.tipo = 'GERAL' AND q.tipo = 'GERAL'
          AND p.aluno_id = q.aluno_id
          AND (q.updated_at > p.updated_at
               OR (q.updated_at = p.updated_at AND q.id > p.id))
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_programacao_aluno_geral
        ON programacao_cantina (aluno_id)
        WHERE tipo = 'GERAL'
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_programacao_aluno_diaria
        ON programacao_cantina (aluno_id, dia_semana)
        WHERE tipo = 'DIARIA'
    """)

    # ── cantina_config: timezone + singleton ──────────────────────
    op.execute(
        "ALTER TABLE cantina_config ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) "
        "DEFAULT 'America/Sao_Paulo'"
    )
    op.execute("""
        DELETE FROM cantina_config c
        USING cantina_config d
        WHERE c.id <> d.id AND c.updated_at < d.updated_at
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_cantina_config_singleton "
        "ON cantina_config ((true))"
    )

    # ── movimentacoes: estorno único por consumo ──────────────────
    op.execute("""
        DELETE FROM movimentacoes m
        USING movimentacoes n
        WHERE m.tipo = 'ESTORNO' AND n.tipo = 'ESTORNO'
          AND m.consumo_original_id = n.consumo_original_id
          AND m.created_at > n.created_at
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_movimentacao_estorno_consumo
        ON movimentacoes (consumo_original_id)
        WHERE tipo = 'ESTORNO'
    """)

    # ── pedido_status_historico ───────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS pedido_status_historico (
            id UUID PRIMARY KEY,
            pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
            status_anterior statuspedido,
            status_novo statuspedido NOT NULL,
            usuario_id UUID REFERENCES usuarios(id),
            observacao VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedido_status_historico_pedido "
        "ON pedido_status_historico (pedido_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pedido_status_historico CASCADE")
    op.execute("DROP INDEX IF EXISTS uq_movimentacao_estorno_consumo")
    op.execute("DROP INDEX IF EXISTS uq_cantina_config_singleton")
    op.execute("ALTER TABLE cantina_config DROP COLUMN IF EXISTS timezone")
    op.execute("DROP INDEX IF EXISTS uq_programacao_aluno_diaria")
    op.execute("DROP INDEX IF EXISTS uq_programacao_aluno_geral")
    op.execute(
        "ALTER TABLE programacao_cantina "
        "ADD CONSTRAINT uq_programacao_aluno_dia UNIQUE (aluno_id, dia_semana)"
    )
    op.execute("DROP INDEX IF EXISTS uq_pedido_aluno_dia")
    op.execute(
        "CREATE UNIQUE INDEX uq_pedido_aluno_dia "
        "ON pedidos (aluno_id, immut_date(created_at)) WHERE status != 'CANCELADO'"
    )
    op.execute("DROP INDEX IF EXISTS ix_pedidos_data_referencia")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS data_referencia")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS origem")
    op.execute("DROP TYPE IF EXISTS origempedido")