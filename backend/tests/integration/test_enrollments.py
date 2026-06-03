import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.enums import Parentesco, Perfil
from tests.factories import (
    create_aluno,
    create_ano_letivo,
    create_serie,
    create_turma,
    create_usuario,
    create_responsavel_aluno,
)


@pytest.fixture
async def setup_data(session: AsyncSession):
    ano = await create_ano_letivo(session)
    serie = await create_serie(session)
    turma = await create_turma(
        session, codigo="1A", serie_id=serie.id, ano_letivo_id=ano.id, vagas_total=2,
    )
    aluno = await create_aluno(session, nome="Maria Aluna", cpf="12345678901")
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno.id, responsavel.id, Parentesco.MAE)
    return {"turma": turma, "aluno": aluno, "ano": ano, "serie": serie}


class TestCreateEnrollment:
    async def test_create_enrollment(self, admin_client: AsyncClient, setup_data):
        turma = setup_data["turma"]
        aluno = setup_data["aluno"]

        response = await admin_client.post("/enrollments", json={
            "aluno_id": str(aluno.id),
            "turma_id": str(turma.id),
        })
        assert response.status_code == 201
        data = response.json()
        assert data["aluno_id"] == str(aluno.id)
        assert data["turma_id"] == str(turma.id)
        assert data["status"] == "ativa"

    async def test_duplicate_enrollment(self, admin_client: AsyncClient, setup_data, session: AsyncSession):
        turma = setup_data["turma"]
        aluno = setup_data["aluno"]

        await admin_client.post("/enrollments", json={
            "aluno_id": str(aluno.id),
            "turma_id": str(turma.id),
        })

        response = await admin_client.post("/enrollments", json={
            "aluno_id": str(aluno.id),
            "turma_id": str(turma.id),
        })
        assert response.status_code == 409

    async def test_turma_sem_vagas(self, admin_client: AsyncClient, setup_data, session: AsyncSession):
        turma = setup_data["turma"]
        aluno = setup_data["aluno"]

        await admin_client.post("/enrollments", json={
            "aluno_id": str(aluno.id),
            "turma_id": str(turma.id),
        })

        aluno2 = await create_aluno(session, nome="Pedro Aluno", cpf="98765432101")
        resp2 = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
        await create_responsavel_aluno(session, aluno2.id, resp2.id, Parentesco.PAI)

        response = await admin_client.post("/enrollments", json={
            "aluno_id": str(aluno2.id),
            "turma_id": str(turma.id),
        })
        assert response.status_code == 201

        aluno3 = await create_aluno(session, nome="Ana Aluna", cpf="11122233344")
        resp3 = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
        await create_responsavel_aluno(session, aluno3.id, resp3.id, Parentesco.MAE)

        response = await admin_client.post("/enrollments", json={
            "aluno_id": str(aluno3.id),
            "turma_id": str(turma.id),
        })
        assert response.status_code == 409
