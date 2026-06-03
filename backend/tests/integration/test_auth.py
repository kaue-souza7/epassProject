import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_refresh_token
from app.shared.enums import Perfil
from tests.factories import PASSWORD, create_sessao, create_usuario


@pytest.fixture
async def active_user(session: AsyncSession):
    return await create_usuario(session, email="active@test.com", perfil=Perfil.ADMIN)


@pytest.fixture
async def inactive_user(session: AsyncSession):
    return await create_usuario(
        session, email="inactive@test.com", perfil=Perfil.ADMIN, ativo=False,
    )


class TestLogin:
    async def test_valid_login(self, client: AsyncClient, active_user):
        response = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": PASSWORD,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_invalid_password(self, client: AsyncClient, active_user):
        response = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert response.json()["error"] == "invalid_credentials"

    async def test_invalid_email(self, client: AsyncClient):
        response = await client.post("/auth/login", json={
            "email": "unknown@test.com",
            "password": PASSWORD,
        })
        assert response.status_code == 401

    async def test_inactive_user(self, client: AsyncClient, inactive_user):
        response = await client.post("/auth/login", json={
            "email": "inactive@test.com",
            "password": PASSWORD,
        })
        assert response.status_code == 403


class TestRefresh:
    async def test_valid_refresh(self, client: AsyncClient, session: AsyncSession, active_user):
        login_resp = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": PASSWORD,
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_invalid_refresh_token(self, client: AsyncClient):
        response = await client.post("/auth/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert response.status_code == 401

    async def test_refresh_with_access_token(self, client: AsyncClient, active_user):
        login_resp = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": PASSWORD,
        })
        access_token = login_resp.json()["access_token"]

        response = await client.post("/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert response.status_code == 401

    async def test_refresh_revoked_session(self, client: AsyncClient, session: AsyncSession, active_user):
        token, jti = create_refresh_token(subject=str(active_user.id))
        await create_sessao(session, usuario_id=active_user.id, jti=jti, revoked=True)

        response = await client.post("/auth/refresh", json={
            "refresh_token": token,
        })
        assert response.status_code == 401


class TestLogout:
    async def test_valid_logout(self, client: AsyncClient, active_user):
        login_resp = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": PASSWORD,
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post("/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 204

    async def test_logout_invalid_token(self, client: AsyncClient):
        response = await client.post("/auth/logout", json={
            "refresh_token": "invalid.token.here",
        })
        assert response.status_code == 401

    async def test_logout_twice(self, client: AsyncClient, active_user):
        login_resp = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": PASSWORD,
        })
        refresh_token = login_resp.json()["refresh_token"]

        await client.post("/auth/logout", json={"refresh_token": refresh_token})
        response = await client.post("/auth/logout", json={"refresh_token": refresh_token})
        assert response.status_code == 401


class TestMe:
    async def test_auth_me_valid(self, client: AsyncClient, active_user):
        login_resp = await client.post("/auth/login", json={
            "email": "active@test.com",
            "password": PASSWORD,
        })
        access_token = login_resp.json()["access_token"]

        response = await client.get("/auth/me", headers={
            "Authorization": f"Bearer {access_token}",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "active@test.com"
        assert data["perfil"] == "admin"
        assert data["ativo"] is True
        assert uuid.UUID(data["id"])

    async def test_auth_me_no_token(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    async def test_auth_me_invalid_token(self, client: AsyncClient):
        response = await client.get("/auth/me", headers={
            "Authorization": "Bearer invalid.token.here",
        })
        assert response.status_code == 401
