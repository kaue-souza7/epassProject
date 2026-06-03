import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFound
from app.database import get_session
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
)
from app.modules.auth.service import AuthService
from app.modules.users.service import UsuarioService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    auth_service = AuthService(session)
    usuario = await auth_service.authenticate_user(body.email, body.password)
    tokens = await auth_service.issue_tokens(usuario)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    body: RefreshRequest, session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    auth_service = AuthService(session)
    tokens = await auth_service.refresh_session(body.refresh_token)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
    )


@router.post("/logout", status_code=204)
async def logout(body: LogoutRequest, session: AsyncSession = Depends(get_session)) -> None:
    auth_service = AuthService(session)
    await auth_service.logout_session(body.refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(
    payload: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    usuario_service = UsuarioService(session)
    usuario = await usuario_service.get_by_id(uuid.UUID(payload["sub"]))
    if usuario is None:
        raise NotFound("Usuário não encontrado")
    return MeResponse(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=usuario.perfil,
        ativo=usuario.ativo,
    )
