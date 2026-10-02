"""ai_conversas + ai_mensagens: histórico da Atena (Fase 5)

O histórico serve para dar continuidade ("e a nota de Matemática?"). Ele NUNCA
participa da autorização: toda consulta de escopo continua filtrando por
`usuario_id` vindo do token. Guardar isto é o que evita que o histórico vire
uma via de IDOR — um histórico roubado injeta texto no prompt, não acesso ao
banco.

A exclusão de `ai_conversas` cascateia em `ai_mensagens`, então apagar a
conversa não deixa resíduo do conteúdo.

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-09-25
"""

from alembic import op

revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Os labels são os NOMES dos membros do StrEnum, em maiúsculas — é o que o
    # SQLAlchemy grava por padrão em todo o projeto (veja `perfil`,
    # `statuspulseira`, `tipomovimentacao`). Criar em minúsculas faria todo
    # INSERT falhar com "invalid input value for enum".
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE papel_mensagem_ia AS ENUM ('USUARIO', 'ASSISTENTE'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_conversas (
            id UUID PRIMARY KEY,
            usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            titulo VARCHAR(200),
            criada_em TIMESTAMPTZ NOT NULL,
            atualizada_em TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_ai_conversas_titulo CHECK (char_length(titulo) <= 200)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_conversas_usuario_id "
        "ON ai_conversas (usuario_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_conversas_usuario_atualizada "
        "ON ai_conversas (usuario_id, atualizada_em)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_mensagens (
            id UUID PRIMARY KEY,
            conversa_id UUID NOT NULL
                REFERENCES ai_conversas(id) ON DELETE CASCADE,
            papel papel_mensagem_ia NOT NULL,
            conteudo TEXT NOT NULL,
            intencao VARCHAR(60),
            codigo VARCHAR(60),
            criado_em TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_ai_mensagens_conteudo
                CHECK (char_length(conteudo) BETWEEN 1 AND 8000)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_mensagens_conversa_id "
        "ON ai_mensagens (conversa_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_mensagens_conversa_criada "
        "ON ai_mensagens (conversa_id, criado_em)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_mensagens CASCADE")
    op.execute("DROP TABLE IF EXISTS ai_conversas CASCADE")
    op.execute("DROP TYPE IF EXISTS papel_mensagem_ia")
