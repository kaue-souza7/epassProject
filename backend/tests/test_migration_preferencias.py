"""A migration de preferências tem que produzir o mesmo schema do modelo.

Sem banco, sem API: compara o DDL que o SQLAlchemy gera para
`PreferenciaNotificacao` com o SQL que a migration executa.

Motivo do teste: `SAEnum(TipoNotificacao)` grava o **nome** do enum
(`"AVISO"`), não o valor (`"aviso"`). Uma migration escrita com valores
minúsculos cria um CHECK que rejeita todo INSERT feito pelo ORM — o app
funciona em `create_all` (testes) e quebra em produção, e só aparece no
primeiro POST. Aqui a divergência é detectada sem precisar do banco.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

# Importar `app.main` carrega todos os modelos, sem o qual o DDL sai incompleto.
from app.main import app as _app  # noqa: F401
from app.modules.communication.models import PreferenciaNotificacao
from app.shared.enums import TipoNotificacao

MIGRATION = (
    pathlib.Path(__file__).resolve().parents[1]
    / "alembic" / "versions"
    / "t5u6v7w8x9y0_preferencias_notificacao_email.py"
)


def _ddl_do_modelo() -> str:
    d = postgresql.dialect()
    partes = [str(CreateTable(PreferenciaNotificacao.__table__).compile(dialect=d))]
    for ix in sorted(PreferenciaNotificacao.__table__.indexes, key=lambda i: i.name or ""):
        partes.append(str(CreateIndex(ix).compile(dialect=d)))
    return "\n".join(partes)


def _sql_da_migration() -> str:
    spec = importlib.util.spec_from_file_location("mig_preferencias", MIGRATION)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    fonte = MIGRATION.read_text(encoding="utf-8")
    corpo = fonte.split("def upgrade", 1)[1].split("def downgrade", 1)[0]
    return "\n".join(re.findall(r'op\.execute\(\s*"""(.*?)"""', corpo, re.S)) + "\n" + "\n".join(
        re.findall(r'op\.execute\(\s*\n?\s*"((?:[^"\\]|\\.)*)"', corpo)
    )


def test_migration_existe_e_tem_down_revision():
    assert MIGRATION.exists(), f"migration ausente: {MIGRATION}"
    spec = importlib.util.spec_from_file_location("mig_preferencias", MIGRATION)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert modulo.down_revision == "s4t5u6v7w8x9"


def test_check_constraint_usa_os_nomes_do_enum():
    """O CHECK precisa aceitar exatamente o que o ORM grava."""
    modelo = _ddl_do_modelo()
    migration = _sql_da_migration()

    esperado = re.search(r"CHECK \(tipo IN \((.*?)\)\)", modelo, re.S)
    assert esperado, "CHECK do modelo não encontrado"
    nomes_modelo = set(re.findall(r"'([A-Z_]+)'", esperado.group(1)))

    na_migration = re.search(r"CHECK \(tipo IN \((.*?)\)\)", migration, re.S)
    assert na_migration, "CHECK da migration não encontrado"
    nomes_migration = set(re.findall(r"'([A-Z_]+)'", na_migration.group(1)))

    assert nomes_migration == nomes_modelo, (
        f"migration e modelo divergem no CHECK: {nomes_migration ^ nomes_modelo}"
    )
    # Nomes, não valores: `Enum` do SQLAlchemy persiste `.name`.
    assert nomes_modelo == {t.name for t in TipoNotificacao}


def test_nomes_do_enum_sao_aceitos_pelo_check():
    migration = _sql_da_migration()
    na_migration = re.search(r"CHECK \(tipo IN \((.*?)\)\)", migration, re.S)
    assert na_migration
    nomes = set(re.findall(r"'([A-Z_]+)'", na_migration.group(1)))
    for tipo in TipoNotificacao:
        assert tipo.name in nomes, f"{tipo.name} rejeitado pelo CHECK da migration"
        assert tipo.name.upper() in nomes


def test_migration_cria_unique_e_fk_com_o_mesmo_nome_do_modelo():
    modelo = _ddl_do_modelo()
    migration = _sql_da_migration()
    for pedaco in (
        "uq_preferencia_notificacao_tipo",
        "UNIQUE (usuario_id, tipo)",
        "ck_preferencias_notificacoes_tipo",
    ):
        assert pedaco in modelo, f"modelo perdeu {pedaco}"
        assert pedaco in migration, f"migration perdeu {pedaco}"

    assert "ON DELETE CASCADE" in modelo
    assert "ON DELETE CASCADE" in migration
    assert "ix_preferencias_notificacoes_usuario_id" in modelo
    assert "ix_preferencias_notificacoes_usuario_id" in migration


def test_migration_e_idempotente():
    migration = _sql_da_migration()
    assert migration.count("IF NOT EXISTS") == 2, migration
    assert "DEFAULT FALSE" in migration.upper()
