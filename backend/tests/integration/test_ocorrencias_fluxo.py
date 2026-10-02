"""Fluxo ponta a ponta de OCORRÊNCIAS + NOTIFICAÇÕES.

Cobre: registro pelo professor com ownership, persistência, identificação do
responsável correto, notificação (in-app/realtime/push), idempotência,
resiliência a falhas de push/notificação, tokens Expo, múltiplos dispositivos,
deep-link payload e segurança/IDOR.
"""
import asyncio
import json
import uuid
from decimal import Decimal

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select

from app.core.realtime import RealtimeBroker
from app.core.security import create_access_token
from app.modules.communication.models import Notificacao, Ocorrencia, PushToken
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

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _login(user) -> str:
    return create_access_token(
        subject=str(user.id), extra_claims={"perfil": user.perfil.value},
    )


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {_login(user)}"}


async def _professor_com_turma(session, turma):
    professor = await create_usuario(session, perfil=Perfil.PROFESSOR)
    await create_professor(session, usuario_id=professor.id)
    disciplina = await create_disciplina(session)
    await create_alocacao(
        session,
        professor_id=professor.id,
        turma_id=turma.id,
        disciplina_id=disciplina.id,
    )
    return professor


async def _aluno_na_turma(session, turma, nome="Aluno"):
    aluno = await create_aluno(session, nome=nome)
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(
        session, aluno_id=aluno.id, responsavel_id=responsavel.id,
    )
    await create_matricula(
        session, aluno_id=aluno.id, turma_id=turma.id,
        status=StatusMatricula.ATIVA,
    )
    await session.flush()
    return aluno, responsavel


async def _criar_ocorrencia(client, autor, aluno, turma=None, **extra):
    client.headers = _auth(autor)
    return await client.post("/ocorrencias", json={
        "aluno_id": str(aluno.id),
        "turma_id": str(turma.id) if turma else None,
        "titulo": "Comportamento em sala",
        "descricao": "Conversa excessiva durante a aula.",
        "tipo": "comportamento",
        "severidade": "media",
        **extra,
    })


# ─── 1/3. Professor registra ocorrência válida e ela é persistida ───

@pytest.mark.asyncio
async def test_professor_registra_ocorrencia_valida_e_persiste(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, _ = await _aluno_na_turma(session, turma, "Aluno da turma")
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno, turma)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["aluno_id"] == str(aluno.id)
    assert body["criado_por"] == str(professor.id)
    assert body["status"] == "aberta"

    registrada = (await session.execute(
        select(Ocorrencia).where(Ocorrencia.id == uuid.UUID(body["id"]))
    )).scalar_one()
    assert registrada.titulo == "Comportamento em sala"
    assert registrada.aluno_id == aluno.id


@pytest.mark.asyncio
async def test_professor_registra_ocorrencia_sem_identity_map(client: AsyncClient, session):
    """Regressão: request real não possui objetos no identity map.

    Após o savepoint da notificação, relacionamentos expirados eram acessados
    pelo serializer (lazy load fora do greenlet) → MissingGreenlet. A criação
    deve funcionar mesmo com o identity map vazio.
    """
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Sem Cache")
    await session.commit()
    session.expunge_all()

    resp = await _criar_ocorrencia(client, professor, aluno, turma)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["aluno_nome"] == "Aluno Sem Cache"
    assert body["turma_codigo"] == turma.codigo

    notificacoes = (await session.execute(
        select(Notificacao).where(Notificacao.destinatario_id == responsavel.id)
    )).scalars().all()
    assert len(notificacoes) == 1


# ─── 2. Professor não registra para aluno de outra turma ────────────

@pytest.mark.asyncio
async def test_professor_nao_registra_para_aluno_de_outra_turma(client: AsyncClient, session):
    minha = await create_turma(session, codigo=f"M{uuid.uuid4().hex[:4]}")
    outra = await create_turma(session, codigo=f"O{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, minha)
    aluno_outro, _ = await _aluno_na_turma(session, outra, "Aluno de outra turma")
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno_outro, outra)
    assert resp.status_code == 403
    assert "turma" in resp.json()["message"].lower()

    # turma que não leciona, mesmo sem aluno
    client.headers = _auth(professor)
    resp_turma = await client.post("/ocorrencias", json={
        "turma_id": str(outra.id),
        "titulo": "Sem aluno",
        "descricao": "Teste de turma",
    })
    assert resp_turma.status_code == 403

    # nada persistido
    total = len((await session.execute(select(Ocorrencia))).scalars().all())
    assert total == 0


# ─── 4/5/6. Responsável correto + notificação criada ────────────────

@pytest.mark.asyncio
async def test_responsavel_correto_recebe_notificacao(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Notificado")
    # responsável de outro aluno (não deve receber)
    outro_aluno, outro_responsavel = await _aluno_na_turma(session, turma, "Aluno Outro")
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno, turma)
    assert resp.status_code == 201, resp.text
    ocorrencia_id = uuid.UUID(resp.json()["id"])

    notificacoes = (await session.execute(
        select(Notificacao).where(
            Notificacao.entidade_tipo == "ocorrencia",
            Notificacao.entidade_id == ocorrencia_id,
        )
    )).scalars().all()
    assert len(notificacoes) == 1
    notificacao = notificacoes[0]
    assert notificacao.destinatario_id == responsavel.id
    assert notificacao.destinatario_id != outro_responsavel.id
    assert notificacao.titulo == "Nova ocorrência"
    from app.shared.enums import TipoNotificacao

    assert notificacao.tipo == TipoNotificacao.OCORRENCIA
    assert "Aluno Notificado" in notificacao.mensagem
    assert (notificacao.dados or {}).get("ocorrencia_id") == str(ocorrencia_id)
    assert (notificacao.dados or {}).get("aluno_id") == str(aluno.id)
    # payload não deve conter descrição detalhada (dado sensível)
    assert "Conversa excessiva" not in json.dumps(notificacao.dados or {})
    assert outro_aluno is not None


# ─── 7. Não duplica em retry (idempotência por evento) ──────────────

@pytest.mark.asyncio
async def test_notificacao_nao_duplica_em_retry(client: AsyncClient, session):
    from app.modules.communication.service import OcorrenciaService

    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Retry")
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno, turma)
    assert resp.status_code == 201
    ocorrencia = (await session.execute(
        select(Ocorrencia).where(Ocorrencia.id == uuid.UUID(resp.json()["id"]))
    )).scalar_one()

    service = OcorrenciaService(session)
    await service._notificar_responsaveis(ocorrencia)
    await service._notificar_responsaveis(ocorrencia)

    notificacoes = (await session.execute(
        select(Notificacao).where(Notificacao.destinatario_id == responsavel.id)
    )).scalars().all()
    assert len(notificacoes) == 1


# ─── 8. Falha no push não remove a ocorrência ───────────────────────

@pytest.mark.asyncio
async def test_falha_no_push_nao_remove_ocorrencia(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Push Falha")
    await session.commit()

    client.headers = _auth(responsavel)
    assert (await client.post("/notificacoes/push-tokens", json={
        "token": "ExponentPushToken[falha-500]",
        "plataforma": "expo",
    })).status_code == 201

    client.headers = _auth(professor)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(EXPO_URL).mock(return_value=httpx.Response(500, json={"error": "boom"}))
        resp = await _criar_ocorrencia(client, professor, aluno, turma)
        assert resp.status_code == 201, resp.text
        assert mock.calls

    ocorrencia_id = uuid.UUID(resp.json()["id"])
    assert (await session.execute(
        select(Ocorrencia).where(Ocorrencia.id == ocorrencia_id)
    )).scalar_one_or_none() is not None
    notificacao = (await session.execute(
        select(Notificacao).where(Notificacao.entidade_id == ocorrencia_id)
    )).scalar_one_or_none()
    assert notificacao is not None


@pytest.mark.asyncio
async def test_falha_da_notificacao_nao_derruba_ocorrencia(
    client: AsyncClient, session, monkeypatch,
):
    """Se a criação da notificação falhar, a ocorrência continua persistida."""
    from app.core.notifications import NotificationDispatcher

    async def dispatch_quebrado(self, *args, **kwargs):
        raise RuntimeError("falha simulada de notificação")

    monkeypatch.setattr(NotificationDispatcher, "dispatch", dispatch_quebrado)

    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, _ = await _aluno_na_turma(session, turma, "Aluno Sem Notificação")
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno, turma)
    assert resp.status_code == 201, resp.text
    ocorrencia_id = uuid.UUID(resp.json()["id"])

    assert (await session.execute(
        select(Ocorrencia).where(Ocorrencia.id == ocorrencia_id)
    )).scalar_one_or_none() is not None
    notificacoes = (await session.execute(
        select(Notificacao).where(Notificacao.entidade_id == ocorrencia_id)
    )).scalars().all()
    assert notificacoes == []


# ─── 9/10/11/12/13. Push: registro, token inválido, multi-device, payload ─

@pytest.mark.asyncio
async def test_push_payload_correto_e_multi_dispositivo(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Multi Device")
    await session.commit()

    client.headers = _auth(responsavel)
    for token in ("ExponentPushToken[device-1]", "ExponentPushToken[device-2]"):
        assert (await client.post("/notificacoes/push-tokens", json={
            "token": token, "plataforma": "expo",
        })).status_code == 201

    client.headers = _auth(professor)
    with respx.mock(assert_all_called=False) as mock:
        rota = mock.post(EXPO_URL).mock(
            return_value=httpx.Response(200, json={"data": [{"status": "ok"}, {"status": "ok"}]})
        )
        resp = await _criar_ocorrencia(client, professor, aluno, turma)
        assert resp.status_code == 201
        ocorrencia_id = resp.json()["id"]
        assert rota.called
        payload = json.loads(rota.calls[0].request.content)
        # um envio por dispositivo ativo
        assert {p["to"] for p in payload} == {
            "ExponentPushToken[device-1]",
            "ExponentPushToken[device-2]",
        }
        for item in payload:
            assert item["title"] == "Nova ocorrência"
            assert "Aluno Multi Device" in item["body"]
            assert item["data"]["tipo"] == "ocorrencia"
            assert item["data"]["ocorrencia_id"] == ocorrencia_id
            assert item["data"]["entidade_tipo"] == "ocorrencia"
            assert "Conversa excessiva" not in json.dumps(item["data"])


@pytest.mark.asyncio
async def test_token_invalido_e_desativado(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Token Inválido")
    await session.commit()

    client.headers = _auth(responsavel)
    await client.post("/notificacoes/push-tokens", json={
        "token": "ExponentPushToken[invalido]", "plataforma": "expo",
    })

    client.headers = _auth(professor)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(EXPO_URL).mock(return_value=httpx.Response(200, json={
            "data": [{"status": "error", "details": {"error": "DeviceNotRegistered"}}],
        }))
        assert (await _criar_ocorrencia(client, professor, aluno, turma)).status_code == 201

    session.expire_all()
    registro = (await session.execute(
        select(PushToken).where(PushToken.token == "ExponentPushToken[invalido]")
    )).scalar_one()
    assert registro.ativo is False


# ─── 14. Realtime (Web) recebe o evento ─────────────────────────────

@pytest.mark.asyncio
async def test_realtime_publica_evento_de_ocorrencia(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Realtime")
    await session.commit()

    fila = await RealtimeBroker.subscribe(responsavel.id)
    try:
        resp = await _criar_ocorrencia(client, professor, aluno, turma)
        assert resp.status_code == 201
        ocorrencia_id = resp.json()["id"]

        evento = await asyncio.wait_for(fila.get(), timeout=2)
        assert evento["evento"] == "notificacao"
        assert evento["notificacao"]["entidade_tipo"] == "ocorrencia"
        assert evento["notificacao"]["entidade_id"] == ocorrencia_id
        assert evento["notificacao"]["dados"]["ocorrencia_id"] == ocorrencia_id
    finally:
        await RealtimeBroker.unsubscribe(responsavel.id, fila)


# ─── 15/18. Contador de não lidas ───────────────────────────────────

@pytest.mark.asyncio
async def test_contador_de_nao_lidas_apos_ocorrencia(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, responsavel = await _aluno_na_turma(session, turma, "Aluno Contador")
    await session.commit()

    client.headers = _auth(responsavel)
    assert (await client.get("/notificacoes/nao-lidas")).json()["total"] == 0

    client.headers = _auth(professor)
    assert (await _criar_ocorrencia(client, professor, aluno, turma)).status_code == 201

    client.headers = _auth(responsavel)
    assert (await client.get("/notificacoes/nao-lidas")).json()["total"] == 1

    nao_lidas = await client.get("/notificacoes", params={"apenas_nao_lidas": True})
    item = nao_lidas.json()["items"][0]
    assert item["entidade_tipo"] == "ocorrencia"
    await client.patch(f"/notificacoes/{item['id']}/ler")
    assert (await client.get("/notificacoes/nao-lidas")).json()["total"] == 0


# ─── 16. IDOR: responsável de outro aluno não acessa ────────────────

@pytest.mark.asyncio
async def test_responsavel_nao_acessa_ocorrencia_de_outro_aluno(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno_a, responsavel_a = await _aluno_na_turma(session, turma, "Aluno A")
    _, responsavel_b = await _aluno_na_turma(session, turma, "Aluno B")
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno_a, turma)
    ocorrencia_id = resp.json()["id"]

    client.headers = _auth(responsavel_a)
    assert (await client.get(f"/ocorrencias/{ocorrencia_id}")).status_code == 200

    client.headers = _auth(responsavel_b)
    assert (await client.get(f"/ocorrencias/{ocorrencia_id}")).status_code == 403
    lista_b = await client.get("/ocorrencias")
    assert all(o["id"] != ocorrencia_id for o in lista_b.json()["items"])


# ─── Token obsoleto/inativo → 401 (causa raiz do 500) ───────────────

@pytest.mark.asyncio
async def test_token_de_usuario_removido_retorna_401(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, _ = await _aluno_na_turma(session, turma, "Aluno Token Obsoleto")
    await session.commit()

    from datetime import UTC, datetime

    token = _login(professor)
    # soft delete (simula usuário removido com token ainda válido)
    from app.modules.users.models import Usuario

    usuario = (await session.execute(
        select(Usuario).where(Usuario.id == professor.id)
    )).scalar_one()
    usuario.deleted_at = datetime.now(UTC)
    await session.flush()

    client.headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/ocorrencias", json={
        "aluno_id": str(aluno.id),
        "titulo": "Deve falhar",
        "descricao": "Token sem usuário",
    })
    assert resp.status_code == 401
    assert "Sessão inválida" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_professor_inativo_nao_registra(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    aluno, _ = await _aluno_na_turma(session, turma, "Aluno Professor Inativo")
    professor.ativo = False
    await session.commit()

    resp = await _criar_ocorrencia(client, professor, aluno, turma)
    assert resp.status_code == 401
