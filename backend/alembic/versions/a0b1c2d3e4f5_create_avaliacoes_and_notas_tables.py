"""create avaliacoes and notas tables

Revision ID: a0b1c2d3e4f5
Revises: 9c0d1e2f3a4b
Create Date: 2026-05-30 06:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "9c0d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "avaliacoes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alocacao_id", sa.Uuid(), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "PROVA", "TRABALHO", "ATIVIDADE",
                "RECUPERACAO", "SIMULADO", "OUTRO",
                name="tipoavaliacao",
            ),
            nullable=False,
        ),
        sa.Column("peso", sa.Integer(), nullable=False),
        sa.Column("nota_maxima", sa.Numeric(5, 2), nullable=False),
        sa.Column("bimestre", sa.Integer(), nullable=False),
        sa.Column("data_aplicacao", sa.Date(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "alocacao_id", "titulo", "bimestre",
            name="uq_avaliacao_alocacao_titulo_bimestre",
        ),
        sa.ForeignKeyConstraint(
            ["alocacao_id"], ["alocacoes.id"],
            name="fk_avaliacao_alocacao",
        ),
    )
    op.create_check_constraint("ck_avaliacao_peso", "avaliacoes", "peso > 0")
    op.create_check_constraint("ck_avaliacao_nota_maxima", "avaliacoes", "nota_maxima > 0")
    op.create_check_constraint(
        "ck_avaliacao_bimestre", "avaliacoes", "bimestre BETWEEN 1 AND 4",
    )
    op.create_index("ix_avaliacoes_alocacao", "avaliacoes", ["alocacao_id"])
    op.create_index("ix_avaliacoes_bimestre", "avaliacoes", ["bimestre"])

    op.create_table(
        "notas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("avaliacao_id", sa.Uuid(), nullable=False),
        sa.Column("matricula_id", sa.Uuid(), nullable=False),
        sa.Column("valor", sa.Numeric(5, 2), nullable=False),
        sa.Column("observacoes", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "avaliacao_id", "matricula_id",
            name="uq_nota_avaliacao_matricula",
        ),
        sa.ForeignKeyConstraint(
            ["avaliacao_id"], ["avaliacoes.id"],
            name="fk_nota_avaliacao", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["matricula_id"], ["matriculas.id"],
            name="fk_nota_matricula",
        ),
    )
    op.create_check_constraint("ck_nota_valor", "notas", "valor >= 0")
    op.create_index("ix_notas_avaliacao", "notas", ["avaliacao_id"])
    op.create_index("ix_notas_matricula", "notas", ["matricula_id"])


def downgrade() -> None:
    op.drop_table("notas")
    op.drop_table("avaliacoes")
    op.execute("DROP TYPE IF EXISTS tipoavaliacao")
