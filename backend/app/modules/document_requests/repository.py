from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_requests.models import SolicitacaoDocumento
from app.shared.enums import StatusSolicitacaoDocumento


class SolicitacaoDocumentoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, solicitacao: SolicitacaoDocumento) -> SolicitacaoDocumento:
        self._session.add(solicitacao)
        await self._session.flush()
        return solicitacao

    async def update(self, solicitacao: SolicitacaoDocumento) -> SolicitacaoDocumento:
        self._session.add(solicitacao)
        await self._session.flush()
        return solicitacao

    async def get_by_id(self, solicitacao_id: uuid.UUID) -> SolicitacaoDocumento | None:
        result = await self._session.execute(
            select(SolicitacaoDocumento).where(
                SolicitacaoDocumento.id == solicitacao_id,
            )
        )
        return result.scalar_one_or_none()

    async def listar_por_responsavel(
        self,
        responsavel_id: uuid.UUID,
        status: StatusSolicitacaoDocumento | None = None,
    ) -> list[SolicitacaoDocumento]:
        query = select(SolicitacaoDocumento).where(
            SolicitacaoDocumento.responsavel_id == responsavel_id,
        )
        if status is not None:
            query = query.where(SolicitacaoDocumento.status == status)
        query = query.order_by(SolicitacaoDocumento.created_at.desc())
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def listar_todas(
        self,
        status: StatusSolicitacaoDocumento | None = None,
    ) -> list[SolicitacaoDocumento]:
        query = select(SolicitacaoDocumento)
        if status is not None:
            query = query.where(SolicitacaoDocumento.status == status)
        query = query.order_by(SolicitacaoDocumento.created_at.desc())
        result = await self._session.execute(query)
        return list(result.scalars().all())
