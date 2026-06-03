from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.enums import Parentesco, Perfil
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_ano_letivo,
    create_avaliacao,
    create_disciplina,
    create_matricula,
    create_nota,
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
        "disciplina": disciplina,
    }


class TestCreateAssessment:
    async def test_create_assessment(self, client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        response = await client.post("/assessments", json={
            "alocacao_id": str(alocacao.id),
            "titulo": "Prova Bimestral",
            "tipo": "prova",
            "peso": 2,
            "nota_maxima": 10,
            "bimestre": 1,
            "data_aplicacao": "2026-03-15",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["titulo"] == "Prova Bimestral"
        assert data["bimestre"] == 1
        assert Decimal(data["nota_maxima"]) == Decimal("10")

    async def test_duplicate_assessment(self, client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        body = {
            "alocacao_id": str(alocacao.id),
            "titulo": "Prova Bimestral",
            "tipo": "prova",
            "peso": 2,
            "nota_maxima": 10,
            "bimestre": 1,
            "data_aplicacao": "2026-03-15",
        }
        await client.post("/assessments", json=body)
        response = await client.post("/assessments", json=body)
        assert response.status_code == 409


class TestCreateGrade:
    async def test_create_grade(self, client: AsyncClient, setup_data, session: AsyncSession):
        alocacao = setup_data["alocacao"]
        matricula = setup_data["matricula"]

        av_resp = await client.post("/assessments", json={
            "alocacao_id": str(alocacao.id),
            "titulo": "Prova",
            "tipo": "prova",
            "peso": 1,
            "nota_maxima": 10,
            "bimestre": 1,
            "data_aplicacao": "2026-03-15",
        })
        avaliacao_id = av_resp.json()["id"]

        response = await client.post("/assessments/grades", json={
            "avaliacao_id": avaliacao_id,
            "notas": [
                {"matricula_id": str(matricula.id), "valor": 8.5},
            ],
        })
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert Decimal(data[0]["valor"]) == Decimal("8.5")

    async def test_grade_above_max(self, client: AsyncClient, setup_data):
        alocacao = setup_data["alocacao"]
        matricula = setup_data["matricula"]

        av_resp = await client.post("/assessments", json={
            "alocacao_id": str(alocacao.id),
            "titulo": "Prova",
            "tipo": "prova",
            "peso": 1,
            "nota_maxima": 10,
            "bimestre": 1,
            "data_aplicacao": "2026-03-15",
        })
        avaliacao_id = av_resp.json()["id"]

        response = await client.post("/assessments/grades", json={
            "avaliacao_id": avaliacao_id,
            "notas": [
                {"matricula_id": str(matricula.id), "valor": 11.0},
            ],
        })
        assert response.status_code == 422
