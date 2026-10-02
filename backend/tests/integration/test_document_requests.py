import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.enums import Perfil
from tests.factories import (
    PASSWORD,
    create_aluno,
    create_responsavel_aluno,
    create_usuario,
)


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return resp.json()["access_token"]


@pytest.fixture
async def responsavel(session: AsyncSession):
    user = await create_usuario(
        session, nome="Maria Resp", email="maria@test.com", perfil=Perfil.RESPONSAVEL,
    )
    aluno = await create_aluno(session, nome="João Aluno")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=user.id)
    return user, aluno


@pytest.fixture
async def outro_responsavel(session: AsyncSession):
    user = await create_usuario(
        session, nome="Pedro Outro", email="pedro@test.com", perfil=Perfil.RESPONSAVEL,
    )
    return user


@pytest.fixture
async def secretaria(session: AsyncSession):
    return await create_usuario(
        session, nome="Sec Sec", email="sec@test.com", perfil=Perfil.SECRETARIA,
    )


class TestCriarSolicitacao:
    async def test_criar_devolve_nome_do_aluno_em_sessao_limpa(
        self, client: AsyncClient, session: AsyncSession, responsavel
    ):
        """Regressão: `aluno_nome` precisa de eager load, não de lazy load.

        O fixture cria o `Aluno` na mesma sessão do request, então o objeto já
        está no identity map e o lazy load resolve sem IO — o bug só aparece
        quando o servidor não tem o aluno carregado. Aqui expulsamos o aluno do
        identity map para reproduzir o ambiente real; sem o join explícito o
        endpoint quebra com `MissingGreenlet`.
        """
        user, aluno = responsavel
        aluno_id = aluno.id
        assert aluno_id is not None
        # Commita antes de expulsar: só o que já foi persistido sobrevive, e o
        # commit também libera o lock de linha que o TRUNCATE de teardown usa.
        await session.commit()
        session.expunge_all()

        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno_id), "tipo": "historico_escolar"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["aluno_nome"] == "João Aluno"

    async def test_cria_solicitacao(self, client: AsyncClient, responsavel):
        user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "historico_escolar"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tipo"] == "historico_escolar"
        assert data["status"] == "pendente"
        assert data["aluno_nome"] == "João Aluno"

    async def test_responsavel_do_outro_aluno_e_bloqueado(
        self, client: AsyncClient, session: AsyncSession, responsavel, outro_responsavel,
    ):
        """IDOR: trocar o aluno_id no payload não pode vazar o acesso."""
        _user, aluno = responsavel
        token = await _login(client, "pedro@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "historico_escolar"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_responsavel_id_vem_do_token(
        self, client: AsyncClient, responsavel,
    ):
        """O corpo não pode forjar o dono da solicitação."""
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={
                "aluno_id": str(aluno.id),
                "tipo": "boletim_anual",
                "responsavel_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        listagem = await client.get(
            "/documentos/solicitacoes", headers={"Authorization": f"Bearer {token}"},
        )
        assert len(listagem.json()) == 1

    async def test_tipo_outro_exige_observacao(self, client: AsyncClient, responsavel):
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "outro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

        ok = await client.post(
            "/documentos/solicitacoes",
            json={
                "aluno_id": str(aluno.id),
                "tipo": "outro",
                "observacoes": "Cópia autenticada da certidão",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ok.status_code == 201

    async def test_observacoes_longas_dem_rejeitadas(
        self, client: AsyncClient, responsavel,
    ):
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={
                "aluno_id": str(aluno.id),
                "tipo": "boletim_bimestral",
                "observacoes": "x" * 1001,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_bloqueia_duplicata_em_aberto(self, client: AsyncClient, responsavel):
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        primeiro = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "declaracao_matricula"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert primeiro.status_code == 201

        segundo = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "declaracao_matricula"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert segundo.status_code == 422

    async def test_perfil_sem_permissao(self, client: AsyncClient, secretaria):
        token = await _login(client, "sec@test.com")
        response = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(uuid.uuid4()), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_sem_token(self, client: AsyncClient):
        response = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(uuid.uuid4()), "tipo": "boletim_anual"},
        )
        assert response.status_code == 401


class TestListarSolicitacoes:
    async def test_lista_apenas_as_minhas(self, client: AsyncClient, responsavel):
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            "/documentos/solicitacoes", headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_filtra_por_status(self, client: AsyncClient, responsavel):
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            "/documentos/solicitacoes?status=concluida",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == []


class TestCancelarSolicitacao:
    async def test_cancela_propria(self, client: AsyncClient, responsavel):
        _user, aluno = responsavel
        token = await _login(client, "maria@test.com")
        criada = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token}"},
        )
        solicitacao_id = criada.json()["id"]

        response = await client.post(
            f"/documentos/solicitacoes/{solicitacao_id}/cancelar",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelada"

    async def test_nao_cancela_de_outro(
        self, client: AsyncClient, responsavel, outro_responsavel,
    ):
        _user, aluno = responsavel
        token_maria = await _login(client, "maria@test.com")
        criada = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token_maria}"},
        )
        solicitacao_id = criada.json()["id"]

        token_pedro = await _login(client, "pedro@test.com")
        response = await client.post(
            f"/documentos/solicitacoes/{solicitacao_id}/cancelar",
            headers={"Authorization": f"Bearer {token_pedro}"},
        )
        assert response.status_code == 403

    async def test_nao_cancela_concluida(self, client: AsyncClient, responsavel, secretaria):
        _user, aluno = responsavel
        token_maria = await _login(client, "maria@test.com")
        criada = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token_maria}"},
        )
        solicitacao_id = criada.json()["id"]

        token_sec = await _login(client, "sec@test.com")
        await client.patch(
            f"/documentos/solicitacoes/admin/{solicitacao_id}",
            json={"status": "concluida", "resposta": "Documento pronto"},
            headers={"Authorization": f"Bearer {token_sec}"},
        )

        response = await client.post(
            f"/documentos/solicitacoes/{solicitacao_id}/cancelar",
            headers={"Authorization": f"Bearer {token_maria}"},
        )
        assert response.status_code == 422

    async def test_solicitacao_inexistente(self, client: AsyncClient, responsavel):
        token = await _login(client, "maria@test.com")
        response = await client.post(
            f"/documentos/solicitacoes/{uuid.uuid4()}/cancelar",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestSecretaria:
    async def test_secretaria_ve_todas(
        self, client: AsyncClient, responsavel, secretaria,
    ):
        _user, aluno = responsavel
        token_maria = await _login(client, "maria@test.com")
        await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_anual"},
            headers={"Authorization": f"Bearer {token_maria}"},
        )

        token_sec = await _login(client, "sec@test.com")
        response = await client.get(
            "/documentos/solicitacoes/admin/todas",
            headers={"Authorization": f"Bearer {token_sec}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_responsavel_nao_acessa_fila_da_secretaria(
        self, client: AsyncClient, responsavel,
    ):
        token = await _login(client, "maria@test.com")
        response = await client.get(
            "/documentos/solicitacoes/admin/todas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_conclui_solicitacao(self, client: AsyncClient, responsavel, secretaria):
        _user, aluno = responsavel
        token_maria = await _login(client, "maria@test.com")
        criada = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_bimestral"},
            headers={"Authorization": f"Bearer {token_maria}"},
        )
        solicitacao_id = criada.json()["id"]

        token_sec = await _login(client, "sec@test.com")
        response = await client.patch(
            f"/documentos/solicitacoes/admin/{solicitacao_id}",
            json={
                "status": "concluida",
                "resposta": "Retirar na secretaria",
                "documento_url": "https://exemplo.com/boletim.pdf",
            },
            headers={"Authorization": f"Bearer {token_sec}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "concluida"
        assert data["resposta"] == "Retirar na secretaria"
        assert data["documento_url"] == "https://exemplo.com/boletim.pdf"
        assert data["atendido_em"] is not None

    async def test_nao_altera_solicitacao_encerrada(
        self, client: AsyncClient, responsavel, secretaria,
    ):
        _user, aluno = responsavel
        token_maria = await _login(client, "maria@test.com")
        criada = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_bimestral"},
            headers={"Authorization": f"Bearer {token_maria}"},
        )
        solicitacao_id = criada.json()["id"]

        token_sec = await _login(client, "sec@test.com")
        await client.patch(
            f"/documentos/solicitacoes/admin/{solicitacao_id}",
            json={"status": "recusada", "resposta": "Documento indisponível"},
            headers={"Authorization": f"Bearer {token_sec}"},
        )
        response = await client.patch(
            f"/documentos/solicitacoes/admin/{solicitacao_id}",
            json={"status": "concluida"},
            headers={"Authorization": f"Bearer {token_sec}"},
        )
        assert response.status_code == 422

    async def test_secretaria_nao_usa_cancelamento(
        self, client: AsyncClient, responsavel, secretaria,
    ):
        _user, aluno = responsavel
        token_maria = await _login(client, "maria@test.com")
        criada = await client.post(
            "/documentos/solicitacoes",
            json={"aluno_id": str(aluno.id), "tipo": "boletim_bimestral"},
            headers={"Authorization": f"Bearer {token_maria}"},
        )
        solicitacao_id = criada.json()["id"]

        token_sec = await _login(client, "sec@test.com")
        response = await client.patch(
            f"/documentos/solicitacoes/admin/{solicitacao_id}",
            json={"status": "cancelada"},
            headers={"Authorization": f"Bearer {token_sec}"},
        )
        assert response.status_code == 422
