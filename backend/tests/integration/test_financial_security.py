"""Tests for Phase 1: financial security (IDOR, idempotent reversal, bracelet status)."""
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.bracelets.models import Bracelet
from app.modules.financial.models import Movimentacao, Wallet
from app.shared.enums import Perfil, StatusCarteira, StatusPulseira, TipoMovimentacao
from tests.factories import create_aluno, create_responsavel_aluno, create_usuario


async def _login_as(session, user) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"perfil": user.perfil.value})


async def _criar_wallet(session, aluno, saldo: str = "100.00") -> Wallet:
    wallet = Wallet(aluno_id=aluno.id, saldo=Decimal(saldo), status=StatusCarteira.ATIVA)
    session.add(wallet)
    await session.flush()
    return wallet


async def _consumo_mov(session, wallet: Wallet, valor: str = "20.00") -> Movimentacao:
    mov = Movimentacao(
        wallet_id=wallet.id,
        tipo=TipoMovimentacao.CONSUMO,
        valor=Decimal(valor),
        saldo_anterior=wallet.saldo,
        saldo_posterior=wallet.saldo - Decimal(valor),
        descricao="Consumo de teste",
    )
    session.add(mov)
    await session.flush()
    return mov


# ─── IDOR: responsável acessando carteira de outro aluno ───────────

@pytest.mark.asyncio
async def test_responsavel_acessa_propria_carteira(client: AsyncClient, session):
    """Responsável consulta saldo, extrato e recarrega carteira do próprio filho."""
    aluno = await create_aluno(session, nome="Filho 1")
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    await _criar_wallet(session, aluno, saldo="50.00")
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno.id}")
    assert resp_balance.status_code == 200
    assert Decimal(str(resp_balance.json()["saldo"])) == Decimal("50.00")

    resp_extrato = await client.get(f"/financial/me/statement?aluno_id={aluno.id}")
    assert resp_extrato.status_code == 200

    resp_recarga = await client.post(
        f"/financial/me/recharge?aluno_id={aluno.id}",
        json={"valor": "25.00"},
    )
    assert resp_recarga.status_code == 201
    assert Decimal(str(resp_recarga.json()["saldo_atual"])) == Decimal("75.00")


@pytest.mark.asyncio
async def test_responsavel_nao_acessa_carteira_de_outro_aluno(client: AsyncClient, session):
    """Responsável recebe 403 ao consultar/recarregar carteira de aluno não vinculado."""
    aluno_meu = await create_aluno(session, nome="Filho Meu")
    aluno_outro = await create_aluno(session, nome="Filho Alheio")
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno_meu.id, responsavel_id=resp_user.id)
    await _criar_wallet(session, aluno_meu)
    await _criar_wallet(session, aluno_outro)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp_balance = await client.get(f"/financial/me/balance?aluno_id={aluno_outro.id}")
    assert resp_balance.status_code == 403

    resp_extrato = await client.get(f"/financial/me/statement?aluno_id={aluno_outro.id}")
    assert resp_extrato.status_code == 403

    resp_recarga = await client.post(
        f"/financial/me/recharge?aluno_id={aluno_outro.id}",
        json={"valor": "10.00"},
    )
    assert resp_recarga.status_code == 403

    saldo_outro = (await session.execute(select(Wallet).where(Wallet.aluno_id == aluno_outro.id))).scalar_one()
    assert saldo_outro.saldo == Decimal("100.00")


# ─── Estorno idempotente ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_estorno_normal(client: AsyncClient, session):
    """Estorno de consumo restaura o saldo da carteira."""
    aluno = await create_aluno(session, nome="Estorno Normal")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    wallet = await _criar_wallet(session, aluno, saldo="100.00")
    consumo = await _consumo_mov(session, wallet, valor="20.00")
    wallet.saldo = Decimal("80.00")
    await session.commit()

    token = await _login_as(session, admin)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(f"/financial/consumption/{consumo.id}/refund")
    assert resp.status_code == 201
    assert Decimal(str(resp.json()["saldo_atual"])) == Decimal("100.00")

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("100.00")


@pytest.mark.asyncio
async def test_segundo_estorno_recusado(client: AsyncClient, session):
    """Segundo estorno do mesmo consumo é recusado (409)."""
    aluno = await create_aluno(session, nome="Estorno Duplo")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    wallet = await _criar_wallet(session, aluno, saldo="100.00")
    consumo = await _consumo_mov(session, wallet, valor="20.00")
    wallet.saldo = Decimal("80.00")
    await session.commit()

    token = await _login_as(session, admin)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp1 = await client.post(f"/financial/consumption/{consumo.id}/refund")
    assert resp1.status_code == 201

    resp2 = await client.post(f"/financial/consumption/{consumo.id}/refund")
    assert resp2.status_code == 409

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("100.00")

    estornos = (await session.execute(
        select(Movimentacao).where(
            Movimentacao.wallet_id == wallet.id,
            Movimentacao.tipo == TipoMovimentacao.ESTORNO,
        )
    )).scalars().all()
    assert len(estornos) == 1


@pytest.mark.asyncio
async def test_estorno_de_recarga_recusado(client: AsyncClient, session):
    """Apenas consumos podem ser estornados."""
    aluno = await create_aluno(session, nome="Estorno Recarga")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    wallet = await _criar_wallet(session, aluno, saldo="100.00")
    recarga = Movimentacao(
        wallet_id=wallet.id,
        tipo=TipoMovimentacao.RECARGA,
        valor=Decimal("50.00"),
        saldo_anterior=Decimal("0.00"),
        saldo_posterior=Decimal("50.00"),
        descricao="Recarga",
    )
    session.add(recarga)
    await session.commit()

    token = await _login_as(session, admin)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(f"/financial/consumption/{recarga.id}/refund")
    assert resp.status_code == 422


# ─── Pulseira ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consumo_pulseira_ativa(client: AsyncClient, session):
    """Pulseira ativa gera consumo normalmente."""
    aluno = await create_aluno(session, nome="Pulseira Ativa")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    wallet = await _criar_wallet(session, aluno, saldo="100.00")
    bracelet = Bracelet(uid=f"UID-{uuid.uuid4().hex[:8]}", codigo="B001", aluno_id=aluno.id, status=StatusPulseira.ATIVA)
    session.add(bracelet)
    await session.commit()

    token = await _login_as(session, admin)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/financial/consumption", json={
        "uid_pulseira": bracelet.uid,
        "valor": "15.00",
        "descricao": "Consumo com pulseira ativa",
    })
    assert resp.status_code == 201
    assert Decimal(str(resp.json()["saldo_atual"])) == Decimal("85.00")


@pytest.mark.asyncio
async def test_consumo_pulseira_bloqueada_negado(client: AsyncClient, session):
    """Pulseira bloqueada não pode debitar a carteira."""
    aluno = await create_aluno(session, nome="Pulseira Bloqueada")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    wallet = await _criar_wallet(session, aluno, saldo="100.00")
    bracelet = Bracelet(
        uid=f"UID-{uuid.uuid4().hex[:8]}", codigo="B002", aluno_id=aluno.id,
        status=StatusPulseira.BLOQUEADA,
    )
    session.add(bracelet)
    await session.commit()

    token = await _login_as(session, admin)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/financial/consumption", json={
        "uid_pulseira": bracelet.uid,
        "valor": "15.00",
    })
    assert resp.status_code in (400, 403, 422)

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("100.00")


@pytest.mark.asyncio
async def test_consumo_pulseira_cancelada_negado(client: AsyncClient, session):
    """Pulseira cancelada não pode debitar a carteira."""
    aluno = await create_aluno(session, nome="Pulseira Cancelada")
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    wallet = await _criar_wallet(session, aluno, saldo="100.00")
    bracelet = Bracelet(
        uid=f"UID-{uuid.uuid4().hex[:8]}", codigo="B003", aluno_id=aluno.id,
        status=StatusPulseira.CANCELADA,
    )
    session.add(bracelet)
    await session.commit()

    token = await _login_as(session, admin)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/financial/consumption", json={
        "uid_pulseira": bracelet.uid,
        "valor": "15.00",
    })
    assert resp.status_code in (400, 403, 422)

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("100.00")