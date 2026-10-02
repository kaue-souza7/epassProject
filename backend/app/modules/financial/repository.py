from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.financial.models import Movimentacao, Wallet
from app.shared.enums import TipoMovimentacao


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Wallet | None:
        result = await self._session.execute(
            select(Wallet).where(Wallet.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_aluno_id(self, aluno_id: uuid.UUID) -> Wallet | None:
        result = await self._session.execute(
            select(Wallet).where(Wallet.aluno_id == aluno_id),
        )
        return result.scalar_one_or_none()

    async def get_by_aluno_id_for_update(self, aluno_id: uuid.UUID) -> Wallet | None:
        result = await self._session.execute(
            select(Wallet).where(Wallet.aluno_id == aluno_id).with_for_update(),
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, id: uuid.UUID) -> Wallet | None:
        result = await self._session.execute(
            select(Wallet).where(Wallet.id == id).with_for_update(),
        )
        return result.scalar_one_or_none()

    async def search_paginated(
        self,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Wallet], int]:
        query = select(Wallet)
        if status:
            query = query.where(Wallet.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Wallet.created_at.desc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def exists_by_aluno(self, aluno_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(Wallet.id).where(Wallet.aluno_id == aluno_id).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def create(self, wallet: Wallet) -> Wallet:
        self._session.add(wallet)
        await self._session.flush()
        return wallet

    async def update(self, wallet: Wallet) -> Wallet:
        wallet.updated_at = datetime.now(timezone.utc)
        self._session.add(wallet)
        await self._session.flush()
        return wallet

    async def atualizar_saldo(self, wallet_id: uuid.UUID, novo_saldo: Decimal) -> None:
        await self._session.execute(
            update(Wallet)
            .where(Wallet.id == wallet_id)
            .values(saldo=novo_saldo, updated_at=datetime.now(timezone.utc)),
        )
        await self._session.flush()


class MovimentacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Movimentacao | None:
        result = await self._session.execute(
            select(Movimentacao).where(Movimentacao.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, id: uuid.UUID) -> Movimentacao | None:
        result = await self._session.execute(
            select(Movimentacao).where(Movimentacao.id == id).with_for_update(),
        )
        return result.scalar_one_or_none()

    async def get_by_wallet_paginated(
        self,
        wallet_id: uuid.UUID,
        tipo: TipoMovimentacao | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Movimentacao], int]:
        query = select(Movimentacao).where(Movimentacao.wallet_id == wallet_id)
        if tipo:
            query = query.where(Movimentacao.tipo == tipo)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(desc(Movimentacao.created_at)).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_by_idempotency_key(self, key: str) -> Movimentacao | None:
        result = await self._session.execute(
            select(Movimentacao).where(Movimentacao.idempotency_key == key).limit(1),
        )
        return result.scalar_one_or_none()

    async def get_estorno_by_consumo_id(self, consumo_id: uuid.UUID) -> Movimentacao | None:
        result = await self._session.execute(
            select(Movimentacao).where(
                Movimentacao.tipo == TipoMovimentacao.ESTORNO,
                Movimentacao.consumo_original_id == consumo_id,
            ).limit(1),
        )
        return result.scalar_one_or_none()

    async def create(self, movimentacao: Movimentacao) -> Movimentacao:
        self._session.add(movimentacao)
        await self._session.flush()
        return movimentacao
