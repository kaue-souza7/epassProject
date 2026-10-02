"""Testes da Central de Avisos / Notificações e idempotência financeira.

Cobrem:
- criação de aviso com destinatários (global/aluno/turma);
- paginação e total corretos para responsável (regressão);
- leitura de aviso e autorização (IDOR);
- escalonamento de avisos não lidos com notificação à coordenação;
- idempotência de notificações por `evento_key`;
- notificações de eventos de ocorrência e cantina;
- idempotência de recarga/consumo direto e bloqueio de carteira.
"""
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.cantina.models import CantinaConfig, Pedido, Produto
from app.modules.communication.models import (
    Aviso,
    AvisoDestinatario,
    Notificacao,
    Ocorrencia,
)
from app.modules.communication.service import AvisoService, NotificationService
from app.modules.financial.models import Movimentacao, Wallet
from app.shared.enums import (
    Perfil,
    SeveridadeOcorrencia,
    StatusAviso,
    StatusCarteira,
    StatusOcorrencia,
    TipoNotificacao,
    TipoOcorrencia,
)
from tests.factories import (
    create_aluno,
    create_matricula,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)


def _login(user) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"perfil": user.perfil.value})


async def _aluno_com_responsavel(session, nome="Aluno", saldo="100.00"):
    aluno = await create_aluno(session, nome=nome)
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=responsavel.id)
    wallet = Wallet(aluno_id=aluno.id, saldo=Decimal(saldo), status=StatusCarteira.ATIVA)
    session.add(wallet)
    await session.flush()
    return aluno, responsavel, wallet


async def _config_aberta(session):
    result = await session.execute(select(CantinaConfig).limit(1))
    config = result.scalars().first()
    if config is None:
        config = CantinaConfig(aberta=True)
        session.add(config)
    config.aberta = True
    config.horario_abertura = None
    config.horario_fechamento = None
    config.dias_funcionamento = None
    config.prazo_pedido_minutos = None
    config.prazo_cancelamento_minutos = None
    config.timezone = "America/Sao_Paulo"
    await session.flush()
    return config


# ─── Avisos ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_criar_aviso_gera_leitura_notificacao_e_marca_leitura(
    client: AsyncClient, session,
):
    aluno, responsavel, _ = await _aluno_com_responsavel(session)
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/avisos", json={
        "titulo": "Reunião de pais",
        "mensagem": "Reunião na próxima sexta.",
        "tipo": "geral",
        "prioridade": "alta",
    })
    assert resp.status_code == 201, resp.text
    aviso_id = uuid.UUID(resp.json()["id"])

    leitura = (await session.execute(
        select(AvisoDestinatario).where(
            AvisoDestinatario.aviso_id == aviso_id,
            AvisoDestinatario.usuario_id == responsavel.id,
        )
    )).scalar_one_or_none()
    assert leitura is not None
    assert leitura.lido_em is None

    notificacao = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == responsavel.id,
            Notificacao.evento_key == f"aviso:{aviso_id}:{responsavel.id}",
        )
    )).scalar_one_or_none()
    assert notificacao is not None
    assert notificacao.tipo == TipoNotificacao.AVISO

    # Responsável lista e o aviso aparece com lido_por_mim=False.
    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    lista = await client.get("/avisos")
    assert lista.status_code == 200
    item = next(a for a in lista.json()["items"] if a["id"] == str(aviso_id))
    assert item["lido_por_mim"] is False
    assert lista.json()["total"] == 1

    # Marca como lido (idempotente).
    for _ in range(2):
        lido = await client.post(f"/avisos/{aviso_id}/ler")
        assert lido.status_code == 200, lido.text
        assert lido.json()["lido_em"] is not None

    lista = await client.get("/avisos")
    item = next(a for a in lista.json()["items"] if a["id"] == str(aviso_id))
    assert item["lido_por_mim"] is True


@pytest.mark.asyncio
async def test_aviso_turma_visivel_apenas_para_responsaveis_da_turma(
    client: AsyncClient, session,
):
    turma_a = await create_turma(session, codigo=f"TA{uuid.uuid4().hex[:4]}")
    turma_b = await create_turma(session, codigo=f"TB{uuid.uuid4().hex[:4]}")
    aluno_a, resp_a, _ = await _aluno_com_responsavel(session, nome="Aluno A")
    aluno_b, resp_b, _ = await _aluno_com_responsavel(session, nome="Aluno B")
    await create_matricula(session, aluno_id=aluno_a.id, turma_id=turma_a.id)
    await create_matricula(session, aluno_id=aluno_b.id, turma_id=turma_b.id)
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/avisos", json={
        "titulo": "Passeio da turma A",
        "mensagem": "Autorização necessária.",
        "destinatario_turma_id": str(turma_a.id),
    })
    assert resp.status_code == 201, resp.text
    aviso_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {_login(resp_a)}"}
    lista_a = await client.get("/avisos")
    assert any(a["id"] == aviso_id for a in lista_a.json()["items"])

    client.headers = {"Authorization": f"Bearer {_login(resp_b)}"}
    lista_b = await client.get("/avisos")
    assert not any(a["id"] == aviso_id for a in lista_b.json()["items"])

    # IDOR: responsável B não marca como lido o aviso da turma A.
    resp_idor = await client.post(f"/avisos/{aviso_id}/ler")
    assert resp_idor.status_code == 403


@pytest.mark.asyncio
async def test_paginacao_de_avisos_do_responsavel_respeita_total(
    client: AsyncClient, session,
):
    """Regressão: paginação precisa filtrar no banco (total correto)."""
    aluno, responsavel, _ = await _aluno_com_responsavel(session)
    outro_aluno, outro_responsavel, _ = await _aluno_com_responsavel(session, nome="Outro")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    for i in range(3):
        r = await client.post("/avisos", json={
            "titulo": f"Aviso global {i}",
            "mensagem": "Mensagem",
        })
        assert r.status_code == 201
    r = await client.post("/avisos", json={
        "titulo": "Aviso de outro aluno",
        "mensagem": "Mensagem",
        "destinatario_aluno_id": str(outro_aluno.id),
    })
    assert r.status_code == 201, r.text

    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    page1 = await client.get("/avisos", params={"page": 1, "size": 2})
    assert page1.status_code == 200
    body = page1.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    page2 = await client.get("/avisos", params={"page": 2, "size": 2})
    assert len(page2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_aviso_destinatario_inexistente_rejeitado(client: AsyncClient, session):
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()
    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/avisos", json={
        "titulo": "Aviso inválido",
        "mensagem": "Destinatário não existe",
        "destinatario_aluno_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_escalonamento_de_aviso_nao_lido_notifica_coordenacao(
    client: AsyncClient, session,
):
    aluno, responsavel, _ = await _aluno_com_responsavel(session)
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    coordenador = await create_usuario(session, perfil=Perfil.COORDENADOR)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/avisos", json={
        "titulo": "Aviso antigo",
        "mensagem": "Ninguém leu",
    })
    aviso_id = uuid.UUID(resp.json()["id"])

    aviso = (await session.execute(select(Aviso).where(Aviso.id == aviso_id))).scalar_one()
    aviso.publicado_em = datetime.now(UTC) - timedelta(hours=48)
    await session.flush()

    service = AvisoService(session)
    escalados = await service.escalar_nao_lidos(24)
    assert escalados == 1

    leitura = (await session.execute(
        select(AvisoDestinatario).where(AvisoDestinatario.aviso_id == aviso_id)
    )).scalar_one()
    assert leitura.escalado_em is not None

    notif_coord = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == coordenador.id,
            Notificacao.evento_key == f"aviso-escalado:{aviso_id}:{coordenador.id}",
        )
    )).scalar_one_or_none()
    assert notif_coord is not None

    # Reexecução não duplica nem re-escala.
    antes = len((await session.execute(select(Notificacao))).scalars().all())
    assert await service.escalar_nao_lidos(24) == 0
    depois = len((await session.execute(select(Notificacao))).scalars().all())
    assert antes == depois


@pytest.mark.asyncio
async def test_notificacao_idempotente_por_evento_key(session):
    usuario = await create_usuario(session)
    service = NotificationService(session)
    for _ in range(3):
        await service.criar(
            destinatario_id=usuario.id,
            tipo=TipoNotificacao.SISTEMA,
            titulo="Teste",
            mensagem="Mensagem",
            evento_key="evento-unico-123",
        )
    notificacoes = (await session.execute(
        select(Notificacao).where(Notificacao.destinatario_id == usuario.id)
    )).scalars().all()
    assert len(notificacoes) == 1


# ─── Ocorrências ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ocorrencia_status_notifica_responsavel(client: AsyncClient, session):
    aluno, responsavel, _ = await _aluno_com_responsavel(session)
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/ocorrencias", json={
        "aluno_id": str(aluno.id),
        "responsavel_id": str(responsavel.id),
        "titulo": "Comportamento em sala",
        "descricao": "Conversa excessiva durante a aula.",
        "tipo": TipoOcorrencia.COMPORTAMENTO.value,
        "severidade": SeveridadeOcorrencia.MEDIA.value,
    })
    assert resp.status_code == 201, resp.text
    ocorrencia_id = resp.json()["id"]

    resp_status = await client.patch(f"/ocorrencias/{ocorrencia_id}/status", json={
        "status": StatusOcorrencia.EM_ANDAMENTO.value,
        "observacao": "Encaminhado à coordenação",
    })
    assert resp_status.status_code == 200, resp_status.text

    evento = f"ocorrencia:{ocorrencia_id}:status:em_andamento:{responsavel.id}"
    notif = (await session.execute(
        select(Notificacao).where(Notificacao.evento_key == evento)
    )).scalar_one_or_none()
    assert notif is not None
    assert notif.destinatario_id == responsavel.id
    assert notif.tipo == TipoNotificacao.OCORRENCIA

    ocorrencia = (await session.execute(
        select(Ocorrencia).where(Ocorrencia.id == uuid.UUID(ocorrencia_id))
    )).scalar_one()
    assert ocorrencia.status == StatusOcorrencia.EM_ANDAMENTO


@pytest.mark.asyncio
async def test_ocorrencia_sem_responsavel_notifica_vinculados(client: AsyncClient, session):
    """Sem responsável explícito, todos os vinculados ao aluno são notificados."""
    aluno, responsavel, _ = await _aluno_com_responsavel(session)
    outro = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=outro.id)
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/ocorrencias", json={
        "aluno_id": str(aluno.id),
        "titulo": "Baixo rendimento",
        "descricao": "Notas em queda no bimestre.",
    })
    assert resp.status_code == 201, resp.text
    ocorrencia_id = resp.json()["id"]

    evento = f"ocorrencia:{ocorrencia_id}:criada"
    notificacoes = (await session.execute(
        select(Notificacao).where(Notificacao.evento_key.like(f"{evento}%"))
    )).scalars().all()
    destinatarios = {n.destinatario_id for n in notificacoes}
    assert destinatarios == {responsavel.id, outro.id}


# ─── Cantina: notificações e idempotência ──────────────────────────

@pytest.mark.asyncio
async def test_fluxo_cantina_notifica_staff_e_responsavel(client: AsyncClient, session):
    aluno, responsavel, _ = await _aluno_com_responsavel(session)
    produto = Produto(
        nome="Salgado", preco=Decimal("10.00"),
        estoque_atual=10, estoque_minimo=1, ativo=True,
    )
    cantineiro = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    session.add(produto)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201, resp.text
    pedido_id = resp.json()["id"]

    notif_staff = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == cantineiro.id,
            Notificacao.evento_key == f"pedido-criado:{pedido_id}:{cantineiro.id}",
        )
    )).scalar_one_or_none()
    assert notif_staff is not None

    client.headers = {"Authorization": f"Bearer {_login(cantineiro)}"}
    assert (await client.patch(f"/cantina/orders/{pedido_id}/approve")).status_code == 200

    notif_aprovado = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == responsavel.id,
            Notificacao.evento_key == f"pedido-aprovado:{pedido_id}",
        )
    )).scalar_one_or_none()
    assert notif_aprovado is not None

    assert (await client.patch(f"/cantina/orders/{pedido_id}/produce")).status_code == 200
    assert (await client.patch(f"/cantina/orders/{pedido_id}/ready")).status_code == 200

    notif_pronto = (await session.execute(
        select(Notificacao).where(
            Notificacao.destinatario_id == responsavel.id,
            Notificacao.evento_key == f"pedido-pronto:{pedido_id}",
        )
    )).scalar_one_or_none()
    assert notif_pronto is not None


@pytest.mark.asyncio
async def test_auto_cancelamento_notifica_responsavel(client: AsyncClient, session):
    from app.modules.cantina.scheduler import CantinaScheduler

    aluno, responsavel, _ = await _aluno_com_responsavel(session, saldo="100.00")
    produto = Produto(
        nome="Torta", preco=Decimal("12.00"),
        estoque_atual=10, estoque_minimo=1, ativo=True,
    )
    session.add(produto)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201, resp.text
    pedido_id = resp.json()["id"]

    pedido = (await session.execute(
        select(Pedido).where(Pedido.id == uuid.UUID(pedido_id))
    )).scalar_one()
    pedido.created_at = datetime.now(UTC) - timedelta(hours=2)
    config = (await session.execute(select(CantinaConfig).limit(1))).scalars().first()
    config.prazo_pedido_minutos = 5
    await session.flush()

    scheduler = CantinaScheduler()
    cancelados = await scheduler._cancelar_pedidos_expirados(session)
    assert cancelados == 1

    notif = (await session.execute(
        select(Notificacao).where(
            Notificacao.evento_key == f"pedido-cancelado-auto:{pedido_id}"
        )
    )).scalar_one_or_none()
    assert notif is not None
    assert notif.destinatario_id == responsavel.id

    pedido = (await session.execute(
        select(Pedido).where(Pedido.id == uuid.UUID(pedido_id))
    )).scalar_one()
    assert pedido.status.value == "cancelado"


@pytest.mark.asyncio
async def test_consumo_direto_idempotente(client: AsyncClient, session):
    aluno, _, wallet = await _aluno_com_responsavel(session, saldo="100.00")
    aluno.autonomia_cantina = True
    wallet_id = wallet.id
    produto = Produto(
        nome="Suco", preco=Decimal("8.00"),
        estoque_atual=10, estoque_minimo=1, ativo=True,
    )
    cantineiro = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    session.add(produto)
    await _config_aberta(session)
    produto_id = produto.id
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(cantineiro)}"}
    payload = {
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto_id), "quantidade": 2}],
        "idempotency_key": "consumo-direto-001",
    }
    r1 = await client.post("/cantina/consumo-direto", json=payload)
    assert r1.status_code == 201, r1.text
    r2 = await client.post("/cantina/consumo-direto", json=payload)
    assert r2.status_code == 201, r2.text
    assert r1.json()["movimentacao_id"] == r2.json()["movimentacao_id"]
    assert r1.json()["consumo_id"] == r2.json()["consumo_id"]

    session.expire_all()
    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet_id))).scalar_one()
    assert wallet.saldo == Decimal("84.00")  # debitado uma única vez (16.00)

    produto = (await session.execute(
        select(Produto).where(Produto.id == produto_id)
    )).scalar_one()
    assert produto.estoque_atual == 8  # baixa única

    pedidos = (await session.execute(select(Pedido))).scalars().all()
    assert len(pedidos) == 1


@pytest.mark.asyncio
async def test_recarga_idempotente(client: AsyncClient, session):
    aluno, responsavel, wallet = await _aluno_com_responsavel(session, saldo="10.00")
    wallet_id = wallet.id
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    payload = {"valor": "30.00", "idempotency_key": "recarga-abc"}
    r1 = await client.post(
        "/financial/me/recharge", params={"aluno_id": str(aluno.id)}, json=payload,
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        "/financial/me/recharge", params={"aluno_id": str(aluno.id)}, json=payload,
    )
    assert r2.status_code == 201, r2.text
    assert r1.json()["movimentacao_id"] == r2.json()["movimentacao_id"]

    session.expire_all()
    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet_id))).scalar_one()
    assert wallet.saldo == Decimal("40.00")  # creditado uma única vez

    recargas = (await session.execute(
        select(Movimentacao).where(Movimentacao.wallet_id == wallet_id)
    )).scalars().all()
    assert len(recargas) == 1


@pytest.mark.asyncio
async def test_recarga_sem_carteira_cria_carteira(client: AsyncClient, session):
    """Responsável recarrega aluno sem carteira: carteira é criada automaticamente."""
    aluno = await create_aluno(session, nome="Sem Carteira")
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=responsavel.id)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    resp = await client.post(
        "/financial/me/recharge",
        params={"aluno_id": str(aluno.id)},
        json={"valor": "25.00"},
    )
    assert resp.status_code == 201, resp.text
    assert Decimal(str(resp.json()["saldo_atual"])) == Decimal("25.00")


@pytest.mark.asyncio
async def test_extrato_retorna_total_e_paginas(client: AsyncClient, session):
    aluno, responsavel, _ = await _aluno_com_responsavel(session, saldo="10.00")
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(responsavel)}"}
    for i in range(3):
        r = await client.post(
            "/financial/me/recharge",
            params={"aluno_id": str(aluno.id)},
            json={"valor": "5.00", "idempotency_key": f"extrato-{i}"},
        )
        assert r.status_code == 201

    resp = await client.get(
        "/financial/me/statement",
        params={"aluno_id": str(aluno.id), "page": 1, "size": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["page"] == 1
    assert len(body["movimentacoes"]) == 2


@pytest.mark.asyncio
async def test_bloqueio_desbloqueio_carteira(client: AsyncClient, session):
    aluno, _, wallet = await _aluno_com_responsavel(session, saldo="50.00")
    aluno.autonomia_cantina = True
    produto = Produto(
        nome="Bolo", preco=Decimal("10.00"),
        estoque_atual=5, estoque_minimo=1, ativo=True,
    )
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    session.add(produto)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}

    block = await client.patch(f"/financial/wallets/{wallet.id}/block")
    assert block.status_code == 200, block.text
    assert block.json()["status"] == "bloqueada"

    # Bloqueio repetido é idempotente.
    assert (await client.patch(f"/financial/wallets/{wallet.id}/block")).status_code == 200

    resp_consumo = await client.post("/cantina/consumo-direto", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp_consumo.status_code == 403

    unblock = await client.patch(f"/financial/wallets/{wallet.id}/unblock")
    assert unblock.status_code == 200
    assert unblock.json()["status"] == "ativa"


@pytest.mark.asyncio
async def test_consumo_pulseira_aluno_inativo_negado(client: AsyncClient, session):
    from app.modules.bracelets.models import Bracelet
    from app.shared.enums import StatusPulseira

    aluno = await create_aluno(session, nome="Inativo")
    aluno.ativo = False
    wallet = Wallet(aluno_id=aluno.id, saldo=Decimal("50.00"), status=StatusCarteira.ATIVA)
    bracelet = Bracelet(
        uid=f"UID-{uuid.uuid4().hex[:8]}", codigo="B900",
        aluno_id=aluno.id, status=StatusPulseira.ATIVA,
    )
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    session.add_all([wallet, bracelet])
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.post("/financial/consumption", json={
        "uid_pulseira": bracelet.uid,
        "valor": "10.00",
    })
    assert resp.status_code == 422
    assert "inativo" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_estorno_duplicado_negado_pela_api(client: AsyncClient, session):
    """Dois POSTs de estorno do mesmo consumo: um 201, outro 409."""
    from app.modules.financial.models import Movimentacao
    from app.shared.enums import TipoMovimentacao

    aluno, _, wallet = await _aluno_com_responsavel(session, saldo="80.00")
    consumo = Movimentacao(
        wallet_id=wallet.id,
        tipo=TipoMovimentacao.CONSUMO,
        valor=Decimal("20.00"),
        saldo_anterior=Decimal("100.00"),
        saldo_posterior=Decimal("80.00"),
        descricao="Consumo",
    )
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    session.add(consumo)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    r1 = await client.post(f"/financial/consumption/{consumo.id}/refund")
    assert r1.status_code == 201, r1.text
    r2 = await client.post(f"/financial/consumption/{consumo.id}/refund")
    assert r2.status_code == 409
