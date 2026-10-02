"""avisos: tipar prioridade e tipo como enum + indices de listagem

`avisos.prioridade` e `avisos.tipo` eram VARCHAR(30) livres, sem nenhuma restrição no
banco: qualquer string passava, e o front desenhava um badge "undefined" quando o valor
não estava no seu dicionário. As enums `PrioridadeAviso` e `TipoAviso` existiam em
`shared/enums.py` desde o começo e nunca foram usadas aqui.

Este módulo usa VARCHAR + CHECK em MAIÚSCULAS (convenção `.name` do SAEnum), o mesmo
dos enums vizinhos `ck_avisos_status` e `ck_ocorrencias_tipo`. Por isso a normalização
vem ANTES da constraint: o front grava "media"/"geral" em minúsculas e o banco passa a
guardar "MEDIA"/"GERAL".

Valores fora do domínio viram o padrão ('MEDIA' / 'GERAL') em vez de a migration
falhar: um aviso legado não pode impedir o deploy do resto.

`tipo` ganha 'AUSENCIA', o tipo do aviso gerado pelo botão "não vir hoje" do
responsável. Ele é tipo próprio porque tem regra de destinatário diferente dos
demais: secretaria + professores da turma no dia, e não o público escolhido no
compositor.

Índices novos, todos a serviço da tela de avisos:
    ix_avisos_publicado_em      — ordenação padrão (recentes) e filtro por período
    ix_avisos_prioridade        — filtro por severidade e ordenação por prioridade
    ix_avisos_tipo              — filtro por tipo
    ix_avisos_status_publicado  — "publicados" é a caixa padrão de todo mundo

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-06-02 10:30:00.000000
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PRIORIDADES = ("BAIXA", "MEDIA", "ALTA")
_TIPOS = ("GERAL", "COMPORTAMENTO", "SAUDE", "ADMINISTRATIVO", "AUSENCIA")


def _in(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    # 1) Normaliza para maiúsculas, com o que está fora do domínio caindo no padrão.
    op.execute(f"""
        UPDATE avisos
        SET prioridade = 'MEDIA'
        WHERE prioridade IS NOT NULL AND UPPER(prioridade) NOT IN ({_in(_PRIORIDADES)})
    """)
    op.execute(
        "UPDATE avisos SET prioridade = UPPER(prioridade) WHERE prioridade IS NOT NULL"
    )
    op.execute(f"""
        UPDATE avisos
        SET tipo = 'GERAL'
        WHERE tipo IS NOT NULL AND UPPER(tipo) NOT IN ({_in(_TIPOS)})
    """)
    op.execute("UPDATE avisos SET tipo = UPPER(tipo) WHERE tipo IS NOT NULL")

    # 2) Agora sim, o domínio é garantido pelo banco.
    op.execute("ALTER TABLE avisos DROP CONSTRAINT IF EXISTS ck_avisos_prioridade")
    op.execute("ALTER TABLE avisos DROP CONSTRAINT IF EXISTS ck_avisos_tipo")
    op.execute(
        f"ALTER TABLE avisos ADD CONSTRAINT ck_avisos_prioridade "
        f"CHECK (prioridade IN ({_in(_PRIORIDADES)}))"
    )
    op.execute(
        f"ALTER TABLE avisos ADD CONSTRAINT ck_avisos_tipo "
        f"CHECK (tipo IN ({_in(_TIPOS)}))"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_publicado_em ON avisos (publicado_em DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_avisos_prioridade ON avisos (prioridade)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_avisos_tipo ON avisos (tipo)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_avisos_status_publicado "
        "ON avisos (status, publicado_em DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_avisos_status_publicado")
    op.execute("DROP INDEX IF EXISTS ix_avisos_tipo")
    op.execute("DROP INDEX IF EXISTS ix_avisos_prioridade")
    op.execute("DROP INDEX IF EXISTS ix_avisos_publicado_em")
    op.execute("ALTER TABLE avisos DROP CONSTRAINT IF EXISTS ck_avisos_tipo")
    op.execute("ALTER TABLE avisos DROP CONSTRAINT IF EXISTS ck_avisos_prioridade")
    op.execute("UPDATE avisos SET prioridade = LOWER(prioridade)")
    op.execute("UPDATE avisos SET tipo = LOWER(tipo)")
