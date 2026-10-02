from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_CHAVE_INTERVALO = "aviso_escalonamento_horas"
_INTERVALO_PADRAO_HORAS = 24
_INTERVALO_VERIFICACAO_SEGUNDOS = 900  # 15 minutos


class PushReceiptScheduler:
    """Confere os recibos de entrega do Expo Push Service.

    O ticket imediato do `/push/send` não garante entrega: erros como
    `DeviceNotRegistered` podem surgir só no recibo. Este job busca os recibos
    pendentes (>60s), marca o resultado e desativa tokens inválidos. Nenhuma
    falha aqui afeta a notificação interna já persistida.
    """

    EXPO_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"
    INTERVALO_SEGUNDOS = 300
    MAX_POR_CICLO = 1000

    def __init__(self) -> None:
        self._session_factory = None
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, session_factory) -> None:
        self._session_factory = session_factory
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="push-receipt-scheduler")
        logger.info("PushReceiptScheduler iniciado")

    async def shutdown(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PushReceiptScheduler desligado")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._processar_ciclo()
            except Exception:
                logger.exception("Erro no ciclo do PushReceiptScheduler")
            await asyncio.sleep(self.INTERVALO_SEGUNDOS)

    async def _processar_ciclo(self) -> int:
        import httpx

        from app.modules.communication.repository import (
            PushTicketRepository,
            PushTokenRepository,
        )

        async with self._session_factory() as session:
            repo = PushTicketRepository(session)
            pendentes = await repo.list_pendentes(limite=self.MAX_POR_CICLO)
            if not pendentes:
                return 0

            from app.config import settings

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if settings.EXPO_ACCESS_TOKEN:
                headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        self.EXPO_RECEIPTS_URL,
                        json={"ids": [t.ticket_id for t in pendentes]},
                        headers=headers,
                    )
                    response.raise_for_status()
                    recibos = response.json().get("data", {})
            except Exception:
                logger.exception("PushReceiptScheduler: falha ao buscar recibos")
                return 0

            token_repo = PushTokenRepository(session)
            verificados = 0
            for ticket in pendentes:
                recibo = recibos.get(ticket.ticket_id)
                if recibo is None:
                    continue  # recibo ainda não disponível: tenta no próximo ciclo
                if recibo.get("status") == "ok":
                    await repo.marcar_verificado(ticket, True)
                else:
                    erro = (recibo.get("details") or {}).get("error")
                    await repo.marcar_verificado(ticket, False, erro)
                    if erro == "DeviceNotRegistered":
                        await token_repo.deactivate(ticket.token)
                verificados += 1

            await session.commit()
            if verificados:
                logger.info("PushReceiptScheduler: %d recibo(s) verificado(s)", verificados)
            return verificados


class AvisoEscalonamentoScheduler:
    """Escalona avisos publicados e não lidos após N horas.

    - `aviso_escalonamento_horas` (configuração do sistema) define o prazo.
      Valor ausente usa 24h; valor <= 0 desativa o escalonamento.
    - Idempotente: `escalado_em` é gravado uma única vez por leitura e as
      notificações usam `evento_key` único.
    """

    def __init__(self) -> None:
        self._session_factory = None
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, session_factory) -> None:
        self._session_factory = session_factory
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="aviso-escalonamento-scheduler")
        logger.info("AvisoEscalonamentoScheduler iniciado")

    async def shutdown(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AvisoEscalonamentoScheduler desligado")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._processar_ciclo()
            except Exception:
                logger.exception("Erro no ciclo do AvisoEscalonamentoScheduler")
            await asyncio.sleep(_INTERVALO_VERIFICACAO_SEGUNDOS)

    async def _processar_ciclo(self) -> None:
        from app.modules.communication.service import AvisoService
        from app.modules.system_config.repository import ConfiguracaoSistemaRepository

        async with self._session_factory() as session:
            valor = await ConfiguracaoSistemaRepository(session).get(_CHAVE_INTERVALO)
            try:
                horas = int(valor) if valor is not None else _INTERVALO_PADRAO_HORAS
            except ValueError:
                horas = _INTERVALO_PADRAO_HORAS

            if horas <= 0:
                return

            escalados = await AvisoService(session).escalar_nao_lidos(horas)
            await session.commit()
            if escalados > 0:
                logger.info(
                    "AvisoEscalonamentoScheduler: %d aviso(s) escalonado(s)", escalados,
                )
