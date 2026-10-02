from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Sessao


class SessaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, sessao_id: uuid.UUID) -> Sessao | None:
        result = await self._session.execute(
            select(Sessao).where(Sessao.id == sessao_id)
        )
        return result.scalar_one_or_none()

    async def get_by_jti(self, jti: str) -> Sessao | None:
        result = await self._session.execute(
            select(Sessao).where(Sessao.refresh_token_jti == jti)
        )
        return result.scalar_one_or_none()

    async def create(self, sessao: Sessao) -> Sessao:
        self._session.add(sessao)
        await self._session.flush()
        return sessao

    async def update(self, sessao: Sessao) -> Sessao:
        self._session.add(sessao)
        await self._session.flush()
        return sessao

    async def get_expired(self) -> list[Sessao]:
        result = await self._session.execute(
            select(Sessao).where(Sessao.expires_at < datetime.now(UTC))
        )
        return list(result.scalars().all())

    async def revogar_ativas_do_usuario(self, usuario_id: uuid.UUID) -> int:
        """Revoga todas as sessões ativas. Usado após troca de senha."""
        result = await self._session.execute(
            select(Sessao).where(
                Sessao.usuario_id == usuario_id,
                Sessao.revoked_at.is_(None),
            )
        )
        sessoes = list(result.scalars().all())
        agora = datetime.now(UTC)
        for sessao in sessoes:
            sessao.revoked_at = agora
            self._session.add(sessao)
        await self._session.flush()
        return len(sessoes)
