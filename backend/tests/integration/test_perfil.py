import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.enums import Perfil
from tests.factories import PASSWORD, create_usuario


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return resp.json()["access_token"]


@pytest.fixture
async def responsavel(session: AsyncSession):
    return await create_usuario(
        session, nome="Maria Resp", email="maria@test.com", perfil=Perfil.RESPONSAVEL,
    )


class TestAtualizarPerfil:
    async def test_atualiza_nome(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"nome": "Maria Silva Responsavel"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["nome"] == "Maria Silva Responsavel"

        # A alteração precisa estar persistida, não só no retorno.
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["nome"] == "Maria Silva Responsavel"

    async def test_atualiza_email(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"email": "maria.nova@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "maria.nova@test.com"

    async def test_email_normalizado(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"email": "  MARIA.NOVA@Test.COM  "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "maria.nova@test.com"

    async def test_email_invalido(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"email": "nao-e-email"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_email_ja_em_uso(
        self, client: AsyncClient, session: AsyncSession, responsavel,
    ):
        await create_usuario(session, email="ocupado@test.com", perfil=Perfil.ADMIN)
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"email": "ocupado@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409

    async def test_nome_curto_demais(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"nome": "Ab"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_espacos_sao_removidos(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"nome": "  Carlos Carlos  "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["nome"] == "Carlos Carlos"

    async def test_sem_token(self, client: AsyncClient):
        response = await client.patch("/auth/me", json={"nome": "X"})
        assert response.status_code == 401

    async def test_nao_altera_perfil_nem_ativo(
        self, client: AsyncClient, responsavel,
    ):
        token = await _login(client, "maria@test.com")
        response = await client.patch(
            "/auth/me",
            json={"nome": "Maria Nova", "perfil": "admin", "ativo": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["perfil"] == "responsavel"
        assert response.json()["ativo"] is True


class TestTrocarSenha:
    async def test_troca_senha_com_sucesso(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/auth/me/senha",
            json={"senha_atual": PASSWORD, "nova_senha": "novasenha123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # A senha antiga não vale mais; a nova, sim.
        antigo = await client.post(
            "/auth/login", json={"email": "maria@test.com", "password": PASSWORD},
        )
        assert antigo.status_code == 401

        novo = await client.post(
            "/auth/login", json={"email": "maria@test.com", "password": "novasenha123"},
        )
        assert novo.status_code == 200

    async def test_senha_atual_incorreta(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/auth/me/senha",
            json={"senha_atual": "errada123", "nova_senha": "novasenha123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_nova_senha_curta(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/auth/me/senha",
            json={"senha_atual": PASSWORD, "nova_senha": "abc"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_nova_senha_igual_a_atual(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/auth/me/senha",
            json={"senha_atual": PASSWORD, "nova_senha": PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_troca_revoga_sessoes_anteriores(
        self, client: AsyncClient, responsavel,
    ):
        login = await client.post(
            "/auth/login", json={"email": "maria@test.com", "password": PASSWORD},
        )
        refresh_antigo = login.json()["refresh_token"]
        token = login.json()["access_token"]

        await client.post(
            "/auth/me/senha",
            json={"senha_atual": PASSWORD, "nova_senha": "novasenha123"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # O refresh emitido antes da troca não pode renovar a sessão.
        response = await client.post("/auth/refresh", json={"refresh_token": refresh_antigo})
        assert response.status_code == 401

    async def test_sem_token(self, client: AsyncClient):
        response = await client.post(
            "/auth/me/senha", json={"senha_atual": PASSWORD, "nova_senha": "novasenha123"},
        )
        assert response.status_code == 401
