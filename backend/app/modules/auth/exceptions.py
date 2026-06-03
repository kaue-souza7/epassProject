from app.core.exceptions import AppException


class InvalidCredentialsError(AppException):
    def __init__(self, message: str = "Email ou senha inválidos"):
        super().__init__(message=message, status_code=401, code="invalid_credentials")


class InactiveUserError(AppException):
    def __init__(self, message: str = "Usuário inativo"):
        super().__init__(message=message, status_code=403, code="inactive_user")


class InvalidTokenError(AppException):
    def __init__(self, message: str = "Token inválido ou expirado"):
        super().__init__(message=message, status_code=401, code="invalid_token")


class SessionNotFoundError(AppException):
    def __init__(self, message: str = "Sessão não encontrada"):
        super().__init__(message=message, status_code=404, code="session_not_found")
