from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.auth.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    SessionNotFoundError,
)
from app.modules.auth.models import Sessao
from app.modules.auth.repository import SessaoRepository
from app.modules.users.models import Usuario
from app.modules.users.service import UsuarioService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SessaoRepository(session)
        self._usuario_service = UsuarioService(session)

    async def create_session(self, sessao: Sessao) -> Sessao:
        return await self._repo.create(sessao)

    async def revoke_session(self, sessao: Sessao) -> Sessao:
        sessao.revoked_at = datetime.now(UTC)
        return await self._repo.update(sessao)

    async def get_session_by_jti(self, jti: str) -> Sessao | None:
        return await self._repo.get_by_jti(jti)

    async def get_expired_sessions(self) -> list[Sessao]:
        return await self._repo.get_expired()

    async def authenticate_user(self, email: str, password: str) -> Usuario:
        usuario = await self._usuario_service.get_by_email(email)
        if usuario is None:
            raise InvalidCredentialsError()
        if not usuario.ativo:
            raise InactiveUserError()
        if not verify_password(password, usuario.senha_hash):
            raise InvalidCredentialsError()
        return usuario

    async def issue_tokens(self, usuario: Usuario) -> dict[str, str]:
        access = create_access_token(
            subject=str(usuario.id),
            extra_claims={"perfil": usuario.perfil.value},
        )
        refresh, jti = create_refresh_token(subject=str(usuario.id))
        sessao = Sessao(
            usuario_id=usuario.id,
            refresh_token_jti=jti,
            expires_at=datetime.now(UTC) + timedelta(
                days=settings.JWT_REFRESH_EXPIRE_DAYS,
            ),
        )
        await self._repo.create(sessao)
        return {
            "access_token": access,
            "refresh_token": refresh,
        }

    async def refresh_session(self, refresh_token: str) -> dict[str, str]:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise InvalidTokenError()
        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        sessao = await self._repo.get_by_jti(payload["jti"])
        if sessao is None:
            raise SessionNotFoundError()
        if sessao.revoked_at is not None:
            raise InvalidTokenError("Sessão já revogada")
        if sessao.expires_at < datetime.now(UTC):
            raise InvalidTokenError("Sessão expirada")

        usuario = await self._usuario_service.get_by_id(
            uuid.UUID(payload["sub"]),
        )
        if usuario is None or not usuario.ativo:
            raise InvalidTokenError("Usuário inválido ou inativo")

        await self.revoke_session(sessao)
        return await self.issue_tokens(usuario)

    async def logout_session(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise InvalidTokenError()
        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        sessao = await self.get_session_by_jti(payload["jti"])
        if sessao is None:
            raise SessionNotFoundError()
        if sessao.revoked_at is not None:
            raise InvalidTokenError("Sessão já revogada")

        await self.revoke_session(sessao)

    async def revogar_sessoes_do_usuario(self, usuario_id: uuid.UUID) -> int:
        """Invalida todas as sessões ativas (usado após troca de senha)."""
        return await self._repo.revogar_ativas_do_usuario(usuario_id)
