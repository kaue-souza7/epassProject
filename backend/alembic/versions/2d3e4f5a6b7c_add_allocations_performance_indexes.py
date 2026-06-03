"""add allocations performance indexes

ix_alocacoes_data_inicio       — suporta ORDER BY data_inicio DESC
ix_alocacoes_professor_data    — suporta WHERE professor_id + ORDER BY data_inicio DESC
ix_alocacoes_turma_data        — suporta WHERE turma_id + ORDER BY data_inicio DESC

Revision ID: 2d3e4f5a6b7c
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-31 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "2d3e4f5a6b7c"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_alocacoes_data_inicio", "alocacoes", ["data_inicio"])
    op.create_index("ix_alocacoes_professor_data", "alocacoes", ["professor_id", "data_inicio"])
    op.create_index("ix_alocacoes_turma_data", "alocacoes", ["turma_id", "data_inicio"])


def downgrade() -> None:
    op.drop_index("ix_alocacoes_turma_data", table_name="alocacoes")
    op.drop_index("ix_alocacoes_professor_data", table_name="alocacoes")
    op.drop_index("ix_alocacoes_data_inicio", table_name="alocacoes")
