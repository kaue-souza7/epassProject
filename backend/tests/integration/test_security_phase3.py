"""Tests for Phase 3: JWT_SECRET validation, login rate limit, boletim access control."""
import os
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.security import create_access_token
from app.modules.allocations.models import Alocacao
from app.modules.boletim.models import LiberacaoBoletim
from app.modules.enrollments.models import Matricula
from app.shared.enums import Perfil, StatusMatricula
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_avaliacao,
    create_matricula,
    create_nota,
    create_professor,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)


async def _login_as(session, user) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"perfil": user.perfil.value})


# ─── JWT_SECRET: boot falha com segredo padrão ─────────────────────

def test_jwt_secret_padrao_falha_no_boot(monkeypatch):
    """Aplicação falha ao iniciar com JWT_SECRET padrão/inseguro."""
    from app.config import Settings

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings()


def test_jwt_secret_curto_falha_em_producao(monkeypatch):
    """Em produção, JWT_SECRET curto (< 32 chars) falha no boot."""
    from app.config import Settings

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "short-secret")
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings()


def test_jwt_secret_valido_aceito(monkeypatch):
    """Segredo forte é aceito em produção."""
    from app.config import Settings

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "x" * 48)
    settings = Settings()
    assert len(settings.JWT_SECRET) >= 32


# ─── Rate limit de login ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_login(client: AsyncClient):
    """Mais de 5 tentativas de login por minuto retornam 429."""
    app.state.limiter.enabled = True
    try:
        for _ in range(5):
            resp = await client.post("/auth/login", json={
                "email": f"nonexistent-{uuid.uuid4().hex[:8]}@test.com",
                "password": "wrong",
            })
            assert resp.status_code == 401

        resp = await client.post("/auth/login", json={
            "email": "another-nonexistent@test.com",
            "password": "wrong",
        })
        assert resp.status_code == 429
    finally:
        app.state.limiter.enabled = False


# ─── Boletim: ownership e vazamento anual ──────────────────────────

async def _setup_escola(session):
    """Turma com professor e aluno responsável, notas lançadas."""
    from app.modules.academic_config.service import ConfiguracaoAcademicaService
    from tests.factories import create_ano_letivo, create_disciplina, create_serie

    turma = await create_turma(session, codigo="3A")
    await ConfiguracaoAcademicaService(session).obter(turma.ano_letivo_id)
    professor_user = await create_usuario(session, perfil=Perfil.PROFESSOR)
    professor = await create_professor(session, usuario_id=professor_user.id)
    alocacao = await create_alocacao(
        session, professor_id=professor.usuario_id, turma_id=turma.id,
    )
    aluno = await create_aluno(session, nome="Filho Boletim")
    matricula = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    avaliacao = await create_avaliacao(session, alocacao_id=alocacao.id, bimestre=1)
    await create_nota(session, avaliacao_id=avaliacao.id, matricula_id=matricula.id, valor=9.0)
    await session.commit()
    return turma, professor_user, aluno, matricula, alocacao


@pytest.mark.asyncio
async def test_boletim_anual_antes_liberacao_nao_vaza(client: AsyncClient, session):
    """Responsável não vê situação final do boletim anual antes da liberação completa."""
    _, _, aluno, matricula, _ = await _setup_escola(session)
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/reports/report-card/{matricula.id}/annual")
    assert resp.status_code == 200
    body = resp.json()
    assert body["situacao_final"] is None
    assert body["media_pre_recuperacao"] is None
    assert body["media_pos_recuperacao"] is None


@pytest.mark.asyncio
async def test_boletim_anual_apos_liberacao_mostra_situacao(client: AsyncClient, session):
    """Com todas as disciplinas liberadas nos 4 bimestres, situação final é exibida."""
    _, _, aluno, matricula, alocacao = await _setup_escola(session)
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    for b in range(1, 5):
        turma_row = (await session.execute(
            select(Alocacao).where(Alocacao.id == alocacao.id)
        )).scalar_one()
        liberacao = LiberacaoBoletim(
            professor_id=alocacao.professor_id,
            turma_id=alocacao.turma_id,
            disciplina_id=alocacao.disciplina_id,
            alocacao_id=alocacao.id,
            ano_letivo_id=turma_row.turma.ano_letivo_id,
            bimestre=b,
            ativo=True,
        )
        session.add(liberacao)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/reports/report-card/{matricula.id}/annual")
    assert resp.status_code == 200
    body = resp.json()
    assert body["situacao_final"] is not None


@pytest.mark.asyncio
async def test_responsavel_nao_ve_boletim_de_outro_aluno(client: AsyncClient, session):
    """Responsável recebe 403 ao acessar boletim de matrícula não vinculada."""
    _, _, _, matricula, _ = await _setup_escola(session)
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/reports/report-card/{matricula.id}?bimestre=1")
    assert resp.status_code == 403

    resp_annual = await client.get(f"/reports/report-card/{matricula.id}/annual")
    assert resp_annual.status_code == 403


@pytest.mark.asyncio
async def test_professor_nao_ve_boletim_de_turma_que_nao_leciona(client: AsyncClient, session):
    """Professor recebe 403 ao acessar boletim de turma sem alocação ativa."""
    turma, professor_user, aluno, matricula, _ = await _setup_escola(session)

    outro_turma = await create_turma(session, codigo="5B")
    outro_professor_user = await create_usuario(session, perfil=Perfil.PROFESSOR)
    outro_professor = await create_professor(session, usuario_id=outro_professor_user.id)
    await create_alocacao(session, professor_id=outro_professor.usuario_id, turma_id=outro_turma.id)
    aluno_outro = await create_aluno(session, nome="Outro Aluno")
    matricula_outro = await create_matricula(session, aluno_id=aluno_outro.id, turma_id=outro_turma.id)
    await session.commit()

    token = await _login_as(session, outro_professor_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/reports/report-card/{matricula.id}?bimestre=1")
    assert resp.status_code == 403

    resp_own = await client.get(f"/reports/report-card/{matricula_outro.id}?bimestre=1")
    assert resp_own.status_code == 200


@pytest.mark.asyncio
async def test_professor_acessa_boletim_de_propria_turma(client: AsyncClient, session):
    """Professor com alocação ativa na turma acessa o boletim normalmente."""
    _, professor_user, _, matricula, _ = await _setup_escola(session)

    token = await _login_as(session, professor_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/reports/report-card/{matricula.id}?bimestre=1")
    assert resp.status_code == 200
    assert resp.json()["matricula_id"] == str(matricula.id)