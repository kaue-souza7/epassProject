from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.realtime import RealtimeBroker
from app.shared.enums import TipoNotificacao

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Despachador central de notificações.

    Persiste a notificação no canal "inapp" (banco), publica em tempo real
    (SSE) para o usuário conectado e encaminha para canais externos
    (push/e-mail). A criação é idempotente quando `evento_key` é informado —
    retries não duplicam persistência, realtime nem push.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        from app.database import SessionLocal
        return SessionLocal()

    async def dispatch(
        self,
        usuario_id: uuid.UUID,
        titulo: str,
        corpo: str,
        dados: dict | None = None,
        canal: str = "inapp",
        tipo: TipoNotificacao = TipoNotificacao.SISTEMA,
        entidade_tipo: str | None = None,
        entidade_id: uuid.UUID | None = None,
        evento_key: str | None = None,
        push: bool = True,
    ) -> None:
        from app.modules.communication.channels import NotificationChannels
        from app.modules.communication.service import NotificationService

        session = await self._get_session()
        owns_session = self._session is None
        try:
            notificacao, criada = await NotificationService(session).criar_detalhado(
                destinatario_id=usuario_id,
                tipo=tipo,
                titulo=titulo,
                mensagem=corpo,
                canal="inapp",
                entidade_tipo=entidade_tipo,
                entidade_id=entidade_id,
                evento_key=evento_key,
                dados=dados,
            )

            # Retry/idempotência: não repete realtime nem push para evento já criado.
            if notificacao is not None and criada:
                RealtimeBroker.publish(
                    usuario_id,
                    {
                        "evento": "notificacao",
                        "notificacao": {
                            "id": str(notificacao.id),
                            "tipo": notificacao.tipo.value if hasattr(notificacao.tipo, "value") else str(notificacao.tipo),
                            "titulo": notificacao.titulo,
                            "mensagem": notificacao.mensagem,
                            "entidade_tipo": notificacao.entidade_tipo,
                            "entidade_id": str(notificacao.entidade_id) if notificacao.entidade_id else None,
                            "dados": notificacao.dados,
                            "lida": False,
                            "created_at": notificacao.created_at.isoformat() if notificacao.created_at else None,
                        },
                    },
                )

                dados_push = {
                    **(dados or {}),
                    "notification_id": str(notificacao.id),
                    "entidade_tipo": entidade_tipo,
                    "entidade_id": str(entidade_id) if entidade_id else None,
                }

                if canal not in ("inapp", "push"):
                    await NotificationChannels.encaminhar(
                        session=session,
                        destinatario_id=usuario_id,
                        tipo=tipo,
                        titulo=titulo,
                        mensagem=corpo,
                        dados=dados_push,
                        canal_solicitado=canal,
                    )

                if push:
                    await NotificationChannels.encaminhar(
                        session=session,
                        destinatario_id=usuario_id,
                        tipo=tipo,
                        titulo=titulo,
                        mensagem=corpo,
                        dados=dados_push,
                        canal_solicitado="push",
                    )

                # Opt-in de e-mail: o usuário precisa ter ligado o canal para
                # aquele tipo. Sem linha de preferência, nada é enviado — o
                # cadastro nunca passa a vazar e-mail para fora da escola.
                #
                # Fica dentro de `criada` para que um retry do mesmo
                # `evento_key` não mande o e-mail duas vezes.
                if await self._email_opt_in(session, usuario_id, tipo):
                    await NotificationChannels.encaminhar(
                        session=session,
                        destinatario_id=usuario_id,
                        tipo=tipo,
                        titulo=titulo,
                        mensagem=corpo,
                        dados=dados_push,
                        canal_solicitado="email",
                    )

            if owns_session:
                await session.commit()
        finally:
            if owns_session:
                await session.close()

    @staticmethod
    async def _email_opt_in(
        session: AsyncSession, usuario_id: uuid.UUID, tipo: TipoNotificacao,
    ) -> bool:
        """Se o destinatário ativou e-mail para este tipo de notificação.

        Uma falha de consulta aqui não pode derrubar o despacho de inapp/push,
        então qualquer erro é registrado e tratado como "não optou".
        """
        from app.modules.communication.repository import (
            PreferenciaNotificacaoRepository,
        )

        try:
            return await PreferenciaNotificacaoRepository(session).email_habilitado(
                usuario_id, tipo,
            )
        except Exception:
            logger.exception(
                "Falha ao consultar a preferência de e-mail de %s (%s); "
                "seguindo sem envio por e-mail.",
                usuario_id, tipo,
            )
            return False
