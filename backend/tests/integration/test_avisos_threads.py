"""Testes do sistema de comunicação ponta a ponta (avisos, threads, leitura,
notificações em tempo real e push).

Cobre os 24 cenários obrigatórios do módulo, incluindo regras de destinatários
por perfil, respostas, confirmação individual de leitura, idempotência e
segurança/ownership.
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
from app.modules.communication.models import (
    Aviso,
    AvisoDestinatario,
    AvisoMensagem,
    Notificacao,
    PushToken,
)
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


def _login(user) -> str:
    return create_access_token(
        subject=str(user.id), extra_claims={"perfil": user.perfil.value},
    )


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {_login(user)}"}


async def _aluno_com_responsavel(session, nome="Aluno", turma=None):
    aluno = await create_aluno(session, nome=nome)
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(
        session, aluno_id=aluno.id, responsavel_id=responsavel.id,
    )
    if turma is not None:
        await create_matricula(
            session, aluno_id=aluno.id, turma_id=turma.id,
            status=StatusMatricula.ATIVA,
        )
    await session.flush()
    return aluno, responsavel


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


async def _criar_aviso(client, autor, payload: dict):
    client.headers = _auth(autor)
    return await client.post("/avisos", json={
        "titulo": "Aviso de teste",
        "mensagem": "Conteúdo do aviso",
        **payload,
    })


# ─── 1. Secretaria → todos os professores ──────────────────────────

@pytest.mark.asyncio
async def test_secretaria_envia_para_todos_professores(client: AsyncClient, session):
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    prof_a = await create_usuario(session, perfil=Perfil.PROFESSOR)
    prof_b = await create_usuario(session, perfil=Perfil.PROFESSOR)
    await session.commit()

    resp = await _criar_aviso(client, secretaria, {"para_professores": True})
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    destinatarios = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalars().all()
    assert {d.usuario_id for d in destinatarios} == {prof_a.id, prof_b.id}


# ─── 2. Secretaria → professores selecionados ──────────────────────

@pytest.mark.asyncio
async def test_secretaria_envia_para_professores_selecionados(client: AsyncClient, session):
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    prof_a = await create_usuario(session, perfil=Perfil.PROFESSOR)
    prof_b = await create_usuario(session, perfil=Perfil.PROFESSOR)
    await session.commit()

    resp = await _criar_aviso(client, secretaria, {"professor_ids": [str(prof_a.id)]})
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    destinatarios = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalars().all()
    assert {d.usuario_id for d in destinatarios} == {prof_a.id}
    assert prof_b.id not in {d.usuario_id for d in destinatarios}


# ─── 3. Secretaria → todos os responsáveis ─────────────────────────

@pytest.mark.asyncio
async def test_secretaria_envia_para_todos_responsaveis(client: AsyncClient, session):
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    _, resp_b = await _aluno_com_responsavel(session, "Aluno B")
    await session.commit()

    resp = await _criar_aviso(client, secretaria, {"para_responsaveis": True})
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    destinatarios = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalars().all()
    assert {d.usuario_id for d in destinatarios} == {resp_a.id, resp_b.id}


# ─── 4. Secretaria → responsáveis selecionados ─────────────────────

@pytest.mark.asyncio
async def test_secretaria_envia_para_responsaveis_selecionados(client: AsyncClient, session):
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    await _aluno_com_responsavel(session, "Aluno B")
    await session.commit()

    resp = await _criar_aviso(client, secretaria, {"responsavel_ids": [str(resp_a.id)]})
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    destinatarios = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalars().all()
    assert {d.usuario_id for d in destinatarios} == {resp_a.id}


# ─── 5. Secretaria → responsáveis por turma ────────────────────────

@pytest.mark.asyncio
async def test_secretaria_envia_para_responsaveis_da_turma(client: AsyncClient, session):
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    turma_a = await create_turma(session, codigo=f"TA{uuid.uuid4().hex[:4]}")
    turma_b = await create_turma(session, codigo=f"TB{uuid.uuid4().hex[:4]}")
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A", turma=turma_a)
    _, resp_b = await _aluno_com_responsavel(session, "Aluno B", turma=turma_b)
    await session.commit()

    resp = await _criar_aviso(client, secretaria, {"turma_ids": [str(turma_a.id)]})
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    destinatarios = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalars().all()
    assert {d.usuario_id for d in destinatarios} == {resp_a.id}
    assert resp_b.id not in {d.usuario_id for d in destinatarios}


# ─── 6/7. Professor → responsáveis da própria turma ────────────────

@pytest.mark.asyncio
async def test_professor_envia_para_responsaveis_da_sua_turma(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A", turma=turma)
    await session.commit()

    # turma inteira
    resp = await _criar_aviso(client, professor, {"turma_ids": [str(turma.id)]})
    assert resp.status_code == 201, resp.text

    # responsável específico da turma
    client.headers = _auth(professor)
    resp2 = await client.post("/avisos", json={
        "titulo": "Reunião",
        "mensagem": "Reunião amanhã às 19h.",
        "responsavel_ids": [str(resp_a.id)],
        "para_responsaveis": False,
    })
    assert resp2.status_code == 201, resp2.text


# ─── 8. Professor não pode enviar para turma alheia ────────────────

@pytest.mark.asyncio
async def test_professor_nao_envia_para_turma_alheia(client: AsyncClient, session):
    minha = await create_turma(session, codigo=f"M{uuid.uuid4().hex[:4]}")
    outra = await create_turma(session, codigo=f"O{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, minha)
    _, resp_outro = await _aluno_com_responsavel(session, "Aluno Outro", turma=outra)
    await session.commit()

    resp = await _criar_aviso(client, professor, {"turma_ids": [str(outra.id)]})
    assert resp.status_code == 403

    resp2 = await _criar_aviso(client, professor, {"responsavel_ids": [str(resp_outro.id)]})
    assert resp2.status_code == 403

    # professor não pode enviar para professores
    resp3 = await _criar_aviso(client, professor, {"para_professores": True})
    assert resp3.status_code == 403


@pytest.mark.asyncio
async def test_professor_publico_disponivel_restrito(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    outra_turma = await create_turma(session, codigo=f"X{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, turma)
    await _aluno_com_responsavel(session, "Aluno A", turma=turma)
    await _aluno_com_responsavel(session, "Aluno B", turma=outra_turma)
    await session.commit()

    client.headers = _auth(professor)
    resp = await client.get("/avisos/publico")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {t["id"] for t in body["turmas"]} == {str(turma.id)}
    assert body["professores"] == []
    assert body["pode_enviar_para_professores"] is False
    assert len(body["responsaveis"]) == 1


# ─── 9/10. Responsável recebe e não acessa aviso alheio ────────────

@pytest.mark.asyncio
async def test_responsavel_recebe_e_nao_acessa_aviso_de_outro(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    _, resp_b = await _aluno_com_responsavel(session, "Aluno B")
    await session.commit()

    resp = await _criar_aviso(client, admin, {"para_responsaveis": True})
    aviso_id = resp.json()["id"]

    # A recebe
    client.headers = _auth(resp_a)
    detalhe = await client.get(f"/avisos/{aviso_id}")
    assert detalhe.status_code == 200
    assert detalhe.json()["aviso"]["lido_por_mim"] is False
    assert detalhe.json()["destinatarios"] == []  # privacidade dos demais
    assert detalhe.json()["estatisticas"]["total"] == 2
    assert detalhe.json()["estatisticas"]["nao_lidos"] == 2

    # B também é destinatário (aviso global), então criamos um aviso só do A
    turma_a = await create_turma(session, codigo=f"A{uuid.uuid4().hex[:4]}")
    client.headers = _auth(admin)
    resp2 = await client.post("/avisos", json={
        "titulo": "Só do A",
        "mensagem": "Recado",
        "responsavel_ids": [str(resp_a.id)],
    })
    assert resp2.status_code == 201
    aviso_a = resp2.json()["id"]

    client.headers = _auth(resp_b)
    assert (await client.get(f"/avisos/{aviso_a}")).status_code == 403
    assert (await client.post(f"/avisos/{aviso_a}/ler")).status_code == 403
    assert (await client.get(f"/avisos/{aviso_a}/mensagens")).status_code == 403

    # caixa=mensagens recebidas não mostra o aviso do A
    lista = await client.get("/avisos", params={"caixa": "recebidos"})
    ids = {a["id"] for a in lista.json()["items"]}
    assert aviso_a not in ids
    assert aviso_id in ids
    assert turma_a is not None


@pytest.mark.asyncio
async def test_responsavel_nao_pode_criar_aviso(client: AsyncClient, session):
    _, responsavel = await _aluno_com_responsavel(session)
    await session.commit()
    resp = await _criar_aviso(client, responsavel, {"para_responsaveis": True})
    assert resp.status_code == 403


# ─── 11/12/13/14. Respostas ────────────────────────────────────────

@pytest.mark.asyncio
async def test_aviso_com_respostas_permite_conversa(client: AsyncClient, session):
    professor_turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor = await _professor_com_turma(session, professor_turma)
    _, responsavel = await _aluno_com_responsavel(session, "Aluno", turma=professor_turma)
    await session.commit()

    resp = await _criar_aviso(client, professor, {
        "turma_ids": [str(professor_turma.id)],
        "permite_respostas": True,
    })
    assert resp.status_code == 201, resp.text
    aviso_id = resp.json()["id"]

    client.headers = _auth(responsavel)
    detalhe = await client.get(f"/avisos/{aviso_id}")
    assert detalhe.json()["pode_responder"] is True

    msg = await client.post(f"/avisos/{aviso_id}/respostas", json={"conteudo": "Confirmado!"})
    assert msg.status_code == 201, msg.text
    assert msg.json()["autor_id"] == str(responsavel.id)
    assert msg.json()["destinatario_id"] == str(professor.id)
    assert msg.json()["enviada_por_mim"] is True

    # professor vê a mensagem e responde o responsável
    client.headers = _auth(professor)
    mensagens = await client.get(f"/avisos/{aviso_id}/mensagens")
    assert mensagens.status_code == 200
    assert [m["conteudo"] for m in mensagens.json()] == ["Confirmado!"]

    resposta_prof = await client.post(
        f"/avisos/{aviso_id}/respostas",
        json={"conteudo": "Até amanhã!", "destinatario_id": str(responsavel.id)},
    )
    assert resposta_prof.status_code == 201, resposta_prof.text
    assert resposta_prof.json()["destinatario_id"] == str(responsavel.id)

    # responsável vê a resposta e marca como lida
    client.headers = _auth(responsavel)
    mensagens = await client.get(f"/avisos/{aviso_id}/mensagens")
    assert len(mensagens.json()) == 2
    ultima = mensagens.json()[-1]
    assert ultima["lida_em"] is None
    lida = await client.patch(f"/avisos/{aviso_id}/mensagens/{ultima['id']}/ler")
    assert lida.status_code == 200
    assert lida.json()["lida_em"] is not None

    # notificação de resposta persistida para o destinatário
    notificacao = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == responsavel.id,
            Notificacao.evento_key.like(f"aviso-resposta:{ultima['id']}%"),
        )
    )).scalar_one_or_none()
    assert notificacao is not None


@pytest.mark.asyncio
async def test_aviso_sem_respostas_bloqueia_e_terceiros_nao_respondem(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    _, resp_b = await _aluno_com_responsavel(session, "Aluno B")
    await session.commit()

    resp = await _criar_aviso(client, admin, {
        "responsavel_ids": [str(resp_a.id)],
        "permite_respostas": False,
    })
    aviso_id = resp.json()["id"]

    client.headers = _auth(resp_a)
    bloqueado = await client.post(f"/avisos/{aviso_id}/respostas", json={"conteudo": "Oi"})
    assert bloqueado.status_code == 422
    assert "não permite respostas" in bloqueado.json()["message"]

    # B não participa: mesmo se o aviso permitisse, não pode responder
    client.headers = _auth(admin)
    resp2 = await client.post("/avisos", json={
        "titulo": "Com respostas",
        "mensagem": "Mensagem",
        "responsavel_ids": [str(resp_a.id)],
        "permite_respostas": True,
    })
    aviso_2 = resp2.json()["id"]

    client.headers = _auth(resp_b)
    terceiro = await client.post(f"/avisos/{aviso_2}/respostas", json={"conteudo": "Oi"})
    assert terceiro.status_code == 403


@pytest.mark.asyncio
async def test_responsavel_so_responde_ao_autor(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    outro = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    await session.commit()

    resp = await _criar_aviso(client, admin, {
        "responsavel_ids": [str(resp_a.id)],
        "permite_respostas": True,
    })
    aviso_id = resp.json()["id"]

    client.headers = _auth(resp_a)
    tentativa = await client.post(f"/avisos/{aviso_id}/respostas", json={
        "conteudo": "Oi",
        "destinatario_id": str(outro.id),
    })
    assert tentativa.status_code == 403


# ─── 15/16. Leitura individual e visão do remetente ────────────────

@pytest.mark.asyncio
async def test_leitura_individual_e_estatisticas_para_remetente(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    _, resp_b = await _aluno_com_responsavel(session, "Aluno B")
    await session.commit()

    resp = await _criar_aviso(client, admin, {"para_responsaveis": True})
    aviso_id = resp.json()["id"]

    client.headers = _auth(resp_a)
    assert (await client.post(f"/avisos/{aviso_id}/ler")).status_code == 200

    client.headers = _auth(admin)
    detalhe = await client.get(f"/avisos/{aviso_id}")
    body = detalhe.json()
    assert body["estatisticas"] == {"total": 2, "lidos": 1, "nao_lidos": 1}
    leituras = {d["usuario_id"]: d for d in body["destinatarios"]}
    assert leituras[str(resp_a.id)]["lido_em"] is not None
    assert leituras[str(resp_a.id)]["usuario_nome"]
    assert leituras[str(resp_b.id)]["lido_em"] is None

    # caixa enviados + não lidas/escalonamento
    enviados = await client.get("/avisos", params={"caixa": "enviados"})
    assert any(a["id"] == aviso_id for a in enviados.json()["items"])
    assert enviados.json()["items"][0]["lidos"] == 1
    assert enviados.json()["items"][0]["nao_lidos"] == 1


@pytest.mark.asyncio
async def test_responsavel_lista_e_marca_lido_apenas_os_seus(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, resp_a = await _aluno_com_responsavel(session, "Aluno A")
    await session.commit()

    resp = await _criar_aviso(client, admin, {"responsavel_ids": [str(resp_a.id)]})
    aviso_id = resp.json()["id"]

    client.headers = _auth(resp_a)
    lista = await client.get("/avisos", params={"caixa": "recebidos"})
    assert lista.json()["total"] == 1
    assert lista.json()["items"][0]["lido_por_mim"] is False

    await client.post(f"/avisos/{aviso_id}/ler")
    lista = await client.get("/avisos", params={"caixa": "recebidos"})
    assert lista.json()["items"][0]["lido_por_mim"] is True


# ─── 17/18. Realtime + contador de não lidas ───────────────────────

@pytest.mark.asyncio
async def test_realtime_e_contador_de_nao_lidas(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, responsavel = await _aluno_com_responsavel(session)
    await session.commit()

    fila = await RealtimeBroker.subscribe(responsavel.id)
    try:
        resp = await _criar_aviso(client, admin, {"responsavel_ids": [str(responsavel.id)]})
        assert resp.status_code == 201
        aviso_id = resp.json()["id"]

        evento = await asyncio.wait_for(fila.get(), timeout=2)
        assert evento["evento"] == "notificacao"
        assert evento["notificacao"]["titulo"] == "Novo aviso"
        assert evento["notificacao"]["entidade_id"] == aviso_id
        assert evento["notificacao"]["dados"]["aviso_id"] == aviso_id
    finally:
        await RealtimeBroker.unsubscribe(responsavel.id, fila)

    client.headers = _auth(responsavel)
    nao_lidas = await client.get("/notificacoes/nao-lidas")
    assert nao_lidas.json()["total"] == 1

    # marcar o aviso como lido também marca a notificação
    await client.post(f"/avisos/{aviso_id}/ler")
    nao_lidas = await client.get("/notificacoes/nao-lidas")
    assert nao_lidas.json()["total"] == 0


# ─── 19/20. Push (Expo) com deep link para o aviso ─────────────────

@pytest.mark.asyncio
async def test_push_enviado_com_aviso_id_e_token_invalido_desativado(
    client: AsyncClient, session,
):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, responsavel = await _aluno_com_responsavel(session)
    await session.commit()

    client.headers = _auth(responsavel)
    token_resp = await client.post("/notificacoes/push-tokens", json={
        "token": "ExponentPushToken[teste-123]",
        "plataforma": "expo",
    })
    assert token_resp.status_code == 201, token_resp.text

    client.headers = _auth(admin)
    with respx.mock(assert_all_called=False) as mock:
        rota = mock.post("https://exp.host/--/api/v2/push/send").mock(
            return_value=httpx.Response(200, json={"data": [{"status": "ok"}]})
        )
        resp = await _criar_aviso(client, admin, {"responsavel_ids": [str(responsavel.id)]})
        assert resp.status_code == 201
        aviso_id = resp.json()["id"]
        assert rota.called
        payload = json.loads(rota.calls[0].request.content)
        assert payload[0]["to"] == "ExponentPushToken[teste-123]"
        assert payload[0]["data"]["aviso_id"] == aviso_id
        assert payload[0]["data"]["entidade_tipo"] == "aviso"

    # Token inválido é desativado automaticamente
    client.headers = _auth(admin)
    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://exp.host/--/api/v2/push/send").mock(
            return_value=httpx.Response(200, json={
                "data": [{"status": "error", "details": {"error": "DeviceNotRegistered"}}],
            })
        )
        resp2 = await _criar_aviso(client, admin, {
            "titulo": "Outro aviso",
            "mensagem": "Mensagem",
            "responsavel_ids": [str(responsavel.id)],
        })
        assert resp2.status_code == 201

    session.expire_all()
    registro = (await session.execute(
        select(PushToken).where(PushToken.token == "ExponentPushToken[teste-123]")
    )).scalar_one()
    assert registro.ativo is False


# ─── 21/22/23. Idempotência e duplicidade ──────────────────────────

@pytest.mark.asyncio
async def test_nao_duplica_notificacoes_nem_destinatarios(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    _, responsavel = await _aluno_com_responsavel(session, "Aluno", turma=turma)
    await session.commit()

    # Responsável vem da turma E da seleção individual: deve aparecer 1x
    resp = await _criar_aviso(client, admin, {
        "turma_ids": [str(turma.id)],
        "responsavel_ids": [str(responsavel.id)],
    })
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    destinatarios = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalars().all()
    assert len(destinatarios) == 1

    notificacoes = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == responsavel.id,
            Notificacao.evento_key == f"aviso:{aviso_id}:{responsavel.id}",
        )
    )).scalars().all()
    assert len(notificacoes) == 1

    # Recriar a notificação com a mesma chave (retry) não duplica
    from app.modules.communication.service import NotificationService

    for _ in range(3):
        await NotificationService(session).criar(
            destinatario_id=responsavel.id,
            tipo=notificacoes[0].tipo,
            titulo="Novo aviso",
            mensagem="Retry",
            evento_key=f"aviso:{aviso_id}:{responsavel.id}",
        )
    notificacoes = (await session.execute(
        select(Notificacao).where(Notificacao.destinatario_id == responsavel.id)
    )).scalars().all()
    assert len(notificacoes) == 1


@pytest.mark.asyncio
async def test_resposta_persistida_e_notificacao_idempotente(client: AsyncClient, session):
    """Retry de resposta não perde mensagem e não duplica notificação."""
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    _, responsavel = await _aluno_com_responsavel(session)
    await session.commit()

    resp = await _criar_aviso(client, admin, {
        "responsavel_ids": [str(responsavel.id)],
        "permite_respostas": True,
    })
    aviso_id = resp.json()["id"]

    client.headers = _auth(responsavel)
    primeira = await client.post(f"/avisos/{aviso_id}/respostas", json={"conteudo": "Mensagem"})
    assert primeira.status_code == 201

    mensagens = (await session.execute(
        select(AvisoMensagem).where(AvisoMensagem.aviso_id == uuid.UUID(aviso_id))
    )).scalars().all()
    assert len(mensagens) == 1

    notificacoes = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == admin.id,
            Notificacao.entidade_id == uuid.UUID(aviso_id),
        )
    )).scalars().all()
    assert len(notificacoes) == 1


# ─── Regressão: request real não possui objetos no identity map ────

@pytest.mark.asyncio
async def test_criar_aviso_sem_objetos_no_identity_map(client: AsyncClient, session):
    """Reproduz a request real: nada em cache no identity map.

    Um lazy load fora do greenlet (ex.: `aviso.criador` após o flush) quebrava
    a request com MissingGreenlet; o serviço deve carregar relacionamentos
    explicitamente antes de usá-los.
    """
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    _, responsavel = await _aluno_com_responsavel(session)
    await session.commit()
    session.expunge_all()

    resp = await _criar_aviso(client, secretaria, {
        "responsavel_ids": [str(responsavel.id)],
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["autor_nome"] == "Test User"
    assert body["total_destinatarios"] == 1


# ─── 24. Segurança/ownership adicional ─────────────────────────────

@pytest.mark.asyncio
async def test_professor_nao_acessa_aviso_de_outro_professor(client: AsyncClient, session):
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    professor_a = await _professor_com_turma(session, turma)
    professor_b = await create_usuario(session, perfil=Perfil.PROFESSOR)
    _, responsavel = await _aluno_com_responsavel(session, "Aluno", turma=turma)
    await session.commit()

    resp = await _criar_aviso(client, professor_a, {"turma_ids": [str(turma.id)]})
    aviso_id = resp.json()["id"]

    client.headers = _auth(professor_b)
    assert (await client.get(f"/avisos/{aviso_id}")).status_code == 403
    assert (await client.post(f"/avisos/{aviso_id}/ler")).status_code == 403
    assert (await client.patch(f"/avisos/{aviso_id}/arquivar")).status_code == 403
    assert (await client.put(f"/avisos/{aviso_id}", json={"titulo": "Hack"})).status_code == 403

    # o destinatário não vê dados dos demais destinatários
    client.headers = _auth(responsavel)
    detalhe = await client.get(f"/avisos/{aviso_id}")
    assert detalhe.status_code == 200
    assert detalhe.json()["destinatarios"] == []


@pytest.mark.asyncio
async def test_secretaria_lista_enviados_recebidos_e_gerencia(client: AsyncClient, session):
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA)
    professor = await create_usuario(session, perfil=Perfil.PROFESSOR)
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()

    # secretaria envia para professor
    resp = await _criar_aviso(client, secretaria, {"professor_ids": [str(professor.id)]})
    aviso_id = resp.json()["id"]

    # professor recebe e responde
    client.headers = _auth(professor)
    await client.post(f"/avisos/{aviso_id}/ler")
    assert (await client.get("/avisos", params={"caixa": "recebidos"})).json()["total"] == 1

    # admin envia para secretaria
    client.headers = _auth(admin)
    resp2 = await client.post("/avisos", json={
        "titulo": "Para a secretaria",
        "mensagem": "Mensagem",
        "responsavel_ids": [],
        "professor_ids": [],
        "para_professores": False,
        "para_responsaveis": False,
        "destinatario_aluno_id": None,
        "destinatario_turma_id": None,
    })
    # sem público declarado → todos os responsáveis (nenhum cadastrado) → 422
    assert resp2.status_code == 422

    # secretaria vê enviados e pode arquivar
    client.headers = _auth(secretaria)
    enviados = await client.get("/avisos", params={"caixa": "enviados"})
    assert any(a["id"] == aviso_id for a in enviados.json()["items"])
    arquivado = await client.patch(f"/avisos/{aviso_id}/arquivar")
    assert arquivado.status_code == 200
    assert arquivado.json()["status"] == "arquivado"

    # aviso arquivado não aceita resposta
    client.headers = _auth(professor)
    bloqueado = await client.post(f"/avisos/{aviso_id}/respostas", json={"conteudo": "Oi"})
    assert bloqueado.status_code in (409, 422)


@pytest.mark.asyncio
async def test_busca_e_caixa_global_apenas_admin(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    coordenador = await create_usuario(session, perfil=Perfil.COORDENADOR)
    _, responsavel = await _aluno_com_responsavel(session)
    await session.commit()

    resp = await _criar_aviso(client, admin, {"responsavel_ids": [str(responsavel.id)]})
    assert resp.status_code == 201

    client.headers = _auth(admin)
    busca = await client.get("/avisos", params={"busca": "teste"})
    assert busca.json()["total"] == 1
    global_lista = await client.get("/avisos", params={"caixa": "global"})
    assert global_lista.status_code == 200

    client.headers = _auth(coordenador)
    proibido = await client.get("/avisos", params={"caixa": "global"})
    assert proibido.status_code == 403
