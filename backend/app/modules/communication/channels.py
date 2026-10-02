from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.enums import TipoNotificacao

logger = logging.getLogger(__name__)

# Rótulo exibido no cabeçalho do e-mail, para o responsável distinguir
# rapidamente o assunto do qual se trata.
ROTULO_TIPO: dict[TipoNotificacao, str] = {
    TipoNotificacao.AVISO: "Aviso",
    TipoNotificacao.OCORRENCIA: "Ocorrência",
    TipoNotificacao.BOLETIM: "Boletim",
    TipoNotificacao.CANTINA: "Cantina",
    TipoNotificacao.AGENDA: "Agenda",
    TipoNotificacao.FINANCEIRO: "Financeiro",
    TipoNotificacao.NOTA: "Nota",
    TipoNotificacao.FREQUENCIA: "Frequência",
    TipoNotificacao.SISTEMA: "Notificação",
}


class NotificationChannel(ABC):
    """Canal de entrega de notificações (inapp, email, push)."""

    name: str = "base"

    @abstractmethod
    async def send(
        self,
        session: AsyncSession,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        dados: dict | None = None,
    ) -> None:
        ...


class InAppChannel(NotificationChannel):
    """Canal padrão: a persistência é feita pelo NotificationService."""

    name = "inapp"

    async def send(
        self,
        session: AsyncSession,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        dados: dict | None = None,
    ) -> None:
        # A persistência inapp já é realizada pelo NotificationService.
        return None


class EmailChannel(NotificationChannel):
    """Canal de e-mail: envia via SMTP configurado (não bloqueia o fluxo)."""

    name = "email"

    async def send(
        self,
        session: AsyncSession,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        dados: dict | None = None,
    ) -> None:
        from app.modules.boletim.email import enviar_email
        from app.modules.system_config.repository import ConfiguracaoSistemaRepository
        from app.modules.users.repository import UsuarioRepository

        # `UsuarioRepository` era importado de `communication.repository`, onde
        # nunca existiu: o `ImportError` era engolido por `encaminhar` e todo
        # e-mail de notificação falhava em silêncio.
        usuario = await UsuarioRepository(session).get_by_id(destinatario_id)
        if usuario is None or not usuario.email:
            logger.warning("EmailChannel: usuário %s sem e-mail — ignorado", destinatario_id)
            return

        smtp_config = await ConfiguracaoSistemaRepository(session).get_all_smtp()
        # Título e mensagem vêm de conteúdo escrito por usuários (professor
        # nomeando a ocorrência, corpo do aviso), então precisam ser escapados
        # antes de virar HTML.
        titulo_html = escape(titulo)
        mensagem_html = escape(mensagem).replace("\n", "<br>")
        rotulo = ROTULO_TIPO.get(tipo, "Notificação")
        corpo_html = (
            "<html><body style=\"margin:0;padding:24px;"
            "font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;"
            "background:#F5F5F7;color:#1F1F1F;\">"
            "<div style=\"max-width:560px;margin:0 auto;background:#FFFFFF;"
            "border-radius:16px;padding:24px;\">"
            f"<p style=\"margin:0 0 4px;font-size:12px;letter-spacing:.5px;"
            f"text-transform:uppercase;color:#FF5B8F;\">{escape(rotulo)}</p>"
            f"<h2 style=\"margin:0 0 12px;font-size:20px;line-height:1.3;\">"
            f"{titulo_html}</h2>"
            f"<p style=\"margin:0;font-size:15px;line-height:1.6;\">"
            f"{mensagem_html}</p>"
            "<hr style=\"border:none;border-top:1px solid #E5E5E5;margin:24px 0 12px;\">"
            "<p style=\"margin:0;font-size:12px;color:#7A7A7A;\">"
            "Você recebe este e-mail porque ativou o envio por e-mail nas "
            "notificações do aplicativo ePass. Para desligar, abra o app em "
            "Perfil › Notificações.</p>"
            "</div></body></html>"
        )
        # SMTP é bloqueante; executa fora do event loop.
        await asyncio.to_thread(
            enviar_email,
            destinatario=usuario.email,
            assunto=f"[ePass] {titulo}",
            corpo_html=corpo_html,
            smtp_config=smtp_config,
        )


class PushChannel(NotificationChannel):
    """Canal push via Expo Push API.

    Lê os tokens ativos do destinatário, envia em lote e desativa tokens
    inválidos (`DeviceNotRegistered`). Sem tokens cadastrados, é no-op.
    """

    name = "push"
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
    TAMANHO_LOTE = 100  # limite do Expo Push Service por requisição

    async def send(
        self,
        session: AsyncSession,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        dados: dict | None = None,
    ) -> None:
        import httpx

        from app.modules.communication.models import PushTicket
        from app.modules.communication.repository import (
            PushTicketRepository,
            PushTokenRepository,
        )

        token_repo = PushTokenRepository(session)
        tokens = await token_repo.list_ativos(destinatario_id)
        if not tokens:
            return

        data_payload = {
            "tipo": tipo.value if hasattr(tipo, "value") else str(tipo),
            **(dados or {}),
        }

        for inicio in range(0, len(tokens), self.TAMANHO_LOTE):
            lote = tokens[inicio:inicio + self.TAMANHO_LOTE]
            payload = [
                {
                    "to": registro.token,
                    "title": titulo,
                    "body": mensagem,
                    "sound": "default",
                    "priority": "high",
                    "data": data_payload,
                }
                for registro in lote
            ]

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            from app.config import settings

            if settings.EXPO_ACCESS_TOKEN:
                headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        self.EXPO_PUSH_URL,
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    tickets = response.json().get("data", [])
            except Exception:
                logger.exception(
                    "PushChannel: falha ao enviar push para %s (lote %d-%d)",
                    destinatario_id, inicio, inicio + len(lote),
                )
                continue

            tickets_ok: list[PushTicket] = []
            for ticket, registro in zip(tickets, lote):
                if not isinstance(ticket, dict):
                    continue
                if ticket.get("status") == "ok" and ticket.get("id"):
                    # Recibo será conferido depois pelo scheduler.
                    tickets_ok.append(PushTicket(
                        ticket_id=str(ticket["id"]),
                        usuario_id=destinatario_id,
                        token=registro.token,
                    ))
                    continue
                erro = (ticket.get("details") or {}).get("error")
                if erro == "DeviceNotRegistered":
                    await token_repo.deactivate(registro.token)
                else:
                    logger.warning(
                        "PushChannel: ticket de erro para %s: %s (%s)",
                        registro.token, ticket.get("message"), erro,
                    )

            if tickets_ok:
                try:
                    await PushTicketRepository(session).create_many(tickets_ok)
                except Exception:
                    # O registro do recibo nunca deve quebrar a entrega.
                    logger.exception("PushChannel: falha ao registrar tickets")


class NotificationChannels:
    """Registro de canais disponíveis — o domínio não depende de canal específico."""

    _registry: dict[str, NotificationChannel] = {
        InAppChannel().name: InAppChannel(),
        EmailChannel().name: EmailChannel(),
        PushChannel().name: PushChannel(),
    }

    @classmethod
    def registrar(cls, canal: NotificationChannel) -> None:
        cls._registry[canal.name] = canal

    @classmethod
    async def encaminhar(
        cls,
        session: AsyncSession,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        dados: dict | None = None,
        canal_solicitado: str | None = None,
    ) -> None:
        canal = cls._registry.get(canal_solicitado or "inapp")
        if canal is None:
            logger.warning("Canal de notificação '%s' não registrado", canal_solicitado)
            return
        try:
            await canal.send(
                session=session,
                destinatario_id=destinatario_id,
                tipo=tipo,
                titulo=titulo,
                mensagem=mensagem,
                dados=dados,
            )
        except Exception:
            logger.exception("Falha ao enviar notificação via canal %s", canal.name)
