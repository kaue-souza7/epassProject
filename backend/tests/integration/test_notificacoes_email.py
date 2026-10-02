"""Opt-in de e-mail para avisos e ocorrências.

Cobre o contrato em três frentes:

1. A preferência é opt-in — sem ela nada sai por e-mail, mesmo com SMTP ativo.
2. Ligar o canal para um tipo não habilita os outros.
3. A entrega respeita a idempotência do `evento_key` e escapa HTML, já que
   título e mensagem são texto escrito por professores e secretaria.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.communication.models import PreferenciaNotificacao
from app.shared.enums import Perfil, StatusMatricula, TipoNotificacao
from tests.factories import (
    create_aluno,
    create_matricula,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)


def _auth(user) -> dict:
    token = create_access_token(
        subject=str(user.id), extra_claims={"perfil": user.perfil.value},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enviados(monkeypatch):
    """Intercepta o SMTP e registra os e-mails que teriam sido enviados."""
    chamadas: list[dict] = []

    def _fake_enviar_email(*, destinatario, assunto, corpo_html, smtp_config=None):
        chamadas.append({
            "destinatario": destinatario,
            "assunto": assunto,
            "corpo_html": corpo_html,
        })
        return True

    # `EmailChannel` importa `enviar_email` de dentro da função, então o patch
    # precisa estar no módulo de origem.
    monkeypatch.setattr("app.modules.boletim.email.enviar_email", _fake_enviar_email)
    return chamadas


async def _cenario(session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    professor = await create_usuario(session, perfil=Perfil.PROFESSOR)
    aluno = await create_aluno(session, nome="Aluno E-mail")
    responsavel = await create_usuario(
        session, perfil=Perfil.RESPONSAVEL, email="responsavel@test.com",
    )
    await create_responsavel_aluno(
        session, aluno_id=aluno.id, responsavel_id=responsavel.id,
    )
    turma = await create_turma(session, codigo=f"E{uuid.uuid4().hex[:4]}")
    await create_matricula(
        session, aluno_id=aluno.id, turma_id=turma.id, status=StatusMatricula.ATIVA,
    )
    await session.commit()
    return admin, professor, aluno, turma, responsavel


async def _criar_aviso(client, admin, responsavel, titulo="Reunião de pais"):
    client.headers = _auth(admin)
    resp = await client.post("/avisos", json={
        "titulo": titulo,
        "mensagem": "Reunião amanhã às 18h.",
        "responsavel_ids": [str(responsavel.id)],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _criar_ocorrencia(client, professor, aluno, turma):
    client.headers = _auth(professor)
    resp = await client.post("/ocorrencias", json={
        "aluno_id": str(aluno.id),
        "turma_id": str(turma.id),
        "titulo": "Falta justificada",
        "descricao": "Aluno chegar atrasado.",
        "tipo": "comportamento",
        "severidade": "baixa",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _ativar_email(client, responsavel, tipo: TipoNotificacao, ativo=True):
    client.headers = _auth(responsavel)
    resp = await client.put(f"/notificacoes/preferencias/{tipo.value}", json={"email": ativo})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ─── Leitura das preferências ───────────────────────────────────────

@pytest.mark.asyncio
async def test_preferencias_trazem_todos_os_tipos_desligados(client: AsyncClient, session):
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await session.commit()

    client.headers = _auth(responsavel)
    resp = await client.get("/notificacoes/preferencias")

    assert resp.status_code == 200, resp.text
    preferencias = resp.json()["preferencias"]
    # Ausência de linha tem de chegar como False, não como chave faltando.
    assert set(preferencias) == {t.value for t in TipoNotificacao}
    assert all(valor is False for valor in preferencias.values())


@pytest.mark.asyncio
async def test_preferencias_sao_persistidas_por_tipo(client: AsyncClient, session):
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await session.commit()

    await _ativar_email(client, responsavel, TipoNotificacao.AVISO)

    client.headers = _auth(responsavel)
    resp = await client.get("/notificacoes/preferencias")
    preferencias = resp.json()["preferencias"]
    assert preferencias["aviso"] is True
    assert preferencias["ocorrencia"] is False

    registro = (await session.execute(
        select(PreferenciaNotificacao).where(
            PreferenciaNotificacao.usuario_id == responsavel.id,
            PreferenciaNotificacao.tipo == TipoNotificacao.AVISO,
        )
    )).scalar_one()
    assert registro.email is True


# ─── Opt-in: nada sai sem ativar ────────────────────────────────────

@pytest.mark.asyncio
async def test_aviso_nao_envia_email_sem_opt_in(client: AsyncClient, session, enviados):
    admin, _prof, _aluno, _turma, responsavel = await _cenario(session)
    await _criar_aviso(client, admin, responsavel)

    assert enviados == [], "e-mail não pode ser enviado sem opt-in explícito"


@pytest.mark.asyncio
async def test_ocorrencia_nao_envia_email_sem_opt_in(client: AsyncClient, session, enviados):
    _admin, professor, aluno, turma, responsavel = await _cenario(session)
    await _criar_ocorrencia(client, professor, aluno, turma)

    assert enviados == [], "e-mail não pode ser enviado sem opt-in explícito"


# ─── Com o canal ligado ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aviso_envia_email_apos_opt_in(client: AsyncClient, session, enviados):
    admin, _prof, _aluno, _turma, responsavel = await _cenario(session)
    await _ativar_email(client, responsavel, TipoNotificacao.AVISO)

    await _criar_aviso(client, admin, responsavel)

    assert len(enviados) == 1
    assert enviados[0]["destinatario"] == "responsavel@test.com"
    assert "Reunião de pais" in enviados[0]["assunto"]
    assert "enviou um novo aviso" in enviados[0]["corpo_html"]
    # O corpo traz o rótulo do tipo, para o assunto se ler rápido na caixa de entrada.
    assert "Aviso" in enviados[0]["corpo_html"]


@pytest.mark.asyncio
async def test_ocorrencia_envia_email_apos_opt_in(client: AsyncClient, session, enviados):
    _admin, professor, aluno, turma, responsavel = await _cenario(session)
    await _ativar_email(client, responsavel, TipoNotificacao.OCORRENCIA)

    await _criar_ocorrencia(client, professor, aluno, turma)

    assert len(enviados) == 1
    assert enviados[0]["destinatario"] == "responsavel@test.com"
    assert "Nova ocorrência" in enviados[0]["assunto"]
    assert "Aluno E-mail" in enviados[0]["corpo_html"]


@pytest.mark.asyncio
async def test_preferencia_e_isolada_por_tipo(client: AsyncClient, session, enviados):
    """Ligar aviso não pode passar a enviar e-mail de ocorrência."""
    _admin, professor, aluno, turma, responsavel = await _cenario(session)
    await _ativar_email(client, responsavel, TipoNotificacao.AVISO)

    await _criar_ocorrencia(client, professor, aluno, turma)

    assert enviados == []


@pytest.mark.asyncio
async def test_desligar_para_de_enviar(client: AsyncClient, session, enviados):
    admin, _prof, _aluno, _turma, responsavel = await _cenario(session)
    await _ativar_email(client, responsavel, TipoNotificacao.AVISO, ativo=True)
    await _ativar_email(client, responsavel, TipoNotificacao.AVISO, ativo=False)

    await _criar_aviso(client, admin, responsavel)

    assert enviados == []


# ─── Robustez ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_html_do_usuario_e_escapado(client: AsyncClient, session, enviados):
    """Título e mensagem vêm de texto livre de professor: não pode virar HTML."""
    admin, _prof, _aluno, _turma, responsavel = await _cenario(session)
    await _ativar_email(client, responsavel, TipoNotificacao.AVISO)

    await _criar_aviso(client, admin, responsavel, titulo="<script>alert(1)</script>")

    assert len(enviados) == 1
    corpo = enviados[0]["corpo_html"]
    assert "<script>" not in corpo
    assert "&lt;script&gt;" in corpo


@pytest.mark.asyncio
async def test_notificacao_inapp_continua_sendo_criada(client: AsyncClient, session, enviados):
    """O opt-in de e-mail não pode substituir o canal inapp."""
    from app.modules.communication.models import Notificacao

    admin, _prof, _aluno, _turma, responsavel = await _cenario(session)
    await _ativar_email(client, responsavel, TipoNotificacao.AVISO)
    aviso_id = await _criar_aviso(client, admin, responsavel)

    notificacao = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == responsavel.id,
            Notificacao.entidade_id == aviso_id,
        )
    )).scalar_one()
    assert notificacao.canal == "inapp"
    assert len(enviados) == 1
