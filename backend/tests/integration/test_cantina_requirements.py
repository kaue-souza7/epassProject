"""Testes dos requisitos funcionais da Cantina (fase de hardening).

Cobrem: consumo direto com pedido no mesmo dia, estorno concorrente,
produto vencido, aluno inativo, movimentações de estoque, programação
GERAL + DIÁRIA, alertas de perecíveis e IDOR de carteira/pedidos.
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.modules.cantina.models import (
    CantinaConfig,
    MovimentacaoEstoque,
    Pedido,
    Produto,
)
from app.modules.cantina.programacao_models import ProgramacaoCantina, ProgramacaoItem
from app.modules.cantina.scheduler import CantinaScheduler
from app.modules.cantina.service import CantinaService
from app.modules.cantina.utils import agora_local
from app.modules.financial.models import Movimentacao, Wallet
from app.shared.enums import (
    DiaSemana,
    OrigemPedido,
    Perfil,
    StatusCarteira,
    StatusPedido,
    TipoMovimentacao,
    TipoMovimentacaoEstoque,
    TipoProgramacao,
)
from tests.conftest import TEST_DATABASE_URL
from tests.factories import (
    create_aluno,
    create_matricula,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)

_DIAS = [
    DiaSemana.SEG,
    DiaSemana.TER,
    DiaSemana.QUA,
    DiaSemana.QUI,
    DiaSemana.SEX,
    DiaSemana.SAB,
]


def _dia_semana_hoje() -> DiaSemana | None:
    weekday = agora_local(None).weekday()
    if weekday > 5:
        return None
    return _DIAS[weekday]


def _login(user) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"perfil": user.perfil.value})


async def _setup_aluno(session, nome="Aluno", saldo="100.00", autonomia=False, ativo=True):
    aluno = await create_aluno(session, nome=nome)
    aluno.ativo = ativo
    aluno.autonomia_cantina = autonomia
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=resp_user.id)
    wallet = Wallet(aluno_id=aluno.id, saldo=Decimal(saldo), status=StatusCarteira.ATIVA)
    session.add(wallet)
    await session.flush()
    return aluno, resp_user, wallet


async def _produto(session, nome="Produto", preco="10.00", estoque=10, **kwargs) -> Produto:
    produto = Produto(
        nome=nome,
        preco=Decimal(preco),
        estoque_atual=estoque,
        estoque_minimo=2,
        ativo=kwargs.pop("ativo", True),
        **kwargs,
    )
    session.add(produto)
    await session.flush()
    return produto


async def _config_aberta(session, **kwargs):
    result = await session.execute(select(CantinaConfig).limit(1))
    config = result.scalars().first()
    if config is None:
        config = CantinaConfig(aberta=True)
        session.add(config)
    config.aberta = True
    config.horario_abertura = None
    config.horario_fechamento = None
    config.dias_funcionamento = None
    config.prazo_pedido_minutos = kwargs.pop("prazo_pedido_minutos", None)
    config.prazo_cancelamento_minutos = None
    config.timezone = kwargs.pop("timezone", "America/Sao_Paulo")
    for field, value in kwargs.items():
        setattr(config, field, value)
    await session.flush()
    return config


# ─── Consumo direto × pedido agendado ──────────────────────────────

@pytest.mark.asyncio
async def test_consumo_direto_permitido_com_pedido_no_mesmo_dia(client: AsyncClient, session):
    """Aluno com autonomia pode consumir no balcão mesmo tendo pedido agendado."""
    aluno, resp_user, wallet = await _setup_aluno(session, autonomia=True)
    wallet_id = wallet.id
    produto = await _produto(session, preco="10.00", estoque=10)
    produto_id = produto.id
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 201

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp_consumo = await client.post("/cantina/consumo-direto", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 2}],
    })
    assert resp_consumo.status_code == 201, resp_consumo.text

    pedidos = (await session.execute(select(Pedido))).scalars().all()
    origens = sorted(p.origem.value for p in pedidos)
    assert origens == ["consumo_direto", "responsavel"]

    session.expire_all()
    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet_id))).scalar_one()
    assert wallet.saldo == Decimal("80.00")  # 100 - 20 (consumo direto de 2 unidades)
    produto = (await session.execute(select(Produto).where(Produto.id == produto_id))).scalar_one()
    assert produto.estoque_atual == 7  # 10 - 1 - 2


# ─── Estorno concorrente ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_estorno_concorrente_apenas_um(client: AsyncClient, session):
    """Dois estornos concorrentes do mesmo consumo: apenas um é aplicado."""
    aluno, resp_user, wallet = await _setup_aluno(session, saldo="100.00")
    wallet_id = wallet.id
    produto = await _produto(session, preco="25.00", estoque=5)
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp_approve = await client.patch(f"/cantina/orders/{pedido_id}/approve")
    consumo_id = uuid.UUID(resp_approve.json()["movimentacao_id"])
    await session.commit()

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _estornar():
        async with factory() as s:
            service = CantinaService(s)
            try:
                await service._financial_service.realizar_estorno_cantina(
                    consumo_id=consumo_id,
                    usuario_id=cant.id,
                )
                await s.commit()
                return "ok"
            except Exception as exc:
                await s.rollback()
                return type(exc).__name__

    resultados = await asyncio.gather(_estornar(), _estornar())
    assert sorted(resultados) == ["Conflict", "ok"], resultados

    session.expire_all()
    movs = (await session.execute(
        select(Movimentacao).where(
            Movimentacao.tipo == TipoMovimentacao.ESTORNO,
            Movimentacao.consumo_original_id == consumo_id,
        )
    )).scalars().all()
    assert len(movs) == 1

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet_id))).scalar_one()
    assert wallet.saldo == Decimal("100.00")  # estorno aplicado exatamente uma vez

    await engine.dispose()


# ─── Produto vencido ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_produto_vencido_indisponivel_e_rejeitado(client: AsyncClient, session):
    """Produto perecível vencido fica indisponível e não pode ser pedido."""
    aluno, resp_user, _ = await _setup_aluno(session)
    vencido = await _produto(
        session,
        nome="Iogurte",
        preco="5.00",
        estoque=10,
        perecivel=True,
        data_validade=datetime.now(UTC) - timedelta(days=2),
    )
    await _config_aberta(session)
    await session.commit()

    menu = await client.get("/cantina/menu")
    assert menu.status_code == 200
    item = next(i for i in menu.json()["itens"] if i["id"] == str(vencido.id))
    assert item["disponivel"] is False

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(vencido.id), "quantidade": 1}],
    })
    assert resp.status_code == 422
    assert "vencido" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_dashboard_alerta_perecivel_vencido(client: AsyncClient, session):
    """Dashboard reporta produto perecível vencido."""
    vencido = await _produto(
        session,
        nome="Bolo",
        perecivel=True,
        data_validade=datetime.now(UTC) - timedelta(days=1),
    )
    admin = await create_usuario(session, perfil=Perfil.ADMIN)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(admin)}"}
    resp = await client.get("/cantina/dashboard")
    assert resp.status_code == 200
    alertas = resp.json()["alertas_estoque"]
    assert any(
        a["produto_id"] == str(vencido.id) and a["tipo"] == "perecivel_vencido"
        for a in alertas
    )


# ─── Aluno inativo ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aluno_inativo_nao_pode_pedir_nem_consumir(client: AsyncClient, session):
    aluno, resp_user, _ = await _setup_aluno(session, ativo=False, autonomia=True)
    produto = await _produto(session)
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 422
    assert "inativo" in resp.json()["message"].lower()

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp2 = await client.post("/cantina/consumo-direto", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_consumo_direto_sem_autonomia_negado(client: AsyncClient, session):
    aluno, _, _ = await _setup_aluno(session, autonomia=False)
    produto = await _produto(session)
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp = await client.post("/cantina/consumo-direto", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 403


# ─── Movimentações de estoque em vendas ────────────────────────────

@pytest.mark.asyncio
async def test_movimentacoes_estoque_registradas_em_venda_e_cancelamento(
    client: AsyncClient, session,
):
    aluno, resp_user, _ = await _setup_aluno(session)
    produto = await _produto(session, estoque=10)
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 3}],
    })
    pedido_id = resp.json()["id"]

    movs = (await session.execute(
        select(MovimentacaoEstoque).where(MovimentacaoEstoque.produto_id == produto.id)
    )).scalars().all()
    assert len(movs) == 1
    assert movs[0].tipo == TipoMovimentacaoEstoque.SAIDA
    assert movs[0].quantidade == 3
    assert movs[0].estoque_atual == 7

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp_cancel = await client.patch(f"/cantina/orders/{pedido_id}/reject")
    assert resp_cancel.status_code == 200

    movs = (await session.execute(
        select(MovimentacaoEstoque).where(MovimentacaoEstoque.produto_id == produto.id)
        .order_by(MovimentacaoEstoque.created_at)
    )).scalars().all()
    assert len(movs) == 2
    assert movs[1].tipo == TipoMovimentacaoEstoque.ENTRADA
    assert movs[1].quantidade == 3
    assert movs[1].estoque_atual == 10

    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 10


# ─── Programação GERAL × DIÁRIA ────────────────────────────────────

@pytest.mark.asyncio
async def test_programacao_geral_e_diaria_coexistem(client: AsyncClient, session):
    """GERAL e DIÁRIA podem coexistir; DIÁRIA tem prioridade no seu dia."""
    dia = _dia_semana_hoje()
    if dia is None:
        pytest.skip("Domingo: scheduler não processa")

    aluno, resp_user, _ = await _setup_aluno(session, saldo="200.00")
    produto_geral = await _produto(session, nome="Geral", preco="5.00", estoque=10)
    produto_diaria = await _produto(session, nome="Diaria", preco="7.00", estoque=10)
    await _config_aberta(session)

    geral = ProgramacaoCantina(
        aluno_id=aluno.id, responsavel_id=resp_user.id,
        dia_semana=DiaSemana.SEG, tipo=TipoProgramacao.GERAL, ativo=True,
    )
    diaria = ProgramacaoCantina(
        aluno_id=aluno.id, responsavel_id=resp_user.id,
        dia_semana=dia, tipo=TipoProgramacao.DIARIA, ativo=True,
    )
    session.add_all([geral, diaria])
    await session.flush()
    session.add_all([
        ProgramacaoItem(programacao_id=geral.id, produto_id=produto_geral.id, quantidade=1),
        ProgramacaoItem(programacao_id=diaria.id, produto_id=produto_diaria.id, quantidade=1),
    ])
    await session.commit()

    scheduler = CantinaScheduler()
    processados = await scheduler._processar_programacoes(session)
    await session.commit()
    assert processados == 1

    pedido = (await session.execute(select(Pedido))).scalar_one()
    assert pedido.origem == OrigemPedido.PROGRAMACAO
    itens = pedido.itens
    assert [i.produto_id for i in itens] == [produto_diaria.id]

    # Executar novamente não duplica o pedido do dia.
    processados = await scheduler._processar_programacoes(session)
    await session.commit()
    assert processados == 0
    assert len((await session.execute(select(Pedido))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_programacao_geral_aplica_a_outros_dias(client: AsyncClient, session):
    """GERAL gera pedido em dias sem DIÁRIA específica."""
    dia = _dia_semana_hoje()
    if dia is None:
        pytest.skip("Domingo: scheduler não processa")

    outro_dia = next(d for d in _DIAS if d != dia)
    aluno, resp_user, _ = await _setup_aluno(session, saldo="200.00")
    produto = await _produto(session, preco="5.00", estoque=10)
    await _config_aberta(session)

    geral = ProgramacaoCantina(
        aluno_id=aluno.id, responsavel_id=resp_user.id,
        dia_semana=outro_dia, tipo=TipoProgramacao.GERAL, ativo=True,
    )
    session.add(geral)
    await session.flush()
    session.add(ProgramacaoItem(
        programacao_id=geral.id, produto_id=produto.id, quantidade=1,
    ))
    await session.commit()

    scheduler = CantinaScheduler()
    processados = await scheduler._processar_programacoes(session)
    await session.commit()
    assert processados == 1
    assert len((await session.execute(select(Pedido))).scalars().all()) == 1


# ─── IDOR ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_responsavel_nao_acessa_aluno_nao_vinculado(client: AsyncClient, session):
    """Responsável não consegue pedir/consultar aluno sem vínculo."""
    resp_user = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    aluno_alheio = await create_aluno(session, nome="Alheio")
    produto = await _produto(session)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}

    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno_alheio.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 403

    resp_today = await client.get(f"/cantina/me/orders/today?aluno_id={aluno_alheio.id}")
    assert resp_today.status_code == 403

    resp_hist = await client.get(f"/cantina/me/orders?aluno_id={aluno_alheio.id}")
    assert resp_hist.status_code == 403


# ─── Fluxo completo do Kanban ──────────────────────────────────────

@pytest.mark.asyncio
async def test_fluxo_completo_pedido(client: AsyncClient, session):
    """PENDENTE → APROVADO → PRODUÇÃO → PRONTO → RETIRADO, com histórico."""
    aluno, resp_user, wallet = await _setup_aluno(session, saldo="100.00")
    produto = await _produto(session, preco="20.00", estoque=5)
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    pedido_id = resp.json()["id"]

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    for acao, status in [
        ("approve", "aprovado"),
        ("produce", "em_producao"),
        ("ready", "pronto"),
        ("delivered", "retirado"),
    ]:
        r = await client.patch(f"/cantina/orders/{pedido_id}/{acao}")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == status

    # Transição inválida após RETIRADO
    r = await client.patch(f"/cantina/orders/{pedido_id}/cancel")
    assert r.status_code == 422

    # Histórico registra quem executou
    r = await client.get(f"/cantina/orders/{pedido_id}/history")
    assert r.status_code == 200
    historico = r.json()
    assert [h["status_novo"] for h in historico] == [
        "pendente", "aprovado", "em_producao", "pronto", "retirado",
    ]
    assert all(h["usuario_id"] for h in historico if h["status_novo"] != "pendente" or True)
    assert all(h["usuario_nome"] for h in historico)

    wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet.id))).scalar_one()
    assert wallet.saldo == Decimal("80.00")
    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 4


@pytest.mark.asyncio
async def test_saldo_insuficiente_nao_baixa_estoque_nem_cria_pedido(client: AsyncClient, session):
    aluno, resp_user, _ = await _setup_aluno(session, saldo="5.00")
    produto = await _produto(session, preco="20.00", estoque=10)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    resp = await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })
    assert resp.status_code == 422
    assert "saldo insuficiente" in resp.json()["message"].lower()

    produto = (await session.execute(select(Produto).where(Produto.id == produto.id))).scalar_one()
    assert produto.estoque_atual == 10
    assert len((await session.execute(select(Pedido))).scalars().all()) == 0
    movs = (await session.execute(
        select(MovimentacaoEstoque).where(MovimentacaoEstoque.produto_id == produto.id)
    )).scalars().all()
    assert len(movs) == 0


@pytest.mark.asyncio
async def test_produto_sem_estoque_nao_disponivel(client: AsyncClient, session):
    produto = await _produto(session, estoque=0)
    await _config_aberta(session)
    await session.commit()

    menu = await client.get("/cantina/menu")
    item = next(i for i in menu.json()["itens"] if i["id"] == str(produto.id))
    assert item["disponivel"] is False


# ─── Consulta de aluno com turma / listagem de pedidos ─────────────

@pytest.mark.asyncio
async def test_busca_aluno_com_turma_e_listagem_de_pedidos(client: AsyncClient, session):
    """Busca do cantineiro resolve a turma (join de matrículas) sem erro."""
    aluno, resp_user, _ = await _setup_aluno(session, nome="Aluno Com Turma")
    turma = await create_turma(session, codigo=f"T{uuid.uuid4().hex[:4]}")
    await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    produto = await _produto(session)
    cant = await create_usuario(session, perfil=Perfil.CANTINEIRO)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp = await client.get("/cantina/students/search", params={"q": "Aluno Com Turma"})
    assert resp.status_code == 200, resp.text
    aluno_resp = next(a for a in resp.json() if a["id"] == str(aluno.id))
    assert aluno_resp["turma"] == turma.codigo

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}
    await client.post("/cantina/orders", json={
        "aluno_id": str(aluno.id),
        "itens": [{"produto_id": str(produto.id), "quantidade": 1}],
    })

    client.headers = {"Authorization": f"Bearer {_login(cant)}"}
    resp_orders = await client.get("/cantina/orders", params={"size": 100})
    assert resp_orders.status_code == 200, resp_orders.text
    pedido = next(p for p in resp_orders.json()["items"] if p["aluno_id"] == str(aluno.id))
    assert pedido["aluno_turma"] == turma.codigo


# ─── Recarga no aluno correto (múltiplos filhos) ───────────────────

@pytest.mark.asyncio
async def test_recarga_no_aluno_correto_com_multiplos_filhos(client: AsyncClient, session):
    """Recarga com aluno_id credita exatamente o filho informado."""
    aluno1, resp_user, wallet1 = await _setup_aluno(session, nome="Filho A", saldo="0.00")
    aluno1_id = aluno1.id
    aluno2 = await create_aluno(session, nome="Filho B")
    aluno2_id = aluno2.id
    await create_responsavel_aluno(session, aluno_id=aluno2_id, responsavel_id=resp_user.id)
    wallet2 = Wallet(aluno_id=aluno2_id, saldo=Decimal("0.00"), status=StatusCarteira.ATIVA)
    session.add(wallet2)
    await _config_aberta(session)
    await session.commit()

    client.headers = {"Authorization": f"Bearer {_login(resp_user)}"}

    # via query param
    resp = await client.post(
        "/financial/me/recharge",
        params={"aluno_id": str(aluno2_id)},
        json={"valor": 30.0},
    )
    assert resp.status_code == 201, resp.text

    # via corpo (compatibilidade)
    resp2 = await client.post(
        "/financial/me/recharge",
        json={"aluno_id": str(aluno1_id), "valor": 10.0},
    )
    assert resp2.status_code == 201, resp2.text

    session.expire_all()
    b1 = await client.get("/financial/me/balance", params={"aluno_id": str(aluno1_id)})
    b2 = await client.get("/financial/me/balance", params={"aluno_id": str(aluno2_id)})
    assert Decimal(b1.json()["saldo"]) == Decimal("10.00")
    assert Decimal(b2.json()["saldo"]) == Decimal("30.00")

    # Filho não vinculado é rejeitado (IDOR)
    aluno_alheio = await create_aluno(session, nome="Filho Alheio")
    await session.commit()
    resp3 = await client.post(
        "/financial/me/recharge",
        params={"aluno_id": str(aluno_alheio.id)},
        json={"valor": 5.0},
    )
    assert resp3.status_code == 403