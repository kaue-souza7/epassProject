from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cantina.models import (
    ItemPedido,
    MovimentacaoEstoque,
    Pedido,
    PedidoStatusHistorico,
    Produto,
)
from app.shared.enums import OrigemPedido, StatusPedido


class ProdutoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Produto | None:
        result = await self._session.execute(
            select(Produto).where(Produto.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, id: uuid.UUID) -> Produto | None:
        result = await self._session.execute(
            select(Produto).where(Produto.id == id).with_for_update(),
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        ativo: bool | None = None,
        categoria: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Produto], int]:
        query = select(Produto)
        if ativo is not None:
            query = query.where(Produto.ativo == ativo)
        if categoria is not None:
            query = query.where(Produto.categoria == categoria)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Produto.nome).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_all_active(self) -> list[Produto]:
        result = await self._session.execute(
            select(Produto)
            .where(Produto.ativo == True)  # noqa: E712
            .order_by(Produto.nome),
        )
        return list(result.scalars().all())

    async def create(self, produto: Produto) -> Produto:
        self._session.add(produto)
        await self._session.flush()
        return produto

    async def update(self, produto: Produto) -> Produto:
        produto.updated_at = datetime.now(timezone.utc)
        self._session.add(produto)
        await self._session.flush()
        return produto

    async def toggle_status(self, id: uuid.UUID) -> Produto | None:
        produto = await self.get_by_id_for_update(id)
        if produto is None:
            return None
        produto.ativo = not produto.ativo
        produto.updated_at = datetime.now(timezone.utc)
        self._session.add(produto)
        await self._session.flush()
        return produto


class PedidoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Pedido | None:
        result = await self._session.execute(
            select(Pedido).where(Pedido.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, id: uuid.UUID) -> Pedido | None:
        result = await self._session.execute(
            select(Pedido).where(Pedido.id == id).with_for_update(),
        )
        return result.scalar_one_or_none()

    async def existe_pedido_hoje_para_aluno(
        self, aluno_id: uuid.UUID, hoje: date | None = None,
    ) -> bool:
        """Existe pedido agendado (não cancelado) para o aluno no dia de referência.

        Consumo direto no balcão não bloqueia nem é bloqueado pelo pedido do dia.
        """
        if hoje is None:
            hoje = date.today()
        result = await self._session.execute(
            select(Pedido.id).where(
                and_(
                    Pedido.aluno_id == aluno_id,
                    Pedido.data_referencia == hoje,
                    Pedido.status != StatusPedido.CANCELADO,
                    Pedido.origem != OrigemPedido.CONSUMO_DIRETO,
                )
            ).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_movimentacao_id(self, movimentacao_id: uuid.UUID) -> Pedido | None:
        result = await self._session.execute(
            select(Pedido).where(Pedido.movimentacao_id == movimentacao_id).limit(1),
        )
        return result.scalar_one_or_none()

    async def get_by_aluno_and_responsavel(
        self, pedido_id: uuid.UUID, responsavel_id: uuid.UUID,
    ) -> Pedido | None:
        result = await self._session.execute(
            select(Pedido).where(
                and_(
                    Pedido.id == pedido_id,
                    Pedido.responsavel_id == responsavel_id,
                )
            ),
        )
        return result.scalar_one_or_none()

    async def listar_por_responsavel(
        self,
        responsavel_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        aluno_id: uuid.UUID | None = None,
    ) -> tuple[list[Pedido], int]:
        query = select(Pedido).where(Pedido.responsavel_id == responsavel_id)
        if aluno_id is not None:
            query = query.where(Pedido.aluno_id == aluno_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Pedido.created_at.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def listar_todos(
        self,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Pedido], int]:
        query = select(Pedido)
        if status:
            query = query.where(Pedido.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Pedido.created_at.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create(self, pedido: Pedido) -> Pedido:
        self._session.add(pedido)
        await self._session.flush()
        return pedido

    async def update(self, pedido: Pedido) -> Pedido:
        pedido.updated_at = datetime.now(timezone.utc)
        self._session.add(pedido)
        await self._session.flush()
        return pedido

    async def listar_pendentes_expirados(
        self, cutoff: datetime,
    ) -> list[Pedido]:
        result = await self._session.execute(
            select(Pedido).where(
                and_(
                    Pedido.status == StatusPedido.PENDENTE,
                    Pedido.created_at < cutoff,
                )
            ).order_by(Pedido.created_at),
        )
        return list(result.scalars().all())

    async def obter_pedido_do_dia(
        self,
        responsavel_id: uuid.UUID,
        aluno_id: uuid.UUID,
        hoje: date | None = None,
    ) -> Pedido | None:
        if hoje is None:
            hoje = date.today()

        query = select(Pedido).where(
            and_(
                Pedido.responsavel_id == responsavel_id,
                Pedido.aluno_id == aluno_id,
                Pedido.data_referencia == hoje,
                Pedido.status != StatusPedido.CANCELADO,
            ),
        ).order_by(Pedido.created_at.desc()).limit(1)

        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def listar_historico_status(
        self, pedido_id: uuid.UUID,
    ) -> list[PedidoStatusHistorico]:
        result = await self._session.execute(
            select(PedidoStatusHistorico)
            .where(PedidoStatusHistorico.pedido_id == pedido_id)
            .order_by(PedidoStatusHistorico.created_at),
        )
        return list(result.scalars().all())


class MovimentacaoEstoqueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, movimentacao: MovimentacaoEstoque) -> MovimentacaoEstoque:
        self._session.add(movimentacao)
        await self._session.flush()
        return movimentacao

    async def list_by_produto(
        self,
        produto_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[MovimentacaoEstoque], int]:
        query = select(MovimentacaoEstoque).where(
            MovimentacaoEstoque.produto_id == produto_id,
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(MovimentacaoEstoque.created_at.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total
