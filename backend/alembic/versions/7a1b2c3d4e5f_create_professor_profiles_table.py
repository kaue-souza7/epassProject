"""create professor_profiles table

Revision ID: 7a1b2c3d4e5f
Revises: 6f0a2c8d3e51
Create Date: 2026-05-30 04:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, None] = "6f0a2c8d3e51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "professor_profiles",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("formacao_principal", sa.String(200), nullable=True),
        sa.Column("matricula_funcional", sa.String(50), nullable=True),
        sa.Column("data_contratacao", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("usuario_id", name="pk_professor_profiles"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuarios.id"],
            name="fk_professor_profile_usuario_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "matricula_funcional", name="uq_professor_profiles_matricula",
        ),
    )


def downgrade() -> None:
    op.drop_table("professor_profiles")
