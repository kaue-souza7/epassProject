from decimal import Decimal
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.academic_config.service import ConfiguracaoAcademicaService
from app.shared.enums import Parentesco, Perfil, StatusFrequencia
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_ano_letivo,
    create_avaliacao,
    create_chamada,
    create_disciplina,
    create_frequencia,
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
    ano = await create_ano_letivo(session, ano=2026)
    config_service = ConfiguracaoAcademicaService(session)
    await config_service.obter(ano.id)
    serie = await create_serie(session)
    turma = await create_turma(
        session, codigo="1A", serie_id=serie.id, ano_letivo_id=ano.id, vagas_total=30,
    )
    disciplina = await create_disciplina(session, codigo="MAT", nome="Matemática")
    disciplina2 = await create_disciplina(session, codigo="POR", nome="Português")
    professor_user = await create_usuario(session, perfil=Perfil.PROFESSOR)
    professor = await create_professor(session, usuario_id=professor_user.id)
    alocacao1 = await create_alocacao(
        session, professor_id=professor.usuario_id, turma_id=turma.id, disciplina_id=disciplina.id,
    )
    alocacao2 = await create_alocacao(
        session, professor_id=professor.usuario_id, turma_id=turma.id, disciplina_id=disciplina2.id,
    )
    aluno = await create_aluno(session, nome="João")
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno.id, responsavel.id, Parentesco.MAE)
    matricula = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)

    avaliacao1 = await create_avaliacao(
        session, alocacao_id=alocacao1.id, titulo="Prova MAT", bimestre=1, peso=2, nota_maxima=10,
    )
    avaliacao2 = await create_avaliacao(
        session, alocacao_id=alocacao1.id, titulo="Trabalho MAT", bimestre=1, peso=1, nota_maxima=10,
    )
    await create_nota(session, avaliacao1.id, matricula.id, valor=8.0)
    await create_nota(session, avaliacao2.id, matricula.id, valor=9.0)

    chamada = await create_chamada(session, alocacao_id=alocacao1.id, data_hora_aula=datetime(2026, 1, 15, 8, 0, 0, tzinfo=timezone.utc))
    chamada2 = await create_chamada(session, alocacao_id=alocacao1.id, data_hora_aula=datetime(2026, 2, 15, 8, 0, 0, tzinfo=timezone.utc))
    await create_frequencia(session, chamada.id, matricula.id, StatusFrequencia.PRESENTE)
    await create_frequencia(session, chamada2.id, matricula.id, StatusFrequencia.FALTA)

    return {
        "matricula": matricula,
        "aluno": aluno,
        "turma": turma,
        "disciplina": disciplina,
        "alocacao1": alocacao1,
        "professor_user": professor_user,
    }


async def _login_professor(client: AsyncClient, professor_user) -> None:
    token = create_access_token(
        subject=str(professor_user.id),
        extra_claims={"perfil": professor_user.perfil.value},
    )
    client.headers = {"Authorization": f"Bearer {token}"}


class TestBimestralReport:
    async def test_bimestral_report(self, client: AsyncClient, setup_data):
        matricula = setup_data["matricula"]
        await _login_professor(client, setup_data["professor_user"])
        response = await client.get(
            f"/reports/report-card/{matricula.id}",
            params={"bimestre": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matricula_id"] == str(matricula.id)
        assert data["bimestre"] == 1
        assert data["aluno_nome"] == "João"
        assert len(data["disciplinas"]) > 0

    async def test_bimestral_report_not_found(self, auth_client: AsyncClient):
        response = await auth_client.get(
            "/reports/report-card/00000000-0000-0000-0000-000000000000",
            params={"bimestre": 1},
        )
        assert response.status_code == 404


class TestAnnualReport:
    async def test_annual_report(self, client: AsyncClient, setup_data):
        matricula = setup_data["matricula"]
        await _login_professor(client, setup_data["professor_user"])
        response = await client.get(
            f"/reports/report-card/{matricula.id}/annual",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matricula_id"] == str(matricula.id)
        assert len(data["bimestres"]) == 4
        assert "situacao_final" in data

    async def test_annual_report_not_found(self, auth_client: AsyncClient):
        response = await auth_client.get(
            "/reports/report-card/00000000-0000-0000-0000-000000000000/annual",
        )
        assert response.status_code == 404


class TestWeightedAverage:
    async def test_weighted_average(self, client: AsyncClient, setup_data):
        matricula = setup_data["matricula"]
        await _login_professor(client, setup_data["professor_user"])
        response = await client.get(
            f"/reports/report-card/{matricula.id}",
            params={"bimestre": 1},
        )
        assert response.status_code == 200
        data = response.json()
        disc = next(d for d in data["disciplinas"] if d["disciplina_nome"] == "Matemática")
        expected = (8.0 * 2 + 9.0 * 1) / (2 + 1)
        assert float(disc["media"]) == pytest.approx(expected, rel=1e-2)


class TestFrequency:
    async def test_frequency_in_report(self, client: AsyncClient, setup_data):
        matricula = setup_data["matricula"]
        await _login_professor(client, setup_data["professor_user"])
        response = await client.get(
            f"/reports/report-card/{matricula.id}",
            params={"bimestre": 1},
        )
        assert response.status_code == 200
        data = response.json()
        disc = next(d for d in data["disciplinas"] if d["disciplina_nome"] == "Matemática")
        assert disc["frequencia"] is not None
        assert disc["frequencia"] == 50.0
