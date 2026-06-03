from uuid import UUID


class NotificationDispatcher:
    async def dispatch(
        self,
        usuario_id: UUID,
        titulo: str,
        corpo: str,
        dados: dict | None = None,
        canal: str = "push",
    ):
        pass  # Implementado quando o módulo de comunicação estiver pronto
