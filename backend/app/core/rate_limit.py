
from fastapi import Request
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)


def chave_por_usuario(request: Request) -> str:
    """Chave de rate limit por USUÁRIO autenticado, não por IP.

    Motivo: o ePass roda atrás de proxy reverso, então `get_remote_address` devolve
    o IP do proxy — o mesmo para toda a escola. Com chave por IP, um único aluno
    que marretasse o chat esgotaria a cota de todos os outros, e o primeiro sintoma
    seria "a IA fica lenta" para gente que não fez nada.

    O `sub` do JWT é lido SEM verificar a assinatura, porque para fins de
    contagem só interessa uma chave estável — a autenticação de verdade acontece
    logo depois, em `get_current_user`. Usar um token forjado aqui só faria o
    atacante queimar a própria cota.

    Sem token reconhecível (health check, requisição sem auth), cai no IP.
    """
    cabecalho = request.headers.get("authorization", "")
    if cabecalho.lower().startswith("bearer "):
        try:
            # options={"verify_signature": False} — só queremos o `sub`.
            payload = jwt.decode(
                cabecalho.split(" ", 1)[1],
                key="",
                options={"verify_signature": False, "verify_aud": False},
            )
            sub = payload.get("sub")
            if sub:
                return f"usuario:{sub}"
        except Exception:  # noqa: BLE001 — token malformado: cai no IP
            pass
    return f"ip:{get_remote_address(request)}"
