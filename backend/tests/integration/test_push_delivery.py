"""Entrega real de push: payload, tickets e recibos do Expo Push Service.

Complementa `test_ocorrencias_fluxo.py` cobrindo o pós-envio: o ticket imediato
é persistido e o recibo (`/push/getReceipts`) trata `DeviceNotRegistered`,
mantendo a notificação interna intacta em qualquer falha.
"""
import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.communication.models import Notificacao, PushTicket, PushToken
from app.modules.communication.scheduler import PushReceiptScheduler
from app.shared.enums import Perfil, StatusMatricula
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_disciplina,
    create_matricula,
    create_professor,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)

EXPO_SEND = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPTS = "https://exp.host/--/api/v2/push/getReceipts"


def _auth(user) -> dict:
    token = create_access_token(
        subject=str(user.id), extra_claims={"perfil": user.perfil.value},
    )
    return {"Authorization": f"Bearer {token}"}


class _FabricaSessao:
    """Adapta a sessão do teste para a interface async context manager."""

    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


async def _cenario(session, nome_aluno="Aluno Push"):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await create_usuario(session, perfil=Perfil.PROFESSOR)
    await create_professor(session, usuario_id=professor.id)
    disciplina = await create_disciplina(session)
    await create_alocacao(
        session, professor_id=professor.id, turma_id=turma.id,
        disciplina_id=disciplina.id,
    )
    aluno = await create_aluno(session, nome=nome_aluno)
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(
        session, aluno_id=aluno.id, responsavel_id=responsavel.id,
    )
    await create_matricula(
        session, aluno_id=aluno.id, turma_id=turma.id,
        status=StatusMatricula.ATIVA,
    )
    await session.commit()
    return turma, professor, aluno, responsavel


async def _registrar_token(client, responsavel, token="ExponentPushToken[recibo-1]"):
    client.headers = _auth(responsavel)
    resp = await client.post("/notificacoes/push-tokens", json={
        "token": token, "plataforma": "expo",
    })
    assert resp.status_code == 201, resp.text
    return token


async def _criar_ocorrencia(client, professor, aluno, turma):
    client.headers = _auth(professor)
    return await client.post("/ocorrencias", json={
        "aluno_id": str(aluno.id),
        "turma_id": str(turma.id),
        "titulo": "Ocorrência push",
        "descricao": "Teste de entrega real de push.",
        "tipo": "comportamento",
        "severidade": "media",
    })


# ─── Aviso: texto e payload do push ─────────────────────────────────

@pytest.mark.asyncio
async def test_aviso_push_texto_e_payload(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    aluno = await create_aluno(session, nome="Aluno Aviso")
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(
        session, aluno_id=aluno.id, responsavel_id=responsavel.id,
    )
    await session.commit()
    token = await _registrar_token(client, responsavel, "ExponentPushToken[aviso-1]")

    client.headers = _auth(admin)
    with respx.mock(assert_all_called=False) as mock:
        rota = mock.post(EXPO_SEND).mock(
            return_value=httpx.Response(200, json={"data": [{"status": "ok", "id": "t-aviso"}]})
        )
        resp = await client.post("/avisos", json={
            "titulo": "Reunião",
            "mensagem": "Reunião amanhã.",
            "responsavel_ids": [str(responsavel.id)],
        })
        assert resp.status_code == 201, resp.text
        aviso_id = resp.json()["id"]

        payload = json.loads(rota.calls[0].request.content)[0]
        assert payload["to"] == token
        assert payload["title"] == "Novo aviso"
        assert "enviou um novo aviso" in payload["body"]
        assert payload["data"]["aviso_id"] == aviso_id
        assert payload["data"]["entidade_tipo"] == "aviso"
        assert payload["data"]["notification_id"]

        # ticket persistido para conferência posterior
        ticket = (await session.execute(
            select(PushTicket).where(PushTicket.ticket_id == "t-aviso")
        )).scalar_one()
        assert ticket.token == token
        assert ticket.usuario_id == responsavel.id
        assert ticket.verificado_em is None


# ─── Ocorrência: texto e payload do push ────────────────────────────

@pytest.mark.asyncio
async def test_ocorrencia_push_texto_e_payload(client: AsyncClient, session):
    turma, professor, aluno, responsavel = await _cenario(session, "Aluno Ocorrência Push")
    token = await _registrar_token(client, responsavel, "ExponentPushToken[oc-1]")

    with respx.mock(assert_all_called=False) as mock:
        rota = mock.post(EXPO_SEND).mock(
            return_value=httpx.Response(200, json={"data": [{"status": "ok", "id": "t-oc"}]})
        )
        resp = await _criar_ocorrencia(client, professor, aluno, turma)
        assert resp.status_code == 201, resp.text
        ocorrencia_id = resp.json()["id"]

        payload = json.loads(rota.calls[0].request.content)[0]
        assert payload["title"] == "Nova ocorrência"
        assert payload["body"] == "Foi registrada uma nova ocorrência para Aluno Ocorrência Push."
        assert payload["data"]["ocorrencia_id"] == ocorrencia_id
        assert payload["data"]["tipo"] == "ocorrencia"
        assert payload["data"]["notification_id"]
        # sem dados sensíveis no payload
        assert "Teste de entrega" not in json.dumps(payload["data"])
    assert token is not None


# ─── Recibos ────────────────────────────────────────────────────────

async def _preparar_ticket_pendente(session, usuario_id, token, ticket_id):
    ticket = PushTicket(
        ticket_id=ticket_id,
        usuario_id=usuario_id,
        token=token,
        criado_em=datetime.now(UTC) - timedelta(minutes=5),
    )
    session.add(ticket)
    await session.flush()
    return ticket


@pytest.mark.asyncio
async def test_recibo_ok_mantem_token_ativo(client: AsyncClient, session):
    turma, professor, aluno, responsavel = await _cenario(session, "Aluno Recibo OK")
    token = await _registrar_token(client, responsavel, "ExponentPushToken[ok-1]")
    await _preparar_ticket_pendente(session, responsavel.id, token, "ticket-ok")
    await session.commit()

    scheduler = PushReceiptScheduler()
    scheduler._session_factory = _FabricaSessao(session)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(EXPO_RECEIPTS).mock(
            return_value=httpx.Response(200, json={"data": {"ticket-ok": {"status": "ok"}}})
        )
        verificados = await scheduler._processar_ciclo()
    assert verificados == 1

    session.expire_all()
    ticket = (await session.execute(
        select(PushTicket).where(PushTicket.ticket_id == "ticket-ok")
    )).scalar_one()
    assert ticket.verificado_em is not None
    assert ticket.sucesso is True
    registro = (await session.execute(
        select(PushToken).where(PushToken.token == token)
    )).scalar_one()
    assert registro.ativo is True
    assert turma is not None and professor is not None and aluno is not None


@pytest.mark.asyncio
async def test_recibo_device_not_registered_desativa_token(client: AsyncClient, session):
    turma, professor, aluno, responsavel = await _cenario(session, "Aluno Recibo Inválido")
    token = await _registrar_token(client, responsavel, "ExponentPushToken[bad-1]")
    await _preparar_ticket_pendente(session, responsavel.id, token, "ticket-bad")
    await session.commit()

    scheduler = PushReceiptScheduler()
    scheduler._session_factory = _FabricaSessao(session)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(EXPO_RECEIPTS).mock(return_value=httpx.Response(200, json={
            "data": {"ticket-bad": {
                "status": "error",
                "message": "The device is not registered",
                "details": {"error": "DeviceNotRegistered"},
            }},
        }))
        assert await scheduler._processar_ciclo() == 1

    session.expire_all()
    ticket = (await session.execute(
        select(PushTicket).where(PushTicket.ticket_id == "ticket-bad")
    )).scalar_one()
    assert ticket.sucesso is False
    assert ticket.erro == "DeviceNotRegistered"
    registro = (await session.execute(
        select(PushToken).where(PushToken.token == token)
    )).scalar_one()
    assert registro.ativo is False
    assert turma is not None and professor is not None and aluno is not None


@pytest.mark.asyncio
async def test_recibo_indisponivel_permanece_pendente(client: AsyncClient, session):
    turma, professor, aluno, responsavel = await _cenario(session, "Aluno Recibo Pendente")
    token = await _registrar_token(client, responsavel, "ExponentPushToken[pend-1]")
    await _preparar_ticket_pendente(session, responsavel.id, token, "ticket-pend")
    await session.commit()

    scheduler = PushReceiptScheduler()
    scheduler._session_factory = _FabricaSessao(session)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(EXPO_RECEIPTS).mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        assert await scheduler._processar_ciclo() == 0

    session.expire_all()
    ticket = (await session.execute(
        select(PushTicket).where(PushTicket.ticket_id == "ticket-pend")
    )).scalar_one()
    assert ticket.verificado_em is None
    assert turma is not None and professor is not None and aluno is not None


# ─── Falha do Expo Push Service ─────────────────────────────────────

@pytest.mark.asyncio
async def test_falha_do_expo_nao_perde_notificacao_interna(client: AsyncClient, session):
    turma, professor, aluno, responsavel = await _cenario(session, "Aluno Expo Fora")
    await _registrar_token(client, responsavel, "ExponentPushToken[down-1]")

    with respx.mock(assert_all_called=False) as mock:
        mock.post(EXPO_SEND).mock(return_value=httpx.Response(503, json={"error": "unavailable"}))
        resp = await _criar_ocorrencia(client, professor, aluno, turma)
        assert resp.status_code == 201, resp.text
        ocorrencia_id = resp.json()["id"]

    # notificação interna persistida mesmo com o Expo indisponível
    notificacao = (await session.execute(
        select(Notificacao).where(Notificacao.entidade_id == uuid.UUID(ocorrencia_id))
    )).scalar_one()
    assert notificacao.destinatario_id == responsavel.id
    # nenhum ticket registrado (o envio nem chegou a ser aceito)
    tickets = (await session.execute(select(PushTicket))).scalars().all()
    assert tickets == []
    assert turma is not None and aluno is not None
