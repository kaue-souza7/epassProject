from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Usuario
from app.modules.users.repository import UsuarioRepository


class UsuarioService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UsuarioRepository(session)

    async def get_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return await self._repo.get_by_id(usuario_id)

    async def get_by_email(self, email: str) -> Usuario | None:
        return await self._repo.get_by_email(email)

    async def create(self, usuario: Usuario) -> Usuario:
        return await self._repo.create(usuario)

    async def update(self, usuario: Usuario) -> Usuario:
        return await self._repo.update(usuario)

    async def soft_delete(self, usuario: Usuario) -> Usuario:
        return await self._repo.soft_delete(usuario)
