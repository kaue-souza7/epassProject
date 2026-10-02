"""solicitacoes_documento: pedidos de documentos feitos pelo responsável

Permite que o responsável peça documentos à secretaria (boletim, histórico,
declaração, comprovantes) e acompanhe o andamento de cada pedido. A
autorização é sempre pelo responsável logado: `responsavel_id` vem do token e
o serviço valida que `aluno_id` pertence a ele, o que impede um responsável de
solicitar documentos de um aluno que não é seu filho.

Os labels dos enums são os NOMES dos membros do StrEnum em maiúsculas — é o que
o SQLAlchemy grava por padrão em todo o projeto.

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-09-28
"""

from alembic import op

revision = "s4t5u6v7w8x9"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE tipodocumento AS ENUM ("
        "'BOLETIM_BIMESTRAL', 'BOLETIM_ANUAL', 'HISTORICO_ESCOLAR', "
        "'DECLARACAO_MATRICULA', 'COMPROVANTE_MATRICULA', "
        "'COMPROVANTE_FREQUENCIA', 'COMPROVANTE_ENDERECO', "
        "'COMPROVANTE_RENDA', 'OUTRO'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE statussolicitacaodocumento AS ENUM ("
        "'PENDENTE', 'EM_ANALISE', 'CONCLUIDA', 'RECUSADA', 'CANCELADA'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_documento (
            id UUID PRIMARY KEY,
            responsavel_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
            tipo tipodocumento NOT NULL,
            status statussolicitacaodocumento NOT NULL DEFAULT 'PENDENTE',
            observacoes TEXT,
            resposta TEXT,
            documento_url VARCHAR(500),
            atendido_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
            atendido_em TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_solicitacao_documento_observacoes
                CHECK (observacoes IS NULL OR char_length(observacoes) <= 1000)
        )
    """)

    # Índice do caminho comum: "minhas solicitações", em ordem recente.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_solicitacoes_documento_responsavel "
        "ON solicitacoes_documento (responsavel_id, created_at DESC)"
    )
    # Fila de trabalho da secretaria.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_solicitacoes_documento_status "
        "ON solicitacoes_documento (status, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS solicitacoes_documento CASCADE")
    op.execute("DROP TYPE IF EXISTS statussolicitacaodocumento")
    op.execute("DROP TYPE IF EXISTS tipodocumento")
