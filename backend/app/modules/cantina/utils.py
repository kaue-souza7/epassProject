from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "America/Sao_Paulo"

DIAS_PARA_ALERTA_VENCIMENTO = 3


def get_timezone(tz: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def agora_local(tz: str | None) -> datetime:
    return datetime.now(get_timezone(tz))


def hoje_local(tz: str | None) -> date:
    return agora_local(tz).date()


def _validade_date(produto) -> date | None:
    validade = getattr(produto, "data_validade", None)
    if validade is None:
        return None
    if isinstance(validade, datetime):
        if validade.tzinfo is None:
            validade = validade.replace(tzinfo=timezone.utc)
        return validade.astimezone(get_timezone(DEFAULT_TIMEZONE)).date()
    return validade


def produto_vencido(produto, tz: str | None = None) -> bool:
    """Produto perecível vencido (validade anterior ao dia local atual)."""
    if not getattr(produto, "perecivel", False):
        return False
    validade = _validade_date(produto)
    if validade is None:
        return False
    return validade < hoje_local(tz)


def dias_para_vencer(produto, tz: str | None = None) -> int | None:
    """Dias restantes até a validade (negativo se vencido)."""
    if not getattr(produto, "perecivel", False):
        return None
    validade = _validade_date(produto)
    if validade is None:
        return None
    return (validade - hoje_local(tz)).days