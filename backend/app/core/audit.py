from uuid import UUID


class AuditLogger:
    async def log(
        self,
        usuario_id: UUID | None,
        acao: str,
        entidade: str,
        entidade_id: UUID | str,
        campos: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        pass  # Implementado quando o módulo de usuários estiver pronto
