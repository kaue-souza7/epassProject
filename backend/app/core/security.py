from datetime import UTC, datetime, timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.config import settings

# Argon2id configuration (argon2-cffi 25.x defaults)
#   time_cost=3     -> 3 iterations
#   memory_cost=65536 -> 64 MB memory usage
#   parallelism=4   -> 4 threads
#   hash_len=32     -> 32-byte output
#   salt_len=16     -> 16-byte random salt
#   type=Type.ID    -> Argon2id (hybrid resistant to side-channel + GPU attacks)
_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
        "iat": now,
        "type": "access",
        "jti": str(uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> tuple[str, str]:
    now = datetime.now(UTC)
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Token inválido ou expirado")
