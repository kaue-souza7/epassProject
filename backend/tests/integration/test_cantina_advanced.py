"""Tests for Cantina advanced features: config validation, scheduler, cancel, unique order."""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.modules.cantina.models import Produto, Pedido, CantinaConfig
from app.modules.financial.models import Movimentacao, Wallet
from app.shared.enums import (
    Perfil,
    StatusCarteira,
    StatusPedido,
    TipoMovimentacao,
)
from app.core.security import create_access_token
from tests.factories import create_aluno, create_usuario, create_responsavel_aluno


async def _login_as(session, user) -> str:
    token = create_access_token(subject=str(user.id), extra_claims={"perfil": user.perfil.value})
    return token


async def _setup_student_with_wallet(session, name: str = "Aluno Teste", saldo: str = "100.00"):
    aluno = await create_aluno(session, nome=name)
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = Wallet(aluno_id=aluno.id, saldo=Decimal(saldo), status=StatusCarteira.ATIVA)
    session.add(wallet)
    await session.flush()
    return aluno, resp_user, wallet


async def _create_product(session, name: str = "Sanduíche", price: str = "25.50", stock: int = 10) -> Produto:
    produto = Produto(
        nome=name, preco=Decimal(price),
        estoque_atual=stock, estoque_minimo=2, ativo=True,
    )
    session.add(produto)
    await session.flush()
    return produto


async def _get_saldo(client, aluno_id, token):
    client.headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(f"/financial/me/balance?aluno_id={aluno_id}")
    return Decimal(str(resp.json().get("saldo", "0")))


# ─── Cenário 9: Pedido duplicado no mesmo dia ──────────────────
@pytest.mark.asyncio
async def test_unique_order_per_day(client: AsyncClient, session):
    """Rejeita segundo pedido para o mesmo aluno no mesmo dia."""
    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno Duplo")
    produto = await _create_product(session, stock=10)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp1 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp1.status_code == 201

    resp2 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp2.status_code in (400, 409)


# ─── Cenário 10: Estoque insuficiente ─────────────────────────
@pytest.mark.asyncio
async def test_insufficient_stock(client: AsyncClient, session):
    """Rejeita pedido quando estoque é insuficiente."""
    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno Stock")
    produto = await _create_product(session, stock=2)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 5}],
    })
    assert resp.status_code in (400, 422)


# ─── Cenário 11: Produto inativo ──────────────────────────────
@pytest.mark.asyncio
async def test_inactive_product(client: AsyncClient, session):
    """Rejeita pedido com produto inativo."""
    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno Inativo")
    produto = await _create_product(session)
    produto.ativo = False
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code in (400, 422)


# ─── Cenário 12: Cancelamento pelo responsável ─────────────────
@pytest.mark.asyncio
async def test_cancel_by_responsible(client: AsyncClient, session):
    """Responsável pode cancelar pedido pendente."""
    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno Cancel")
    produto = await _create_product(session, stock=10)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    resp_cancel = await client.patch(f"/cantina/me/orders/{pedido_id}/cancel")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelado"


# ─── Cenário 13: Cancelamento pelo cantineiro ──────────────────
@pytest.mark.asyncio
async def test_cancel_by_cantineiro(client: AsyncClient, session):
    """Cantineiro pode cancelar pedido pendente."""
    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno CantCancel")
    produto = await _create_product(session, stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await session.commit()

    resp_token = await _login_as(session, resp_user)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_cancel = await client.patch(f"/cantina/orders/{pedido_id}/cancel")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelado"


# ─── Cenário 14: Cancelamento com estorno (APROVADO → CANCELADO) ─
@pytest.mark.asyncio
async def test_cancel_approved_with_reversal(client: AsyncClient, session):
    """Cancelamento de pedido aprovado gera estorno."""
    aluno, resp_user, wallet = await _setup_student_with_wallet(session, "Aluno Estorno")
    produto = await _create_product(session, price="30.00", stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await session.commit()

    saldo_inicial = wallet.saldo
    resp_token = await _login_as(session, resp_user)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido_id}/approve")

    saldo = await _get_saldo(client, aluno.id, resp_token)
    assert saldo == saldo_inicial - Decimal("30.00")

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_cancel = await client.patch(f"/cantina/orders/{pedido_id}/cancel")
    assert resp_cancel.json()["status"] == "cancelado"

    saldo = await _get_saldo(client, aluno.id, resp_token)
    assert saldo == saldo_inicial

    from sqlalchemy import select
    movs = await session.execute(
        select(Movimentacao).where(
            Movimentacao.wallet_id == wallet.id,
            Movimentacao.tipo == TipoMovimentacao.ESTORNO,
        )
    )
    assert len(movs.scalars().all()) == 1


# ─── Cenário 15: Reserva de estoque ───────────────────────────
@pytest.mark.asyncio
async def test_stock_reserved_not_available(client: AsyncClient, session):
    """Estoque reservado por pedido pendente não está disponível para outro pedido."""
    aluno1, resp_user1, _ = await _setup_student_with_wallet(session, "Aluno A")
    aluno2, resp_user2, _ = await _setup_student_with_wallet(session, "Aluno B")
    produto = await _create_product(session, stock=3)
    await session.commit()

    resp_token1 = await _login_as(session, resp_user1)

    client.headers = {"Authorization": f"Bearer {resp_token1}"}
    resp1 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno1.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 3}],
    })
    assert resp1.status_code == 201

    resp_token2 = await _login_as(session, resp_user2)
    client.headers = {"Authorization": f"Bearer {resp_token2}"}
    resp2 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno2.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp2.status_code in (400, 422)


# ─── Cenário 16: Estorno não afeta outro aluno ─────────────────
@pytest.mark.asyncio
async def test_reversal_does_not_affect_other(client: AsyncClient, session):
    """Estorno de um aluno não altera saldo de outro."""
    aluno1, resp_user1, wallet1 = await _setup_student_with_wallet(session, "Aluno X")
    aluno2, resp_user2, wallet2 = await _setup_student_with_wallet(session, "Aluno Y", saldo="200.00")
    produto = await _create_product(session, price="20.00", stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await session.commit()

    resp_token = await _login_as(session, resp_user1)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp1 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno1.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido1_id = resp1.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido1_id}/approve")

    resp_token2 = await _login_as(session, resp_user2)
    client.headers = {"Authorization": f"Bearer {resp_token2}"}
    resp2 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno2.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 2}],
    })
    pedido2_id = resp2.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido2_id}/approve")

    await client.patch(f"/cantina/orders/{pedido1_id}/cancel")

    saldo2 = await _get_saldo(client, aluno2.id, resp_token2)
    assert saldo2 == Decimal("160.00")


# ─── Cenário 17: Cancelamento de pedido pronto/retirado ────────
@pytest.mark.asyncio
async def test_cannot_cancel_pronto_retirado(client: AsyncClient, session):
    """Não é possível cancelar pedido já pronto ou retirado."""
    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno NoCancel")
    produto = await _create_product(session, stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await session.commit()

    resp_token = await _login_as(session, resp_user)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido_id}/approve")
    await client.patch(f"/cantina/orders/{pedido_id}/produce")
    await client.patch(f"/cantina/orders/{pedido_id}/ready")

    resp_cancel = await client.patch(f"/cantina/orders/{pedido_id}/cancel")
    assert resp_cancel.status_code in (400, 409, 422)


# ─── Cenário 18: Cancelamento respeita prazo da config ────────
@pytest.mark.asyncio
async def test_cancel_respects_config_prazo(client: AsyncClient, session):
    """Cancelamento respeita prazo_cancelamento_minutos da config."""
    from sqlalchemy import select

    aluno, resp_user, _ = await _setup_student_with_wallet(session, "Aluno Prazo")
    produto = await _create_product(session, stock=10)

    # Update the singleton config to set prazo_cancelamento_minutos=1
    result = await session.execute(select(CantinaConfig).limit(1))
    config = result.scalars().first()
    if config:
        config.prazo_cancelamento_minutos = 1
        config.prazo_pedido_minutos = None
        config.aberta = True
        config.horario_abertura = None
        config.horario_fechamento = None
        config.dias_funcionamento = None
    else:
        config = CantinaConfig(
            aberta=True,
            horario_abertura=None,
            horario_fechamento=None,
            dias_funcionamento=None,
            prazo_pedido_minutos=None,
            prazo_cancelamento_minutos=1,
        )
        session.add(config)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    pedido_id = resp.json()["id"]

    # Imediatamente → deve poder cancelar (prazo de 1 minuto)
    resp_cancel = await client.patch(f"/cantina/me/orders/{pedido_id}/cancel")
    assert resp_cancel.status_code == 200
