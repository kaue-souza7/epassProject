"""Context builders da CANTINA.

O cantineiro é o operador do balcão: ele precisa saber o que tem para produzir
hoje, o que está acabando e se a carteira do aluno que está na frente dele tem
saldo. Não é um perfil administrativo — é operacional.

ESCOPO
------
O RBAC dá ao cantineiro `("aluno", "read", "cantina")` e
`("financeiro", "read_wallet", "cantina")`. Ou seja: ele pode VER o saldo de
qualquer aluno (para autorizar a compra no balcão), mas não o extrato, não as
notas e não as ocorrências. Estes builders respeitam essa linha:

- `saldo_aluno_cantina` mostra APENAS o saldo e a situação da carteira. Nunca
  o extrato, nunca o valor de um consumo anterior, porque o cantineiro não tem
  permissão de leitura sobre `movimentacoes` no RBAC.
- `pedidos_cantina_hoje` mostra o que precisa ser produzido — nome do aluno e
  itens — porque é o dado de operação, não dado financeiro do aluno.

A identificação do aluno na pergunta é feita por nome, e o nome é resolvido
contra a lista de alunos ATIVOS com matrícula — que é a mesma base que o
endpoint de busca do balcão usa.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.context.base import (
    AlunoNoEscopo,
    ResultadoContexto,
    formatar_decimal,
    resolver_por_nome,
    resolver_por_primeiro_nome_no_escopo,
)
from app.modules.ai.context.comum import MAX_LINHAS
from app.modules.cantina.models import ItemPedido, Pedido, Produto
from app.modules.classes.models import Turma
from app.modules.enrollments.models import Matricula
from app.modules.financial.models import Wallet
from app.modules.students.models import Aluno
from app.shared.enums import StatusCarteira, StatusMatricula, StatusPedido

# Status que ainda exigem ação do cantineiro. Um pedido "retirado" ou
# "cancelado" não está na fila de produção.
_STATUS_NA_FILA = (
    StatusPedido.PENDENTE,
    StatusPedido.APROVADO,
    StatusPedido.EM_PRODUCAO,
    StatusPedido.PRONTO,
)


def formatar_estado(status) -> str:
    """Enum do projeto -> rótulo de tela ('em_producao' -> 'Em producao')."""
    return str(getattr(status, "value", status)).replace("_", " ").capitalize()


def _preco(valor) -> str:
    return formatar_decimal(valor)


def _rotulo_produto(item: ItemPedido) -> str:
    return f"{item.quantidade}x {item.produto.nome}"


# ---------------------------------------------------------------------------
# pedidos_cantina_hoje
# ---------------------------------------------------------------------------
async def pedidos_cantina_hoje(session: AsyncSession) -> ResultadoContexto:
    """Fila de produção do balcão: pedidos de hoje que ainda não foram retirados."""
    hoje = date.today()

    por_status = (
        await session.execute(
            select(Pedido.status, func.count(Pedido.id))
            .where(Pedido.data_referencia == hoje, Pedido.status.in_(_STATUS_NA_FILA))
            .group_by(Pedido.status)
        )
    ).all()

    total = sum(int(quantidade) for _status, quantidade in por_status)

    resultado = ResultadoContexto(
        intencao="pedidos_cantina_hoje", fontes=["pedidos", "itens_pedido", "alunos"],
    )

    if total == 0:
        resultado.vazio = True
        resultado.resumo = "Não há pedidos pendentes para hoje na cantina."
        return resultado

    resultado.adicionar(
        f"Pedidos de hoje na fila: {total} (data {hoje.strftime('%d/%m/%Y')})"
    )
    for status, quantidade in por_status:
        resultado.adicionar(f"- {formatar_estado(status)}: {quantidade}")

    # WHERE data_referencia = hoje AND status na fila
    pedidos = (
        await session.execute(
            select(Pedido)
            .where(Pedido.data_referencia == hoje, Pedido.status.in_(_STATUS_NA_FILA))
            .order_by(Pedido.created_at)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado.adicionar("Pedidos a preparar:")
    for pedido in pedidos:
        itens = ", ".join(_rotulo_produto(item) for item in pedido.itens) or "sem itens"
        resultado.adicionar(
            f"- {formatar_estado(pedido.status)} | {pedido.aluno.nome} | {itens}"
        )

    resultado.resumo = (
        f"Há {total} pedido(s) de hoje aguardando na cantina."
    )
    return resultado


# ---------------------------------------------------------------------------
# cardapio_cantina
# ---------------------------------------------------------------------------
async def cardapio_cantina(session: AsyncSession) -> ResultadoContexto:
    """Produtos disponíveis para venda no balcão.

    "Disponível" tem o mesmo significado do cardápio público
    (`GET /cantina/menu`): estoque maior que zero. A IA não promete lanche que
    o balcão não tem.
    """
    produtos = (
        await session.execute(
            select(Produto)
            .where(Produto.ativo.is_(True), Produto.estoque_atual > 0)
            .order_by(Produto.categoria, Produto.nome)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado = ResultadoContexto(intencao="cardapio_cantina", fontes=["produtos"])

    if not produtos:
        resultado.vazio = True
        resultado.resumo = "Nenhum produto está disponível no cardápio agora."
        return resultado

    resultado.adicionar(f"Produtos disponíveis: {len(produtos)}")

    por_categoria: dict[str, list[Produto]] = {}
    for produto in produtos:
        categoria = str(getattr(produto.categoria, "value", produto.categoria))
        por_categoria.setdefault(categoria, []).append(produto)

    for categoria, itens in por_categoria.items():
        resultado.adicionar(f"{categoria}:")
        for produto in itens:
            resultado.adicionar(
                f"  - {produto.nome}: R$ {_preco(produto.preco)} "
                f"({produto.estoque_atual} em estoque)"
            )

    resultado.resumo = (
        f"O cardápio tem {len(produtos)} produto(s) disponível(is) para venda."
    )
    return resultado


# ---------------------------------------------------------------------------
# estoque_cantina
# ---------------------------------------------------------------------------
async def estoque_cantina(session: AsyncSession) -> ResultadoContexto:
    """Estoque de todos os produtos ativos, com destaque para os críticos."""
    total = (
        await session.execute(
            select(func.count()).select_from(Produto).where(Produto.ativo.is_(True))
        )
    ).scalar_one()

    zerados = (
        await session.execute(
            select(func.count()).select_from(Produto).where(
                Produto.ativo.is_(True), Produto.estoque_atual == 0,
            )
        )
    ).scalar_one()

    resultado = ResultadoContexto(intencao="estoque_cantina", fontes=["produtos"])

    if total == 0:
        resultado.vazio = True
        resultado.resumo = "Nenhum produto está cadastrado na cantina."
        return resultado

    resultado.adicionar(
        f"Produtos ativos: {total} | Produtos esgotados: {zerados}"
    )

    produtos = (
        await session.execute(
            select(Produto)
            .where(Produto.ativo.is_(True))
            .order_by(Produto.nome)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado.adicionar("Estoque por produto:")
    for produto in produtos:
        sinal = ""
        if produto.estoque_atual == 0:
            sinal = " [ESGOTADO]"
        elif produto.estoque_minimo and produto.estoque_atual <= produto.estoque_minimo:
            sinal = " [BAIXO]"
        resultado.adicionar(
            f"- {produto.nome}: {produto.estoque_atual} em estoque "
            f"(mínimo {produto.estoque_minimo}){sinal}"
        )

    resultado.resumo = (
        f"Há {total} produto(s) ativo(s) no estoque, sendo {zerados} esgotado(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# saldo_aluno_cantina
# ---------------------------------------------------------------------------
async def _alunos_para_busca(session: AsyncSession, busca: str) -> list[AlunoNoEscopo]:
    """Base de busca do balcão: alunos ativos com matrícula ativa.

    Espelha `GET /cantina/students/search`. O `WHERE` já traz o limite de
    matrícula ativa, então um aluno sem turma não aparece como opção de busca —
    igual ao balcão.
    """
    linhas = (
        await session.execute(
            select(Aluno, Turma)
            .join(Matricula, Matricula.aluno_id == Aluno.id)
            .join(Turma, Turma.id == Matricula.turma_id)
            .where(
                Aluno.ativo.is_(True),
                Matricula.status == StatusMatricula.ATIVA,
            )
            .order_by(Aluno.nome)
            .limit(200)
        )
    ).all()

    return [
        AlunoNoEscopo(
            id=aluno.id,
            nome=aluno.nome,
            turma_nome=turma.nome or turma.codigo,
        )
        for aluno, turma in linhas
    ]


async def saldo_aluno_cantina(
    session: AsyncSession,
    nome_candidato: str | None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Saldo na carteira de um aluno, para autorizar a compra no balcão.

    O cantineiro pode VER o saldo (é o que o RBAC permite: `read_wallet`), mas
    não o extrato. Por isso este builder nunca lista movimentações — mesmo que
    a pergunta seja "quanto ele gastou". Nesse caso a resposta é o que a
    carteira tem hoje, e o motivo do consumo não é informação do cantineiro.
    """
    if not nome_candidato:
        # Sem nome não há como responder: no balcão é sempre sobre UM aluno.
        resultado = ResultadoContexto(intencao="saldo_aluno_cantina", fontes=["wallets"])
        resultado.vazio = True
        resultado.resumo = "Me diga o nome do aluno que você quer consultar o saldo."
        return resultado

    alunos = await _alunos_para_busca(session, nome_candidato)

    # Mesma precedência do `escolher_aluno`: nome completo, depois primeiro
    # nome citado — sempre comparado contra a base JÁ filtrada do balcão.
    alvo = resolver_por_nome(alunos, nome_candidato)
    if alvo is None:
        alvo = resolver_por_primeiro_nome_no_escopo(alunos, mensagem)

    resultado = ResultadoContexto(intencao="saldo_aluno_cantina", fontes=["wallets"])

    if alvo is None:
        resultado.vazio = True
        resultado.resumo = (
            "Não encontrei esse aluno entre os alunos matriculados. "
            "Confira o nome ou use a busca da tela."
        )
        return resultado

    resultado.alunos_autorizados.append(alvo.id)
    resultado.adicionar(f"Aluno: {alvo.nome}")
    if alvo.turma_nome:
        resultado.adicionar(f"Turma: {alvo.turma_nome}")

    # WHERE wallets.aluno_id = <aluno resolvido na base do balcão>
    wallet = (
        await session.execute(select(Wallet).where(Wallet.aluno_id == alvo.id))
    ).scalar_one_or_none()

    if wallet is None:
        resultado.vazio = True
        resultado.resumo = f"{alvo.nome} ainda não possui carteira cadastrada."
        return resultado

    resultado.adicionar(f"Saldo: R$ {_preco(wallet.saldo)}")
    resultado.adicionar(f"Situação da carteira: {formatar_estado(wallet.status)}")

    if wallet.status == StatusCarteira.BLOQUEADA:
        resultado.adicionar("Atenção: a carteira está bloqueada para compras.")

    resultado.resumo = (
        f"A carteira de {alvo.nome} tem R$ {_preco(wallet.saldo)} e está "
        f"{formatar_estado(wallet.status).lower()}."
    )
    return resultado
