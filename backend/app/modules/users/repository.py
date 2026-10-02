from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Usuario


class UsuarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        result = await self._session.execute(
            select(Usuario).where(Usuario.id == usuario_id, Usuario.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, usuario_ids: list[uuid.UUID]) -> list[Usuario]:
        if not usuario_ids:
            return []
        result = await self._session.execute(
            select(Usuario).where(
                Usuario.id.in_(usuario_ids),
                Usuario.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_by_email(self, email: str) -> Usuario | None:
        result = await self._session.execute(
            select(Usuario).where(Usuario.email == email, Usuario.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_perfis(self, perfis: list) -> list[Usuario]:
        result = await self._session.execute(
            select(Usuario).where(
                Usuario.perfil.in_(perfis),
                Usuario.ativo.is_(True),
                Usuario.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_admin_user(self) -> Usuario | None:
        from app.shared.enums import Perfil

        result = await self._session.execute(
            select(Usuario).where(
                Usuario.perfil == Perfil.ADMIN,
                Usuario.ativo.is_(True),
                Usuario.deleted_at.is_(None),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, usuario: Usuario) -> Usuario:
        self._session.add(usuario)
        await self._session.flush()
        return usuario

    async def update(self, usuario: Usuario) -> Usuario:
        self._session.add(usuario)
        await self._session.flush()
        return usuario

    async def soft_delete(self, usuario: Usuario) -> Usuario:
        self._session.add(usuario)
        await self._session.flush()
        return usuario
