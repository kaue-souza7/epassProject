"""add performance indexes

ix_usuarios_nome        — GET /teachers (ILIKE on Usuario.nome)
ix_matriculas_data_matricula — GET /enrollments (ORDER BY data_matricula DESC)
ix_alunos_ativo         — GET /students (?only_active=true)

Revision ID: 1a2b3c4d5e6f
Revises: f1e2d3c4b5a6
Create Date: 2026-05-31 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_usuarios_nome", "usuarios", ["nome"])
    op.create_index("ix_matriculas_data_matricula", "matriculas", ["data_matricula"])
    op.create_index("ix_alunos_ativo", "alunos", ["ativo"])


def downgrade() -> None:
    op.drop_index("ix_alunos_ativo", table_name="alunos")
    op.drop_index("ix_matriculas_data_matricula", table_name="matriculas")
    op.drop_index("ix_usuarios_nome", table_name="usuarios")
