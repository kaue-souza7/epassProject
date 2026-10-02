"""create_cantina_config

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-09-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE cantina_config (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            aberta BOOLEAN NOT NULL DEFAULT true,
            horario_abertura VARCHAR(5),
            horario_fechamento VARCHAR(5),
            dias_funcionamento VARCHAR(100),
            prazo_pedido_minutos INTEGER,
            prazo_cancelamento_minutos INTEGER,
            observacoes VARCHAR(500),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    # Insert default config
    op.execute("INSERT INTO cantina_config (id, aberta) VALUES (gen_random_uuid(), true)")


def downgrade() -> None:
    op.drop_table("cantina_config")
