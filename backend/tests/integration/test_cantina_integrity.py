"""Tests for Phase 2: cantina integrity (saldo on order creation, scheduler race, programação concurrency)."""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.modules.cantina.models import CantinaConfig, Pedido, Produto
from app.modules.cantina.programacao_models import ProgramacaoCantina, ProgramacaoItem
from app.modules.cantina.repository import PedidoRepository
from app.modules.cantina.scheduler import CantinaScheduler
from app.modules.cantina.service import CantinaService
from app.modules.financial.models import Wallet
from app.shared.enums import DiaSemana, Perfil, StatusCarteira, StatusPedido, TipoProgramacao
from tests.conftest import TEST_DATABASE_URL
from tests.factories import create_aluno, create_responsavel_aluno, create_usuario


async def _login_as(session, user) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"perfil": user.perfil.value})


async def _setup(session, nome: str = "Aluno", saldo: str = "100.00"):
    aluno = await create_aluno(session, nome=nome)
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = Wallet(aluno_id=aluno.id, saldo=Decimal(saldo), status=StatusCarteira.ATIVA)
    session.add(wallet)
    await session.flush()
    return aluno, resp_user, wallet


async def _create_product(session, nome: str = "Produto", price: str = "25.50", stock: int = 10) -> Produto:
    produto = Produto(
        nome=nome, preco=Decimal(price),
        estoque_atual=stock, estoque_minimo=2, ativo=True,
    )
    session.add(produto)
    await session.flush()
    return produto


async def _config_singleton(session, prazo_pedido_minutos: int | None = 5):
    result = await session.execute(select(CantinaConfig).limit(1))
    config = result.scalars().first()
    if config is None:
        config = CantinaConfig(aberta=True)
        session.add(config)
    config.aberta = True
    config.horario_abertura = None
    config.horario_fechamento = None
    config.dias_funcionamento = None
    config.prazo_cancelamento_minutos = None
    config.prazo_pedido_minutos = prazo_pedido_minutos
    await session.flush()
    return config


# ─── Pedido sem saldo ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pedido_sem_saldo_rejeitado(client: AsyncClient, session):
    """Pedido sem saldo suficiente é rejeitado na criação (sem pedido fantasma)."""
    aluno, resp_user, wallet = await _setup(session, nome="Sem Saldo", saldo="10.00")
    produto = await _create_product(session, price="25.50", stock=10)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 422
    assert "Saldo insuficiente" in resp.json()["message"]

    pedidos = (await session.execute(select(Pedido))).scalars().all()
    assert len(pedidos) == 0

    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 10


@pytest.mark.asyncio
async def test_pedido_sem_carteira_rejeitado(client: AsyncClient, session):
    """Aluno sem carteira não pode criar pedido."""
    aluno = await create_aluno(session, nome="Sem Carteira")
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    produto = await _create_product(session)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 422
    assert len((await session.execute(select(Pedido))).scalars().all()) == 0


# ─── Scheduler × aprovação (race condition) ────────────────────────

@pytest.mark.asyncio
async def test_auto_cancel_nao_cancela_pedido_aprovado(client: AsyncClient, session, monkeypatch):
    """Auto-cancelamento não cancela pedido já aprovado nem devolve estoque."""
    aluno, resp_user, wallet = await _setup(session, nome="Race Aprovado", saldo="100.00")
    produto = await _create_product(session, price="30.00", stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_singleton(session, prazo_pedido_minutos=None)
    await session.commit()

    resp_token = await _login_as(session, resp_user)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    assert resp_approve.status_code == 200

    pedido = (await session.execute(select(Pedido).where(Pedido.id == pedido_id))).scalar_one()
    pedido.created_at = datetime.now(UTC) - timedelta(hours=2)
    config = (await session.execute(select(CantinaConfig).limit(1))).scalars().first()
    config.prazo_pedido_minutos = 5
    await session.commit()

    pedido_stale = (await session.execute(select(Pedido).where(Pedido.id == pedido_id))).scalar_one()
    assert pedido_stale.status == StatusPedido.APROVADO

    async def _stale_read(self, cutoff):
        return [pedido_stale]

    monkeypatch.setattr(PedidoRepository, "listar_pendentes_expirados", _stale_read)

    scheduler = CantinaScheduler()
    cancelados = await scheduler._cancelar_pedidos_expirados(session)
    await session.commit()

    assert cancelados == 0

    pedido = (await session.execute(select(Pedido).where(Pedido.id == pedido_id))).scalar_one()
    assert pedido.status == StatusPedido.APROVADO
    assert pedido.saldo_debitado == Decimal("30.00")
    assert pedido.movimentacao_id is not None

    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 9

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("70.00")


@pytest.mark.asyncio
async def test_auto_cancel_cancela_apenas_pendentes_expirados(client: AsyncClient, session):
    """Auto-cancelamento cancela somente pedidos pendentes expirados e devolve estoque."""
    aluno1, resp_user1, _ = await _setup(session, nome="Pendente", saldo="100.00")
    aluno2, resp_user2, _ = await _setup(session, nome="Aprovado", saldo="100.00")
    produto = await _create_product(session, price="20.00", stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_singleton(session, prazo_pedido_minutos=None)
    await session.commit()

    token1 = await _login_as(session, resp_user1)
    token2 = await _login_as(session, resp_user2)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {token1}"}
    resp1 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno1.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido1_id = resp1.json()["id"]

    client.headers = {"Authorization": f"Bearer {token2}"}
    resp2 = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno2.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 2}],
    })
    pedido2_id = resp2.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    await client.patch(f"/cantina/orders/{pedido2_id}/approve")

    pedido1 = (await session.execute(select(Pedido).where(Pedido.id == pedido1_id))).scalar_one()
    pedido1.created_at = datetime.now(UTC) - timedelta(hours=2)
    config = (await session.execute(select(CantinaConfig).limit(1))).scalars().first()
    config.prazo_pedido_minutos = 5
    await session.commit()

    scheduler = CantinaScheduler()
    cancelados = await scheduler._cancelar_pedidos_expirados(session)
    await session.commit()

    assert cancelados == 1

    p1 = (await session.execute(select(Pedido).where(Pedido.id == pedido1_id))).scalar_one()
    p2 = (await session.execute(select(Pedido).where(Pedido.id == pedido2_id))).scalar_one()
    assert p1.status == StatusPedido.CANCELADO
    assert p2.status == StatusPedido.APROVADO

    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 8  # 10 - 1 (p1) - 2 (p2) + 1 (devolução p1)


# ─── Saldo nunca negativo ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_aprovacao_nao_deixa_saldo_negativo(client: AsyncClient, session):
    """Aprovação de pedido nunca deixa saldo negativo (saldo exato funciona, excedente falha)."""
    aluno, resp_user, wallet = await _setup(session, nome="Saldo Exato", saldo="25.50")
    aluno.autonomia_cantina = True
    produto = await _create_product(session, price="25.50", stock=10)
    produto2 = await _create_product(session, nome="Outro", price="10.00", stock=10)
    cant_user = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await session.commit()

    resp_token = await _login_as(session, resp_user)
    cant_token = await _login_as(session, cant_user)

    client.headers = {"Authorization": f"Bearer {resp_token}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    assert resp_approve.status_code == 200

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("0.00")

    client.headers = {"Authorization": f"Bearer {cant_token}"}
    resp_consumo = await client.post("/cantina/consumo-direto", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto2.id), "quantidade": 1}],
    })
    assert resp_consumo.status_code == 422
    assert "Saldo insuficiente" in resp_consumo.json()["message"]

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("0.00")


# ─── Programação: duplicada / concorrência ─────────────────────────

async def _criar_programacao(session, aluno, resp_user, produto):
    prog = ProgramacaoCantina(
        aluno_id=aluno.id,
        responsavel_id=resp_user.id,
        dia_semana=DiaSemana.SEG,
        tipo=TipoProgramacao.DIARIA,
        ativo=True,
    )
    session.add(prog)
    await session.flush()
    item = ProgramacaoItem(
        programacao_id=prog.id,
        produto_id=produto.id,
        quantidade=1,
    )
    session.add(item)
    await session.flush()
    return prog


@pytest.mark.asyncio
async def test_conversao_programacao_duplicada_409(client: AsyncClient, session):
    """Converter a mesma programação duas vezes gera 409 (sem pedido duplicado)."""
    aluno, resp_user, _ = await _setup(session, nome="Prog Dupla", saldo="100.00")
    produto = await _create_product(session, price="15.00", stock=10)
    prog = await _criar_programacao(session, aluno, resp_user, produto)
    await session.commit()

    token = await _login_as(session, resp_user)
    client.headers = {"Authorization": f"Bearer {token}"}

    resp1 = await client.post(f"/cantina/programacao/{prog.id}/converter-pedido")
    assert resp1.status_code == 201

    resp2 = await client.post(f"/cantina/programacao/{prog.id}/converter-pedido")
    assert resp2.status_code == 409

    pedidos = (await session.execute(select(Pedido))).scalars().all()
    assert len(pedidos) == 1

    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 9


@pytest.mark.asyncio
async def test_conversao_programacao_concorrente_com_indice_unico(client: AsyncClient, session):
    """Conversão concorrente da mesma programação gera exatamente 1 pedido (índice único)."""
    aluno, resp_user, _ = await _setup(session, nome="Prog Concorrente", saldo="100.00")
    produto = await _create_product(session, price="15.00", stock=10)
    prog = await _criar_programacao(session, aluno, resp_user, produto)

    # O índice único uq_pedido_aluno_dia é criado pelo modelo (aluno_id,
    # data_referencia) e é a garantia de idempotência sob concorrência.
    await session.commit()

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _tentar():
        async with factory() as s:
            from app.modules.cantina.programacao_repository import ProgramacaoRepository
            prog_own = await ProgramacaoRepository(s).get_by_id(prog.id)
            service = CantinaService(s)
            try:
                await service._criar_pedido_de_programacao_manual(prog_own)
                await s.commit()
                return "ok"
            except Exception as exc:
                await s.rollback()
                return type(exc).__name__

    try:
        resultados = await asyncio.gather(_tentar(), _tentar())

        assert sorted(resultados) == ["Conflict", "ok"]

        async with factory() as s:
            pedidos = (await s.execute(select(Pedido))).scalars().all()
            assert len(pedidos) == 1
            produto_check = (await s.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
            assert produto_check.estoque_atual == 9
    finally:
        await engine.dispose()