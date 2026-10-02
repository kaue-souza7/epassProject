"""create grade horaria

horarios_aula — a agenda que responde "quem tem aula com este aluno hoje".

Índices:
    uq_horarios_turma_dia_hora   — uma aula por (turma, dia, hora de início) entre as ativas
    ix_horarios_turma_dia        — "a grade desta turma neste dia" (usado no aviso de ausência)
    ix_horarios_professor_dia    — "a agenda deste professor neste dia" (conflito)

O tipo `diasemana` NÃO é criado aqui: ele já existe desde a migration da programação
da cantina (f6a7b8c9d0e1), em maiúsculas ('SEG', 'TER', ...). Criar de novo falharia
com "type already exists", e recriá-lo apagaria as programações já cadastradas.

Escrita em SQL cru pelo mesmo motivo das tabelas anteriores do projeto: o
`sa.Enum(...)` do Alembic tentaria criar o tipo, e a diferença de caixa entre
`DiaSemana` (StrEnum minúsculo) e o valor gravado (maiúsculo) exigiria coerção manual
a cada leitura.

Revision ID: u1v2w3x4y5z6
Revises: t5u6v7w8x9y0
Create Date: 2026-06-02 09:00:00.000000
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, None] = "t5u6v7w8x9y0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS horarios_aula (
            id UUID PRIMARY KEY,
            turma_id UUID NOT NULL REFERENCES turmas(id),
            professor_id UUID NOT NULL REFERENCES professor_profiles(usuario_id),
            disciplina_id UUID REFERENCES disciplinas(id),
            dia_semana diasemana NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_horario_hora_fim CHECK (hora_fim > hora_inicio),
            CONSTRAINT ck_horario_hora_inicio_plausivel
                CHECK (hora_inicio >= '06:00' AND hora_inicio <= '22:00')
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_horarios_aula_turma_id ON horarios_aula (turma_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_horarios_aula_professor_id "
        "ON horarios_aula (professor_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_horarios_turma_dia "
        "ON horarios_aula (turma_id, dia_semana)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_horarios_professor_dia "
        "ON horarios_aula (professor_id, dia_semana)"
    )

    # Parcial sobre `ativo`: desativar uma janela libera o mesmo (turma, dia, hora)
    # para o professor substituto, que é a operação do dia a dia.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_horarios_turma_dia_hora
        ON horarios_aula (turma_id, dia_semana, hora_inicio)
        WHERE ativo
    """)


def downgrade() -> None:
    # O tipo `diasemana` NÃO é derrubado aqui: ele pertence à cantina.
    op.execute("DROP INDEX IF EXISTS uq_horarios_turma_dia_hora")
    op.execute("DROP INDEX IF EXISTS ix_horarios_professor_dia")
    op.execute("DROP INDEX IF EXISTS ix_horarios_turma_dia")
    op.execute("DROP INDEX IF EXISTS ix_horarios_aula_professor_id")
    op.execute("DROP INDEX IF EXISTS ix_horarios_aula_turma_id")
    op.execute("DROP TABLE IF EXISTS horarios_aula")
