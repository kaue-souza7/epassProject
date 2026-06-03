from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.enums import Parentesco, Perfil
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_ano_letivo,
    create_disciplina,
    create_matricula,
    create_professor,
    create_responsavel_aluno,
    create_serie,
    create_turma,
    create_usuario,
)


@pytest.fixture
async def setup_data(session: AsyncSession):
    ano = await create_ano_letivo(session)
    serie = await create_serie(session)
    turma = await create_turma(
        session, codigo="1A", serie_id=serie.id, ano_letivo_id=ano.id, vagas_total=30,
    )
    disciplina = await create_disciplina(session)
    professor = await create_professor(session)
    alocacao = await create_alocacao(
        session, professor_id=professor.usuario_id, turma_id=turma.id, disciplina_id=disciplina.id,
    )
    aluno = await create_aluno(session, nome="João")
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno.id, responsavel.id, Parentesco.MAE)
    matricula = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    return {
        "alocacao": alocacao,
        "turma": turma,
        "matricula": matricula,
        "aluno": aluno,
    }


class TestCalls:
    async def test_create_call(self, auth_client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        response = await auth_client.post("/attendance/calls", json={
            "alocacao_id": str(alocacao.id),
            "data_hora_aula": "2026-03-10T08:00:00",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["alocacao_id"] == str(alocacao.id)

    async def test_duplicate_call(self, auth_client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        body = {
            "alocacao_id": str(alocacao.id),
            "data_hora_aula": "2026-03-10T08:00:00",
        }
        await auth_client.post("/attendance/calls", json=body)
        response = await auth_client.post("/attendance/calls", json=body)
        assert response.status_code == 409

    async def test_create_call_auto_creates_frequencies(self, auth_client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        response = await auth_client.post("/attendance/calls", json={
            "alocacao_id": str(alocacao.id),
            "data_hora_aula": "2026-03-11T08:00:00",
        })
        assert response.status_code == 201


class TestFrequencies:
    async def test_register_frequencies(self, auth_client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        matricula = setup_data["matricula"]

        call_resp = await auth_client.post("/attendance/calls", json={
            "alocacao_id": str(alocacao.id),
            "data_hora_aula": "2026-03-12T08:00:00",
        })
        chamada_id = call_resp.json()["id"]

        response = await auth_client.post("/attendance/frequencies", json={
            "chamada_id": chamada_id,
            "frequencias": [
                {"matricula_id": str(matricula.id), "status": "presente"},
            ],
        })
        assert response.status_code == 204

    async def test_register_frequencies_invalid_chamada(self, auth_client: AsyncClient, setup_data):
        matricula = setup_data["matricula"]
        response = await auth_client.post("/attendance/frequencies", json={
            "chamada_id": "00000000-0000-0000-0000-000000000000",
            "frequencias": [
                {"matricula_id": str(matricula.id), "status": "presente"},
            ],
        })
        assert response.status_code == 404
