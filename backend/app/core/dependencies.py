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

    # O token pode ser válido e ainda assim apontar para um usuário removido ou
    # inativo (token obsoleto). Sem esta checagem, inserts com `criado_por`/FK
    # caíam em IntegrityError → 500 genérico. Aqui a falha vira 401 explícito,
    # forçando o cliente a renovar a sessão.
    import uuid as _uuid

    from app.modules.users.repository import UsuarioRepository

    try:
        usuario_id = _uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    usuario = await UsuarioRepository(session).get_by_id(usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida. Faça login novamente.",
        )

    payload["nome"] = usuario.nome
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
