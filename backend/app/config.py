from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_SECRETS = {
    "change-me-in-production",
    "change-me-in-production-jwt-secret-key",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    ENV: Literal["local", "hml", "prod"] = "local"
    DEBUG: bool = True
    APP_NAME: str = "ePass API"
    APP_VERSION: str = "0.1.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://epass:epass123@localhost:5432/epass"
    DATABASE_URL_SYNC: str = "postgresql://epass:epass123@localhost:5432/epass"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8081"]

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_PATH: str = "./storage"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "epass-uploads"

    # SMTP
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    # TLS/STARTTLS: a porta 587 sobe a partir de texto puro. Na 465 isso é
    # corrigido para TLS implícito automaticamente (ver `core.smtp`).
    SMTP_USE_TLS: bool = True
    # TLS implícito (SMTPS), usado pela porta 465.
    SMTP_USE_SSL: bool = False
    # Valida o certificado do servidor. Desligar só para servidor on-premise
    # com certificado self-signed: a senha do SMTP passa a trafegar sem
    # garantia de integridade.
    SMTP_VERIFY_SSL: bool = True

    # Push (Expo)
    # Necessário apenas quando o projeto Expo usa "Enhanced Security for Push".
    EXPO_ACCESS_TOKEN: str | None = None

    # Sentry
    SENTRY_DSN: str | None = None

    # ------------------------------------------------------------------
    # IA local "Atena" (Ollama)
    # ------------------------------------------------------------------
    # Módulo DESACOPLADO: nada aqui pode derrubar o SGE. Se o Ollama estiver
    # parado, sem modelo ou inacessível, o sistema principal continua 100%
    # funcional e apenas o /ai/* responde degradado.
    AI_ENABLED: bool = True

    # Endpoint do Ollama. Dentro do Compose: http://ollama:11434
    # Para usar Ollama NATIVO no Mac (aceleração Metal), suba o Ollama no host
    # (`brew install ollama && ollama serve`) e aponte para:
    #   OLLAMA_BASE_URL=http://host.docker.internal:11434
    # O backend funciona igual nos dois casos — nada além desta URL muda.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Modelo local da Atena. O `ollama-bootstrap` (docker-compose) garante o
    # download automático deste tag exato; trocar aqui exige trocar lá também.
    OLLAMA_MODEL: str = "qwen3:4b"

    # Timeout da inferência (s). Alto porque em CPU o primeiro token demora:
    # o modelo precisa ser carregado do volume antes de responder.
    OLLAMA_TIMEOUT: int = 120
    # Timeout de conexão (s) — curto, para falhar rápido quando o Ollama está
    # desligado, sem penalizar o usuário que espera a inferência.
    OLLAMA_CONNECT_TIMEOUT: float = 3.0
    # Timeout do healthcheck (s).
    OLLAMA_HEALTH_TIMEOUT: float = 3.0

    # Parâmetros de inferência
    OLLAMA_NUM_CTX: int = 4096
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_REPEAT_PENALTY: float = 1.1
    # Teto de tokens de resposta. Resposta de school = curta; e teto de token
    # é também teto de memória e de latência no modelo pequeno.
    OLLAMA_MAX_TOKENS: int = 400

    # Modo raciocínio do modelo. `false` é o padrão e é intencional: o Qwen3 é
    # um modelo "thinking" e, ligado, spends minutos raciocinando para reescrever
    # um fato que o backend já calculou (medido em CPU: 7min39 → 2s desligado).
    # Só liga se o modelo for trocado por um que não suporte `think`.
    OLLAMA_THINK: bool = False

    # Concorrência: em hardware modesto, inferências simultâneas estouram a RAM.
    # 1 = serializa; a 2ª pergunta entra na fila do Ollama (OLLAMA_MAX_QUEUE).
    OLLAMA_MAX_CONCURRENCY: int = 1

    # Retry: só para erros transitórios (5xx / timeout de conexão), e apenas
    # ANTES de qualquer token ter sido gerado.
    OLLAMA_RETRY_ATTEMPTS: int = 2
    OLLAMA_RETRY_BACKOFF: float = 0.5

    # Circuit breaker: após N falhas consecutivas, o cliente para de tentar
    # durante X segundos (evita martelar uma IA caída e protege o event loop).
    OLLAMA_CIRCUIT_FAILURES: int = 5
    OLLAMA_CIRCUIT_RESET_SECONDS: int = 60

    # Streaming (SSE): tempo máximo de ESPRADA entre dois pedaços de texto.
    # Não é o timeout da resposta inteira — o modelo pode ficar quieto entre
    # tokens, mas não pode ficar quieto para sempre. Sem este teto, um stream
    # meio-morto segura a conexão e o semáforo indefinidamente.
    OLLAMA_STREAM_READ_TIMEOUT: float = 30.0

    # Streaming (SSE): tempo máximo de espera pelo PRIMEIRO token. Separado do
    # acima porque o primeiro byte inclui o carregamento do modelo pelo Ollama:
    # a primeira pergunta depois de o container subir leva dezenas de segundos
    # (medido: ~56s) enquanto os tokens seguintes saem em milissegundos. Sem
    # esta folga, a primeira pergunta do dia morreria com "demorou demais".
    OLLAMA_STREAM_FIRST_TOKEN_TIMEOUT: float = 120.0

    # Teto de caracteres do contexto autorizado enviado ao modelo.
    # O próprio tamanho do modelo (janela 4k) força economia de contexto.
    AI_CONTEXT_MAX_CHARS: int = 4000

    # --- Histórico de conversas (Fase 5) ---
    # Quantos turnos (pergunta+resposta) vão no prompt. 0 desliga o histórico:
    # cada pergunta passa a ser independente. Baixo de propósito — o modelo é
    # de 1,7 B e um histórico longo faz ele responder à conversa antiga em vez
    # da pergunta atual.
    AI_HISTORY_TURNS: int = 3
    # Teto de caracteres do bloco de histórico, independente dos turnos.
    AI_HISTORY_MAX_CHARS: int = 1200
    # Quantas conversas o endpoint de listagem devolve por padrão.
    AI_HISTORY_LIST_LIMIT: int = 50

    # Rate Limiting
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"
    AI_RATE_LIMIT: str = "20/minute"

    @model_validator(mode="after")
    def _validar_jwt_secret(self):
        if self.JWT_SECRET.strip().lower() in INSECURE_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET não pode ser um valor padrão/inseguro. "
                "Defina um segredo forte no .env antes de iniciar a aplicação."
            )
        if self.ENV == "prod" and len(self.JWT_SECRET) < 32:
            raise ValueError(
                "JWT_SECRET deve ter pelo menos 32 caracteres em ambiente de produção."
            )
        return self


settings = Settings()
