from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.code = code or "app_error"


class NotFound(AppException):
    def __init__(self, message: str = "Recurso não encontrado"):
        super().__init__(message=message, status_code=404, code="not_found")


class Forbidden(AppException):
    def __init__(self, message: str = "Acesso negado"):
        super().__init__(message=message, status_code=403, code="forbidden")


class Unauthorized(AppException):
    def __init__(self, message: str = "Não autenticado"):
        super().__init__(message=message, status_code=401, code="unauthorized")


class Conflict(AppException):
    def __init__(self, message: str = "Conflito"):
        super().__init__(message=message, status_code=409, code="conflict")


class ValidationError(AppException):
    def __init__(self, message: str = "Dados inválidos"):
        super().__init__(message=message, status_code=422, code="validation_error")


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
        )
