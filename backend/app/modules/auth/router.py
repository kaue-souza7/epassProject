import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.exceptions import Conflict, NotFound, ValidationError
from app.core.rate_limit import limiter
from app.core.security import hash_password, verify_password
from app.database import get_session
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    UpdateMeRequest,
)
from app.modules.auth.service import AuthService
from app.modules.users.service import UsuarioService

router = APIRouter(prefix="/auth", tags=["auth"])

MIN_SENHA_LEN = 8


def _validar_email(email: str) -> str:
    normalizado = email.strip().lower()
    if "@" not in normalizado or "." not in normalizado.split("@")[-1]:
        raise ValidationError("E-mail inválido")
    return normalizado


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(request: Request, body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
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


@router.patch("/me", response_model=MeResponse)
async def atualizar_me(
    body: UpdateMeRequest,
    payload: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    usuario_service = UsuarioService(session)
    usuario = await usuario_service.get_by_id(uuid.UUID(payload["sub"]))
    if usuario is None:
        raise NotFound("Usuário não encontrado")

    if body.nome is not None:
        nome = body.nome.strip()
        if len(nome) < 3:
            raise ValidationError("Nome deve ter ao menos 3 caracteres")
        if len(nome) > 200:
            raise ValidationError("Nome deve ter no máximo 200 caracteres")
        usuario.nome = nome

    if body.email is not None:
        email = _validar_email(body.email)
        if email != usuario.email:
            existente = await usuario_service.get_by_email(email)
            if existente is not None:
                raise Conflict("Este e-mail já está em uso")
            usuario.email = email

    await usuario_service.update(usuario)
    return MeResponse(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=usuario.perfil,
        ativo=usuario.ativo,
    )


@router.post("/me/senha", status_code=204)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def trocar_senha(
    request: Request,
    body: ChangePasswordRequest,
    payload: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    if len(body.nova_senha) < MIN_SENHA_LEN:
        raise ValidationError(f"A nova senha deve ter ao menos {MIN_SENHA_LEN} caracteres")
    if body.nova_senha == body.senha_atual:
        raise ValidationError("A nova senha deve ser diferente da atual")

    usuario_service = UsuarioService(session)
    usuario = await usuario_service.get_by_id(uuid.UUID(payload["sub"]))
    if usuario is None:
        raise NotFound("Usuário não encontrado")
    if not verify_password(body.senha_atual, usuario.senha_hash):
        raise ValidationError("Senha atual incorreta")

    usuario.senha_hash = hash_password(body.nova_senha)
    await usuario_service.update(usuario)

    # A troca de senha encerra as sessões ativas: qualquer token de refresh
    # emitido antes da troca deixa de valer.
    auth_service = AuthService(session)
    await auth_service.revogar_sessoes_do_usuario(usuario.id)
