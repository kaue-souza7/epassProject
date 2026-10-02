import asyncio
import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://epass:epass123@localhost:5433/epass_test",
)

app.state.limiter.enabled = False


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Reset completo do schema: remove tabelas e tipos (enums) residuais.
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def _limpar_tabelas(session: AsyncSession) -> None:
    """Trunca todas as tabelas, tolerando contenção de lock.

    `TRUNCATE ... CASCADE` pede ACCESS EXCLUSIVE em ~40 tabelas numa única
    instrução. Em arquivo de teste longo, o TRUNCATE do teste N pode cruzar com
    o primeiro comando do teste N+1, e o PostgreSQL reporta `deadlock detected`
    — erro que NÃO indica falha do teste e que, sem este retry, aparece
    esporadicamente como "erro no teardown" de um teste que passou.

    Repetir é seguro: TRUNCATE é idempotente e, se já rodou, repetir não muda
    nada. O rollback da transação antes do retry é obrigatório para liberar os
    locks que a tentativa falhada segurou.
    """
    tabelas = ", ".join(f"public.{t}" for t in Base.metadata.tables)
    comando = text(f"TRUNCATE TABLE {tabelas} CASCADE")

    for tentativa in range(4):
        try:
            await session.execute(comando)
            await session.commit()
            return
        except (OperationalError, DBAPIError):
            await session.rollback()
            if tentativa == 3:
                raise
            await asyncio.sleep(0.2 * (tentativa + 1))


@pytest_asyncio.fixture
async def session(setup_db) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        # Isolamento: limpa dados comprometidos ao final do teste (na mesma conexão,
        # evitando deadlock com o reset de schema do próximo teste).
        await session.rollback()
        await _limpar_tabelas(session)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient, session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    import uuid as _uuid

    from app.shared.enums import Perfil
    from tests.factories import PASSWORD, create_usuario
    email = f"auth.{_uuid.uuid4().hex[:8]}@test.com"
    await create_usuario(session, email=email, perfil=Perfil.PROFESSOR)
    await session.commit()
    login_resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = login_resp.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient, session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    import uuid as _uuid

    from app.shared.enums import Perfil
    from tests.factories import PASSWORD, create_usuario
    email = f"admin.{_uuid.uuid4().hex[:8]}@test.com"
    await create_usuario(session, email=email, perfil=Perfil.ADMIN)
    await session.commit()
    login_resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = login_resp.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client
