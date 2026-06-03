from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.security import decode_token
from app.core.permissions import PermissionChecker
from app.shared.enums import Perfil

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    session: AsyncSession = Depends(get_session),
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de token inválido")
    return payload


def require_roles(*roles: Perfil):
    async def check(current_user: dict = Depends(get_current_user)):
        if current_user.get("perfil") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado",
            )
        return current_user

    return check


def require_permission(recurso: str, acao: str, escopo: str):
    async def check(current_user: dict = Depends(get_current_user)):
        perfil = current_user.get("perfil", "")
        if not PermissionChecker.has_permission(perfil, recurso, acao, escopo):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
        return current_user
    return Depends(check)
