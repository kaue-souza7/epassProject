"""add_cantineiro_to_perfil_enum

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE perfil ADD VALUE 'CANTINEIRO'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # To downgrade, recreate the enum without CANTINEIRO.
    op.execute("ALTER TABLE usuarios ALTER COLUMN perfil TYPE VARCHAR(20)")
    op.execute("DROP TYPE IF EXISTS perfil")
    op.execute("""
        CREATE TYPE perfil AS ENUM ('ADMIN', 'SECRETARIA', 'PROFESSOR', 'RESPONSAVEL')
    """)
    op.execute("""
        ALTER TABLE usuarios ALTER COLUMN perfil
        TYPE perfil USING UPPER(perfil::text)::perfil
    """)
