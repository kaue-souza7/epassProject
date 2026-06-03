"""create configuracoes_academicas table

Revision ID: f1e2d3c4b5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-05-30 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "configuracoes_academicas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ano_letivo_id", sa.Uuid(), nullable=False),
        sa.Column("media_aprovacao", sa.Numeric(4, 2), nullable=False),
        sa.Column("frequencia_minima", sa.Numeric(5, 2), nullable=False),
        sa.Column("possui_recuperacao", sa.Boolean(), nullable=False),
        sa.Column("media_minima_recuperacao", sa.Numeric(4, 2), nullable=True),
        sa.Column("quantidade_periodos", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["ano_letivo_id"],
            ["anos_letivos.id"],
            name="fk_config_ano_letivo",
        ),
        sa.UniqueConstraint("ano_letivo_id", name="uq_config_ano_letivo"),
    )
    op.create_check_constraint(
        "ck_config_media_aprovacao",
        "configuracoes_academicas",
        "media_aprovacao > 0",
    )
    op.create_check_constraint(
        "ck_config_frequencia_minima",
        "configuracoes_academicas",
        "frequencia_minima BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        "ck_config_quantidade_periodos",
        "configuracoes_academicas",
        "quantidade_periodos IN (2, 3, 4, 6)",
    )
    op.create_check_constraint(
        "ck_config_recuperacao_consistente",
        "configuracoes_academicas",
        "CASE WHEN possui_recuperacao = FALSE THEN media_minima_recuperacao IS NULL ELSE media_minima_recuperacao IS NOT NULL END",
    )

    op.execute("""
        INSERT INTO configuracoes_academicas (
            id, ano_letivo_id, media_aprovacao, frequencia_minima,
            possui_recuperacao, media_minima_recuperacao, quantidade_periodos, ativo,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(), id, 6.00, 75.00,
            TRUE, 4.00, 4, TRUE,
            now(), now()
        FROM anos_letivos
        WHERE id NOT IN (
            SELECT ano_letivo_id FROM configuracoes_academicas
        )
    """)


def downgrade() -> None:
    op.drop_table("configuracoes_academicas")
