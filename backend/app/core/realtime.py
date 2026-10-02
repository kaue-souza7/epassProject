from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class RealtimeBroker:
    """Pub/sub em memória para eventos em tempo real (SSE).

    Limitação conhecida: o broker é por processo. Com múltiplos workers do
    Uvicorn, cada conexão recebe apenas eventos publicados no seu próprio
    worker. O polling permanece como fallback garantido no cliente.
    """

    _subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
    _lock = asyncio.Lock()

    @classmethod
    async def subscribe(cls, usuario_id: uuid.UUID) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with cls._lock:
            cls._subscribers[str(usuario_id)].add(queue)
        return queue

    @classmethod
    async def unsubscribe(cls, usuario_id: uuid.UUID, queue: asyncio.Queue) -> None:
        async with cls._lock:
            chave = str(usuario_id)
            subscribers = cls._subscribers.get(chave)
            if subscribers is None:
                return
            subscribers.discard(queue)
            if not subscribers:
                cls._subscribers.pop(chave, None)

    @classmethod
    def publish(cls, usuario_id: uuid.UUID, evento: dict) -> None:
        """Publica um evento para todas as conexões do usuário (não bloqueante)."""
        for queue in list(cls._subscribers.get(str(usuario_id), ())):
            try:
                queue.put_nowait(evento)
            except asyncio.QueueFull:  # pragma: no cover - consumidor lento
                logger.warning("Fila realtime cheia para usuário %s", usuario_id)

    @classmethod
    def subscriber_count(cls, usuario_id: uuid.UUID | None = None) -> int:
        if usuario_id is None:
            return sum(len(v) for v in cls._subscribers.values())
        return len(cls._subscribers.get(str(usuario_id), ()))
