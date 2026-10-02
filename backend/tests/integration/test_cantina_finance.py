"""Tests for Cantina financial operations (wallet, reversal, stock)."""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.modules.financial.models import Movimentacao, Wallet
from app.modules.cantina.models import Produto, Pedido
from app.shared.enums import (
    Perfil,
    StatusCarteira,
    StatusPedido,
    TipoMovimentacao,
)
from tests.factories import (
    create_aluno,
    create_usuario,
    create_responsavel_aluno,
    PASSWORD,
)


async def _login(client: AsyncClient, session, perfil: Perfil, email: str | None = None) -> tuple[str, object]:
    email = email or f"{perfil.value}.{uuid.uuid4().hex[:8]}@test.com"
    user = await create_usuario(session, email=email, perfil=perfil)
    await session.commit()
    resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = resp.json()["access_token"]
    return token, user


async def _create_product(session, name: str = "Sanduíche", price: str = "25.50", stock: int = 10) -> Produto:
    produto = Produto(
        nome=name,
        preco=Decimal(price),
        estoque_atual=stock,
        estoque_minimo=2,
        ativo=True,
    )
    session.add(produto)
    await session.flush()
    return produto


async def _create_wallet(session, aluno_id: uuid.UUID, saldo: str = "100.00") -> Wallet:
    wallet = Wallet(
        aluno_id=aluno_id,
        saldo=Decimal(saldo),
        status=StatusCarteira.ATIVA,
    )
    session.add(wallet)
    await session.flush()
    return wallet


# ─── Cenário 1: PENDENTE → CANCELADO ────────────────────────────
@pytest.mark.asyncio
async def test_scenario1_pending_cancel(client: AsyncClient, session):
    """Saldo não muda ao rejeitar pedido pendente."""
    from app.modules.cantina.models import ItemPedido

    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)
    client.headers = {"Authorization": f"Bearer {resp_token}"}

    aluno = await create_aluno(session, nome="Cenário 1")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="25.50", stock=10)
    await session.commit()

    saldo_inicial = wallet.saldo

    # Criar pedido
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201
    pedido_id = resp.json()["id"]

    # Saldo não muda
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    assert Decimal(resp_balance.json()["saldo"]) == saldo_inicial

    # Rejeitar pedido pendente
    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_reject = await client.patch(f"/cantina/orders/{pedido_id}/reject")
    assert resp_reject.status_code == 200
    assert resp_reject.json()["status"] == "cancelado"

    # Saldo permanece o mesmo
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    assert Decimal(resp_balance.json()["saldo"]) == saldo_inicial

    # Nenhuma movimentação de estorno criada
    movs = await session.execute(
        __import__('sqlalchemy').select(Movimentacao).where(
            Movimentacao.wallet_id == wallet.id,
            Movimentacao.tipo == TipoMovimentacao.ESTORNO,
        )
    )
    assert len(movs.scalars().all()) == 0


# ─── Cenário 2: PENDENTE → APROVADO ────────────────────────────
@pytest.mark.asyncio
async def test_scenario2_pending_approved(client: AsyncClient, session):
    """Saldo debitado corretamente ao aprovar pedido."""
    from app.modules.cantina.models import ItemPedido

    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)

    aluno = await create_aluno(session, nome="Cenário 2")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="25.50", stock=10)
    await session.commit()

    saldo_inicial = wallet.saldo

    # Criar pedido
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201
    pedido_id = resp.json()["id"]

    # Aprovar pedido
    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "aprovado"
    assert Decimal(resp_approve.json()["saldo_debitado"]) == Decimal("25.50")

    # Saldo debitado
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    assert Decimal(resp_balance.json()["saldo"]) == saldo_inicial - Decimal("25.50")

    # Movimentação de consumo criada
    movs = await session.execute(
        __import__('sqlalchemy').select(Movimentacao).where(
            Movimentacao.wallet_id == wallet.id,
            Movimentacao.tipo == TipoMovimentacao.CONSUMO,
        )
    )
    movs_list = movs.scalars().all()
    assert len(movs_list) == 1
    assert movs_list[0].valor == Decimal("25.50")


# ─── Cenário 3: APROVADO → CANCELADO (estorno) ──────────────────
@pytest.mark.asyncio
async def test_scenario3_approved_cancelled(client: AsyncClient, session):
    """Saldo estornado corretamente ao rejeitar pedido aprovado."""
    from app.modules.cantina.models import ItemPedido

    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)

    aluno = await create_aluno(session, nome="Cenário 3")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="25.50", stock=10)
    await session.commit()

    saldo_inicial = wallet.saldo

    # Criar pedido
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    # Aprovar pedido
    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    assert resp_approve.json()["status"] == "aprovado"

    # Saldo após aprovação
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    saldo_pos_aprovacao = Decimal(resp_balance.json()["saldo"])
    assert saldo_pos_aprovacao == saldo_inicial - Decimal("25.50")

    # Rejeitar pedido aprovado
    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_reject = await client.patch(f"/cantina/orders/{pedido_id}/reject")
    assert resp_reject.json()["status"] == "cancelado"

    # Saldo restaurado
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    assert Decimal(resp_balance.json()["saldo"]) == saldo_inicial

    # Histórico: consumo + estorno
    movs = await session.execute(
        __import__('sqlalchemy').select(Movimentacao).where(
            Movimentacao.wallet_id == wallet.id,
        ).order_by(Movimentacao.created_at)
    )
    movs_list = movs.scalars().all()
    assert len(movs_list) == 2
    assert movs_list[0].tipo == TipoMovimentacao.CONSUMO
    assert movs_list[0].valor == Decimal("25.50")
    assert movs_list[1].tipo == TipoMovimentacao.ESTORNO
    assert movs_list[1].valor == Decimal("25.50")


# ─── Cenário 4: Duplo estorno ──────────────────────────────────
@pytest.mark.asyncio
async def test_scenario4_double_reversal(client: AsyncClient, session):
    """Segundo estorno é recusado."""
    from app.modules.cantina.models import ItemPedido
    from app.core.exceptions import Conflict

    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)

    aluno = await create_aluno(session, nome="Cenário 4")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="25.50", stock=10)
    await session.commit()

    # Criar e aprovar pedido
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido_id}/approve")

    # Rejeitar pedido aprovado
    resp_reject = await client.patch(f"/cantina/orders/{pedido_id}/reject")
    assert resp_reject.json()["status"] == "cancelado"

    # Tentar rejeitar novamente
    resp_reject2 = await client.patch(f"/cantina/orders/{pedido_id}/reject")
    assert resp_reject2.status_code == 422  # ValidationError (transição inválida)

    # Saldo permanece restaurado
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    assert Decimal(resp_balance.json()["saldo"]) == Decimal("100.00")

    # Apenas 1 estorno no histórico
    movs = await session.execute(
        __import__('sqlalchemy').select(Movimentacao).where(
            Movimentacao.wallet_id == wallet.id,
            Movimentacao.tipo == TipoMovimentacao.ESTORNO,
        )
    )
    assert len(movs.scalars().all()) == 1


# ─── Cenário 5: Múltiplos alunos ───────────────────────────────
@pytest.mark.asyncio
async def test_scenario5_multiple_students(client: AsyncClient, session):
    """Estorno afeta somente o aluno correto."""
    from app.modules.cantina.models import ItemPedido

    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)

    aluno1 = await create_aluno(session, nome="Aluno 1")
    aluno2 = await create_aluno(session, nome="Aluno 2")
    await create_responsavel_aluno(session, aluno_id=aluno1.id, responsavel_id=resp_user.id)
    await create_responsavel_aluno(session, aluno_id=aluno2.id, responsavel_id=resp_user.id)
    wallet1 = await _create_wallet(session, aluno1.id, saldo="100.00")
    wallet2 = await _create_wallet(session, aluno2.id, saldo="200.00")
    produto = await _create_product(session, price="25.50", stock=10)
    await session.commit()

    # Criar pedido para aluno1 e aprovar
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp1 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno1.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido1_id = resp1.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido1_id}/approve")

    # Criar pedido para aluno2 e aprovar
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp2 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno2.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 2}],
    })
    pedido2_id = resp2.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido2_id}/approve")

    # Saldo após aprovação
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    balance1 = await client.get(f"/financial/me/balance?aluno_id={aluno1.id}")
    balance2 = await client.get(f"/financial/me/balance?aluno_id={aluno2.id}")
    assert Decimal(balance1.json()["saldo"]) == Decimal("74.50")  # 100 - 25.50
    assert Decimal(balance2.json()["saldo"]) == Decimal("149.00")  # 200 - 51.00

    # Rejeitar pedido do aluno1
    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido1_id}/reject")

    # Saldo do aluno1 restaurado, aluno2 inalterado
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    balance1 = await client.get(f"/financial/me/balance?aluno_id={aluno1.id}")
    balance2 = await client.get(f"/financial/me/balance?aluno_id={aluno2.id}")
    assert Decimal(balance1.json()["saldo"]) == Decimal("100.00")  # Restaurado
    assert Decimal(balance2.json()["saldo"]) == Decimal("149.00")  # Inalterado


# ─── Cenário 6: movimentacao_id no response ─────────────────────
@pytest.mark.asyncio
async def test_movimentacao_id_in_response(client: AsyncClient, session):
    """Pedido aprovado retorna movimentacao_id; pendente retorna None."""
    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)

    aluno = await create_aluno(session, nome="Cenário 6")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="10.00", stock=5)
    await session.commit()

    # Criar pedido pendente
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]
    assert resp.json()["movimentacao_id"] is None

    # Aprovar pedido
    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    assert resp_approve.json()["movimentacao_id"] is not None

    # Rejeitar pedido
    resp_reject = await client.patch(f"/cantina/orders/{pedido_id}/reject")
    assert resp_reject.json()["movimentacao_id"] is not None  # Mantém referência histórica


# ─── Cenário 7: Idempotência contra duplo estorno via descrição ──
@pytest.mark.asyncio
async def test_idempotent_reversal_description(client: AsyncClient, session):
    """Movimentação de estorno contém ID do consumo original na descrição."""
    from app.modules.cantina.models import ItemPedido

    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)
    cant_token, _ = await _login(client, session, Perfil.CANTINEIRO)

    aluno = await create_aluno(session, nome="Cenário 7")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="15.00", stock=5)
    await session.commit()

    # Criar e aprovar pedido
    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    consumo_mov_id = resp_approve.json()["movimentacao_id"]

    # Rejeitar
    await client.patch(f"/cantina/orders/{pedido_id}/reject")

    # Verificar descrição do estorno contém o ID do consumo
    movs = await session.execute(
        __import__('sqlalchemy').select(Movimentacao).where(
            Movimentacao.tipo == TipoMovimentacao.ESTORNO,
        )
    )
    estorno = movs.scalars().first()
    assert estorno is not None
    assert str(consumo_mov_id) in (estorno.descricao or "")


# ─── Cenário 8: Trailing slash ─────────────────────────────────
@pytest.mark.asyncio
async def test_trailing_slash_order_detail(client: AsyncClient, session):
    """GET /cantina/me/orders/{id} funciona sem redirect 307."""
    resp_token, resp_user = await _login(client, session, Perfil.RESPONSAVEL)

    aluno = await create_aluno(session, nome="Cenário 8")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    await _create_wallet(session, aluno.id, saldo="100.00")
    produto = await _create_product(session, price="10.00", stock=5)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    # GET sem trailing slash - deve retornar 200 direto
    resp_detail = await client.get(f"/cantina/me/orders/{pedido_id}", follow_redirects=False)
    assert resp_detail.status_code == 200
