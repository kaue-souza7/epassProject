"""push_tickets: recibos de entrega do Expo Push Service

Permite confirmar a entrega real no dispositivo após o ticket imediato:
`/push/getReceipts` pode retornar `DeviceNotRegistered` (e outros erros) só
depois. Tokens inválidos são desativados e o envio de Aviso/Ocorrência nunca
depende disso.

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-09-25
"""

from alembic import op


revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS push_tickets (
            id UUID PRIMARY KEY,
            ticket_id VARCHAR(120) NOT NULL UNIQUE,
            usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            token VARCHAR(255) NOT NULL,
            criado_em TIMESTAMPTZ NOT NULL,
            verificado_em TIMESTAMPTZ,
            sucesso BOOLEAN,
            erro VARCHAR(120)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_push_tickets_usuario_id ON push_tickets (usuario_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_push_tickets_token ON push_tickets (token)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_push_tickets_pendentes "
        "ON push_tickets (criado_em) WHERE verificado_em IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS push_tickets CASCADE")
