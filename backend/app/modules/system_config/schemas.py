from pydantic import BaseModel, Field


class SmtpConfigRequest(BaseModel):
    smtp_host: str = Field(..., min_length=1, description="Servidor SMTP")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="Porta SMTP")
    smtp_user: str = Field(..., min_length=1, description="Usuário/e-mail SMTP")
    # A senha nunca volta da API, então o formulário não consegue reexibi-la.
    # Ausente ou vazia = manter a que já está salva.
    smtp_password: str | None = Field(
        default=None, description="Senha SMTP. Omitir mantém a atual.",
    )
    smtp_from: str = Field(..., min_length=1, description="Remetente (e-mail)")
    smtp_use_tls: bool = Field(default=True, description="Usar STARTTLS (porta 587)")
    smtp_use_ssl: bool = Field(default=False, description="Usar TLS implícito (porta 465)")


class SmtpConfigResponse(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool | None = None
    smtp_use_ssl: bool | None = None
    configured: bool = False


class SmtpTestRequest(BaseModel):
    destinatario: str = Field(..., min_length=1, description="E-mail de destino para o teste")


class SmtpTestResponse(BaseModel):
    success: bool
    message: str


class AvisoConfigRequest(BaseModel):
    escalonamento_horas: int = Field(
        default=24,
        ge=0,
        le=720,
        description="Horas sem leitura antes de escalonar o aviso (0 desativa)",
    )


class AvisoConfigResponse(BaseModel):
    escalonamento_horas: int = 24
