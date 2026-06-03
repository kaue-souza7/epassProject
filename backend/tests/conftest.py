from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import Base, get_session

TEST_DATABASE_URL = "postgresql+asyncpg://epass:epass123@localhost:5433/epass_test"


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(setup_db) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
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
async def auth_client(client: AsyncClient, session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    import uuid as _uuid
    from app.shared.enums import Perfil
    from tests.factories import create_usuario, PASSWORD
    email = f"auth.{_uuid.uuid4().hex[:8]}@test.com"
    await create_usuario(session, email=email, perfil=Perfil.PROFESSOR)
    await session.commit()
    login_resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = login_resp.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    import uuid as _uuid
    from app.shared.enums import Perfil
    from tests.factories import create_usuario, PASSWORD
    email = f"admin.{_uuid.uuid4().hex[:8]}@test.com"
    await create_usuario(session, email=email, perfil=Perfil.ADMIN)
    await session.commit()
    login_resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = login_resp.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client
