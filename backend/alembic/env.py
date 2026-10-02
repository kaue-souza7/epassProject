import asyncio
import os
import sys
from logging.config import fileConfig

# alembic muda o CWD para alembic/, entao precisamos adicionar a raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base
# TODO: centralizar registry de models quando novos modulos forem implementados.
from app.modules.users.models import Usuario        # noqa: F401
from app.modules.auth.models import Sessao          # noqa: F401
from app.modules.academic_years.models import AnoLetivo  # noqa: F401
from app.modules.students.models import Aluno, ResponsavelAluno  # noqa: F401
from app.modules.series.models import Serie  # noqa: F401
from app.modules.classes.models import Turma  # noqa: F401
from app.modules.enrollments.models import Matricula  # noqa: F401
from app.modules.subjects.models import Disciplina  # noqa: F401
from app.modules.teachers.models import ProfessorProfile  # noqa: F401
from app.modules.allocations.models import Alocacao  # noqa: F401
from app.modules.attendance.models import Chamada, Frequencia  # noqa: F401
from app.modules.assessment.models import Avaliacao, Nota  # noqa: F401
from app.modules.academic_config.models import ConfiguracaoAcademica  # noqa: F401
from app.modules.agenda.models import Evento, EventoDestinatario  # noqa: F401
from app.modules.financial.models import Wallet, Movimentacao  # noqa: F401
from app.modules.bracelets.models import Bracelet  # noqa: F401
from app.modules.cantina.models import Produto, Pedido, ItemPedido, MovimentacaoEstoque, CantinaConfig  # noqa: F401
from app.modules.cantina.programacao_models import ProgramacaoCantina, ProgramacaoItem  # noqa: F401
from app.modules.ai.history_models import Conversa, Mensagem  # noqa: F401
from app.modules.communication.models import (  # noqa: F401
    Aviso,
    AvisoDestinatario,
    AvisoMensagem,
    Notificacao,
    Ocorrencia,
    OcorrenciaHistorico,
    PushTicket,
    PushToken,
)


config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
