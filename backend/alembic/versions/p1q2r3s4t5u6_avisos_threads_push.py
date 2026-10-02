"""avisos: destinatarios, threads e push

Fecha a lacuna histórica: as tabelas de comunicação (avisos, avisos_leituras,
notificacoes, ocorrencias, ocorrencias_historico) nunca tiveram migration e só
existiam via metadata.create_all nos testes. Esta revisão:

1. Cria as tabelas de comunicação quando ausentes (idempotente).
2. Evolui avisos_leituras -> avisos_destinatarios (destinatários genéricos,
   não só responsáveis) com `usuario_id` + contexto `aluno_id`.
3. Adiciona `avisos.permite_respostas`.
4. Cria `avisos_mensagens` (thread/conversa) e `push_tokens` (Expo push).

Nota de arquitetura: as colunas de enumeração deste módulo usam VARCHAR +
CHECK (native_enum=False nos models) em vez de enums nativos do PostgreSQL.
O DDL de enum nativo dentro do encadeamento de migrations se mostrou frágil
sob asyncpg (CREATE TABLE não enxergava o tipo recém-criado), e o CHECK
mantém a integridade no banco sem essa dependência.

Revision ID: p1q2r3s4t5u6
Revises: o3p4q5r6s7t8
Create Date: 2026-09-24
"""

from alembic import op

revision = "p1q2r3s4t5u6"
down_revision = "o3p4q5r6s7t8"
branch_labels = None
depends_on = None


_AVISO_STATUS = ("PUBLICADO", "ARQUIVADO")
_NOTIFICACAO_TIPOS = (
    "SISTEMA", "CANTINA", "BOLETIM", "OCORRENCIA", "AVISO",
    "AGENDA", "FINANCEIRO", "NOTA", "FREQUENCIA",
)
_OCORRENCIA_TIPOS = ("COMPORTAMENTO", "SAUDE", "ACADEMICO", "OUTRO")
_OCORRENCIA_SEVERIDADES = ("BAIXA", "MEDIA", "ALTA")
_OCORRENCIA_STATUS = ("ABERTA", "EM_ANDAMENTO", "RESOLVIDA", "ARQUIVADA")


def _check(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _criar_tabelas_legadas() -> None:
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS avisos (
            id UUID PRIMARY KEY,
            titulo VARCHAR(200) NOT NULL,
            mensagem TEXT NOT NULL,
            tipo VARCHAR(30) NOT NULL,
            prioridade VARCHAR(30) NOT NULL,
            destinatario_aluno_id UUID REFERENCES alunos(id),
            destinatario_turma_id UUID REFERENCES turmas(id),
            status VARCHAR(20) NOT NULL DEFAULT 'PUBLICADO'
                CHECK (status IN ({_check(_AVISO_STATUS)})),
            criado_por UUID NOT NULL REFERENCES usuarios(id),
            publicado_em TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_avisos_destinatario_aluno_id ON avisos (destinatario_aluno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_avisos_destinatario_turma_id ON avisos (destinatario_turma_id)")

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id UUID PRIMARY KEY,
            destinatario_id UUID NOT NULL REFERENCES usuarios(id),
            tipo VARCHAR(20) NOT NULL
                CHECK (tipo IN ({_check(_NOTIFICACAO_TIPOS)})),
            titulo VARCHAR(200) NOT NULL,
            mensagem TEXT NOT NULL,
            canal VARCHAR(30) NOT NULL DEFAULT 'inapp',
            entidade_tipo VARCHAR(50),
            entidade_id UUID,
            evento_key VARCHAR(255),
            dados JSON,
            lida BOOLEAN NOT NULL DEFAULT FALSE,
            lida_em TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notificacoes_destinatario_id ON notificacoes (destinatario_id)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notificacao_evento
        ON notificacoes (destinatario_id, evento_key)
        WHERE evento_key IS NOT NULL
    """)

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id UUID PRIMARY KEY,
            aluno_id UUID REFERENCES alunos(id),
            turma_id UUID REFERENCES turmas(id),
            titulo VARCHAR(200) NOT NULL,
            descricao TEXT NOT NULL,
            tipo VARCHAR(20) NOT NULL
                CHECK (tipo IN ({_check(_OCORRENCIA_TIPOS)})),
            severidade VARCHAR(10) NOT NULL
                CHECK (severidade IN ({_check(_OCORRENCIA_SEVERIDADES)})),
            status VARCHAR(20) NOT NULL DEFAULT 'ABERTA'
                CHECK (status IN ({_check(_OCORRENCIA_STATUS)})),
            criado_por UUID NOT NULL REFERENCES usuarios(id),
            responsavel_id UUID REFERENCES usuarios(id),
            resolvida_em TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ocorrencias_aluno_id ON ocorrencias (aluno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ocorrencias_turma_id ON ocorrencias (turma_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ocorrencias_responsavel_id ON ocorrencias (responsavel_id)")

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS ocorrencias_historico (
            id UUID PRIMARY KEY,
            ocorrencia_id UUID NOT NULL REFERENCES ocorrencias(id) ON DELETE CASCADE,
            status_anterior VARCHAR(20)
                CHECK (status_anterior IS NULL OR status_anterior IN ({_check(_OCORRENCIA_STATUS)})),
            status_novo VARCHAR(20)
                CHECK (status_novo IS NULL OR status_novo IN ({_check(_OCORRENCIA_STATUS)})),
            acao VARCHAR(255) NOT NULL,
            autor_id UUID REFERENCES usuarios(id),
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ocorrencias_historico_ocorrencia_id "
        "ON ocorrencias_historico (ocorrencia_id)"
    )


def _converter_enums_nativos() -> None:
    """Converte colunas que já existam como enum nativo para VARCHAR.

    Necessário para bancos de desenvolvimento onde as tabelas foram criadas
    via metadata.create_all (enums nativos) antes desta migration.
    """
    conversoes = [
        ("ocorrencias", "tipo", 20),
        ("ocorrencias", "severidade", 10),
        ("ocorrencias", "status", 20),
        ("ocorrencias_historico", "status_anterior", 20),
        ("ocorrencias_historico", "status_novo", 20),
        ("avisos", "status", 20),
        ("notificacoes", "tipo", 20),
    ]
    for tabela, coluna, tamanho in conversoes:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns c
                    JOIN pg_type t ON t.typname = c.udt_name
                    WHERE c.table_schema = 'public'
                      AND c.table_name = '{tabela}'
                      AND c.column_name = '{coluna}'
                      AND t.typtype = 'e'
                ) THEN
                    EXECUTE 'ALTER TABLE {tabela} ALTER COLUMN {coluna} TYPE VARCHAR({tamanho}) '
                         || 'USING {coluna}::text';
                END IF;
            END
            $$;
        """)


def _migrar_leituras_para_destinatarios() -> None:
    """Renomeia avisos_leituras -> avisos_destinatarios quando existir.

    Em bancos novos a tabela é criada diretamente com o schema novo.
    """
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='avisos_leituras'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='avisos_destinatarios'
            ) THEN
                ALTER TABLE avisos_leituras RENAME TO avisos_destinatarios;
            END IF;
        END
        $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='avisos_destinatarios'
                  AND column_name='responsavel_id'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='avisos_destinatarios'
                  AND column_name='usuario_id'
            ) THEN
                ALTER TABLE avisos_destinatarios RENAME COLUMN responsavel_id TO usuario_id;
            END IF;
        END
        $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS avisos_destinatarios (
            id UUID PRIMARY KEY,
            aviso_id UUID NOT NULL REFERENCES avisos(id) ON DELETE CASCADE,
            usuario_id UUID NOT NULL REFERENCES usuarios(id),
            aluno_id UUID REFERENCES alunos(id),
            lido_em TIMESTAMPTZ,
            escalado_em TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)

    op.execute(
        "ALTER TABLE avisos_destinatarios ADD COLUMN IF NOT EXISTS aluno_id UUID REFERENCES alunos(id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_destinatarios_aviso_id "
        "ON avisos_destinatarios (aviso_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_destinatarios_usuario_id "
        "ON avisos_destinatarios (usuario_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_destinatarios_aluno_id "
        "ON avisos_destinatarios (aluno_id)"
    )
    op.execute("DROP INDEX IF EXISTS uq_aviso_leitura")
    op.execute("DROP INDEX IF EXISTS uq_aviso_destinatario")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_aviso_destinatario
        ON avisos_destinatarios (aviso_id, usuario_id)
    """)


def _criar_tabela_mensagens() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS avisos_mensagens (
            id UUID PRIMARY KEY,
            aviso_id UUID NOT NULL REFERENCES avisos(id) ON DELETE CASCADE,
            autor_id UUID NOT NULL REFERENCES usuarios(id),
            destinatario_id UUID NOT NULL REFERENCES usuarios(id),
            conteudo TEXT NOT NULL,
            lida_em TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_mensagens_aviso_id ON avisos_mensagens (aviso_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_mensagens_autor_id ON avisos_mensagens (autor_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_mensagens_destinatario_id "
        "ON avisos_mensagens (destinatario_id)"
    )


def _criar_tabela_push_tokens() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS push_tokens (
            id UUID PRIMARY KEY,
            usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            token VARCHAR(255) NOT NULL UNIQUE,
            plataforma VARCHAR(20) NOT NULL DEFAULT 'expo',
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_push_tokens_usuario_id ON push_tokens (usuario_id)"
    )


def _backfill_destinatarios() -> None:
    """Materializa destinatários para avisos legados sem registros."""
    op.execute("""
        INSERT INTO avisos_destinatarios (id, aviso_id, usuario_id, aluno_id, created_at)
        SELECT gen_random_uuid(), a.id, ra.responsavel_id, a.destinatario_aluno_id, NOW()
        FROM avisos a
        JOIN responsavel_aluno ra ON ra.aluno_id = a.destinatario_aluno_id
        WHERE a.destinatario_aluno_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM avisos_destinatarios d WHERE d.aviso_id = a.id)
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO avisos_destinatarios (id, aviso_id, usuario_id, aluno_id, created_at)
        SELECT gen_random_uuid(), a.id, ra.responsavel_id, ra.aluno_id, NOW()
        FROM avisos a
        JOIN matriculas m ON m.turma_id = a.destinatario_turma_id
        JOIN responsavel_aluno ra ON ra.aluno_id = m.aluno_id
        WHERE a.destinatario_turma_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM avisos_destinatarios d WHERE d.aviso_id = a.id)
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO avisos_destinatarios (id, aviso_id, usuario_id, aluno_id, created_at)
        SELECT gen_random_uuid(), a.id, ra.responsavel_id, ra.aluno_id, NOW()
        FROM avisos a
        JOIN responsavel_aluno ra ON TRUE
        WHERE a.destinatario_aluno_id IS NULL
          AND a.destinatario_turma_id IS NULL
          AND NOT EXISTS (SELECT 1 FROM avisos_destinatarios d WHERE d.aviso_id = a.id)
        ON CONFLICT DO NOTHING
    """)


def upgrade() -> None:
    _converter_enums_nativos()
    _criar_tabelas_legadas()
    _migrar_leituras_para_destinatarios()
    _criar_tabela_mensagens()
    _criar_tabela_push_tokens()

    op.execute(
        "ALTER TABLE avisos ADD COLUMN IF NOT EXISTS permite_respostas "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )

    _backfill_destinatarios()


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS push_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS avisos_mensagens CASCADE")
    op.execute("ALTER TABLE avisos DROP COLUMN IF EXISTS permite_respostas")

    op.execute("DROP INDEX IF EXISTS uq_aviso_destinatario")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='avisos_destinatarios'
            ) THEN
                ALTER TABLE avisos_destinatarios RENAME TO avisos_leituras;
                ALTER TABLE avisos_leituras RENAME COLUMN usuario_id TO responsavel_id;
                ALTER TABLE avisos_leituras DROP COLUMN IF EXISTS aluno_id;
                DROP INDEX IF EXISTS ix_avisos_destinatarios_aviso_id;
                DROP INDEX IF EXISTS ix_avisos_destinatarios_usuario_id;
                DROP INDEX IF EXISTS ix_avisos_destinatarios_aluno_id;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_aviso_leitura
                ON avisos_leituras (aviso_id, responsavel_id);
            END IF;
        END
        $$;
    """)

    op.execute("DROP TABLE IF EXISTS ocorrencias_historico CASCADE")
    op.execute("DROP TABLE IF EXISTS ocorrencias CASCADE")
    op.execute("DROP TABLE IF EXISTS notificacoes CASCADE")
    op.execute("DROP TABLE IF EXISTS avisos CASCADE")
