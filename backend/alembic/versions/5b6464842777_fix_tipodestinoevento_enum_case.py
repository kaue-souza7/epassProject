"""fix tipodestinoevento enum case to match SAEnum .name convention

Migration 3a4b5c6d7e8f created the enum tipodestinoevento with lowercase
values ('professor', 'responsavel', 'turma'), but SQLAlchemy's SAEnum
always uses .name (uppercase: 'PROFESSOR', 'RESPONSAVEL', 'TURMA').

This caused HTTP 500 on GET /api/v1/agenda/events for RESPONSAVEL and
PROFESSOR profiles due to:
  invalid input value for enum tipodestinoevento: "PROFESSOR"

All other enums in the project use uppercase values matching SAEnum
.name convention. This migration renames them to align.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "5b6464842777"
down_revision: Union[str, None] = "4a5b6c7d8e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE tipodestinoevento RENAME VALUE 'professor' TO 'PROFESSOR'")
    op.execute("ALTER TYPE tipodestinoevento RENAME VALUE 'responsavel' TO 'RESPONSAVEL'")
    op.execute("ALTER TYPE tipodestinoevento RENAME VALUE 'turma' TO 'TURMA'")


def downgrade() -> None:
    op.execute("ALTER TYPE tipodestinoevento RENAME VALUE 'TURMA' TO 'turma'")
    op.execute("ALTER TYPE tipodestinoevento RENAME VALUE 'RESPONSAVEL' TO 'responsavel'")
    op.execute("ALTER TYPE tipodestinoevento RENAME VALUE 'PROFESSOR' TO 'professor'")
