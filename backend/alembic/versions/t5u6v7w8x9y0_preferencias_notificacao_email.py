"""preferencias_notificacoes: opt-in de envio de avisos/ocorrências por e-mail

Uma linha por (usuário, tipo). `email` nasce `false`: o responsável precisa
ligar o canal explicitamente, e a ausência da linha equivale a desligado —
assim nenhum usuário passa a receber e-mail fora da escola só por existir.

O `NotificationDispatcher` consulta esta tabela ao despachar e encaminha para o
`EmailChannel` apenas quando o opt-in está ativo, sem alterar o comportamento
de inapp/push.

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-09-28
"""

from alembic import op


revision = "t5u6v7w8x9y0"
down_revision = "s4t5u6v7w8x9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Os valores do CHECK são os NOMES do enum (`TipoNotificacao`), em maiúsculas,
    # e é isso que o SQLAlchemy grava: `Enum` com enum Python persiste `.name`,
    # não `.value`. As tabelas irmãs (`notificacoes`) seguem a mesma convenção.
    # Com valores minúsculos aqui, qualquer INSERT falharia no CHECK.
    op.execute("""
        CREATE TABLE IF NOT EXISTS preferencias_notificacoes (
            id UUID PRIMARY KEY,
            usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            tipo VARCHAR(20) NOT NULL,
            email BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_preferencia_notificacao_tipo
                UNIQUE (usuario_id, tipo),
            CONSTRAINT ck_preferencias_notificacoes_tipo
                CHECK (tipo IN ('SISTEMA', 'CANTINA', 'BOLETIM', 'OCORRENCIA',
                                'AVISO', 'AGENDA', 'FINANCEIRO', 'NOTA',
                                'FREQUENCIA'))
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_preferencias_notificacoes_usuario_id "
        "ON preferencias_notificacoes (usuario_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS preferencias_notificacoes CASCADE")
