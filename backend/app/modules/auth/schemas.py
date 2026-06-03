import uuid

from pydantic import BaseModel

from app.shared.enums import Perfil


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    perfil: Perfil
    ativo: bool
