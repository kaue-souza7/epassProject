"""create alunos and responsavel_aluno tables

Revision ID: 9a1d5c7b3f20
Revises: 8f4c3a21b5e9
Create Date: 2026-05-30 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a1d5c7b3f20"
down_revision: Union[str, None] = "8f4c3a21b5e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alunos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=False),
        sa.Column("cpf", sa.String(11), nullable=True),
        sa.Column("rg", sa.String(20), nullable=True),
        sa.Column("endereco", sa.String(500), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("data_entrada", sa.Date(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf", name="uq_alunos_cpf"),
    )
    op.create_index("ix_alunos_nome", "alunos", ["nome"])

    op.create_table(
        "responsavel_aluno",
        sa.Column("aluno_id", sa.Uuid(), nullable=False),
        sa.Column("responsavel_id", sa.Uuid(), nullable=False),
        sa.Column(
            "parentesco",
            sa.Enum(
                "PAI", "MAE", "AVO", "AVA", "TIO", "TIA",
                "IRMAO", "IRMA", "TUTOR", "OUTRO",
                name="parentesco",
            ),
            nullable=False,
        ),
        sa.Column(
            "responsavel_financeiro", sa.Boolean(),
            server_default=sa.text("false"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["aluno_id"], ["alunos.id"],
            name="fk_resp_aluno_aluno_id",
        ),
        sa.ForeignKeyConstraint(
            ["responsavel_id"], ["usuarios.id"],
            name="fk_resp_aluno_responsavel_id",
        ),
        sa.PrimaryKeyConstraint("aluno_id", "responsavel_id", name="pk_resp_aluno"),
    )
    op.create_index("ix_resp_aluno_aluno_id", "responsavel_aluno", ["aluno_id"])
    op.create_index("ix_resp_aluno_responsavel_id", "responsavel_aluno", ["responsavel_id"])


def downgrade() -> None:
    op.drop_table("responsavel_aluno")
    op.drop_table("alunos")
    op.execute("DROP TYPE IF EXISTS parentesco")
