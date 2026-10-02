from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationError
from app.modules.cantina.models import (
    CantinaConfig,
    MovimentacaoEstoque,
    Pedido,
    PedidoStatusHistorico,
)
from app.modules.cantina.programacao_models import ProgramacaoCantina
from app.modules.cantina.repository import PedidoRepository, ProdutoRepository
from app.modules.cantina.utils import agora_local
from app.modules.students.repository import AlunoRepository
from app.shared.enums import (
    DiaSemana,
    OrigemPedido,
    StatusPedido,
    TipoMovimentacaoEstoque,
    TipoProgramacao,
)

logger = logging.getLogger(__name__)

# Lock de transação do Postgres para evitar ciclos concorrentes entre workers.
_ADVISORY_LOCK_KEY = 0x0C4A71A  # "CANT1NA"

_DIA_SEMANA_MAP: dict[int, DiaSemana] = {
    0: DiaSemana.SEG,
    1: DiaSemana.TER,
    2: DiaSemana.QUA,
    3: DiaSemana.QUI,
    4: DiaSemana.SEX,
    5: DiaSemana.SAB,
}


class CantinaScheduler:
    """Processa programações semanais e as converte em pedidos.

    - Roda periodicamente (a cada 5 minutos).
    - Converte programação DIARIA e GERAL em pedidos.
    - DIARIA tem prioridade sobre GERAL.
    - É idempotente: não duplica pedidos.
    - Auto-cancela pedidos PENDENTE que excederam o prazo.
    - Usa advisory lock para não rodar em paralelo entre workers.
    """

    def __init__(self) -> None:
        self._session_factory = None
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, session_factory) -> None:
        self._session_factory = session_factory
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="cantina-scheduler")
        logger.info("CantinaScheduler iniciado")

    async def shutdown(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CantinaScheduler desligado")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._processar_ciclo()
            except Exception:
                logger.exception("Erro no ciclo do CantinaScheduler")
            await asyncio.sleep(300)

    async def _processar_ciclo(self) -> None:
        async with self._session_factory() as session:
            if self._suporta_advisory_lock(session):
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": _ADVISORY_LOCK_KEY},
                )
            cancelados = await self._cancelar_pedidos_expirados(session)
            processados = await self._processar_programacoes(session)
            await session.commit()
            if cancelados > 0 or processados > 0:
                logger.info(
                    "CantinaScheduler: %d pedido(s) cancelado(s), %d programação(ões) processada(s)",
                    cancelados, processados,
                )

    def _suporta_advisory_lock(self, session: AsyncSession) -> bool:
        try:
            bind = session.get_bind()
            return bind is not None and bind.dialect.name == "postgresql"
        except Exception:  # pragma: no cover - defensivo
            return False

    async def _cancelar_pedidos_expirados(self, session: AsyncSession) -> int:
        from datetime import timedelta

        result = await session.execute(select(CantinaConfig).limit(1))
        config = result.scalars().first()
        if config is None or not config.prazo_pedido_minutos or config.prazo_pedido_minutos <= 0:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.prazo_pedido_minutos)
        pedido_repo = PedidoRepository(session)
        produto_repo = ProdutoRepository(session)

        pedidos_expirados = await pedido_repo.listar_pendentes_expirados(cutoff)
        cancelados = 0
        for pedido in pedidos_expirados:
            pedido_lock = await pedido_repo.get_by_id_for_update(pedido.id)
            if pedido_lock is None or pedido_lock.status != StatusPedido.PENDENTE:
                continue

            if pedido_lock.saldo_debitado > Decimal("0.00") or pedido_lock.movimentacao_id is not None:
                logger.warning(
                    "Pedido %s não está mais pendente (saldo debitado). Cancelamento automático ignorado.",
                    pedido.id,
                )
                continue

            for item in pedido_lock.itens:
                produto = await produto_repo.get_by_id_for_update(item.produto_id)
                if produto is not None:
                    estoque_anterior = produto.estoque_atual
                    produto.estoque_atual = estoque_anterior + item.quantidade
                    await produto_repo.update(produto)
                    session.add(MovimentacaoEstoque(
                        produto_id=produto.id,
                        tipo=TipoMovimentacaoEstoque.ENTRADA,
                        quantidade=item.quantidade,
                        estoque_anterior=estoque_anterior,
                        estoque_atual=produto.estoque_atual,
                        motivo=f"Cancelamento automático do pedido #{str(pedido_lock.id)[:8]}",
                        usuario_id=None,
                    ))

            status_anterior = pedido_lock.status
            pedido_lock.status = StatusPedido.CANCELADO
            pedido_lock.cancelado_em = datetime.now(timezone.utc)
            obs = pedido_lock.observacoes or ""
            pedido_lock.observacoes = (obs + " [Cancelado automaticamente — prazo expirado]").strip()
            await pedido_repo.update(pedido_lock)
            session.add(PedidoStatusHistorico(
                pedido_id=pedido_lock.id,
                status_anterior=status_anterior,
                status_novo=StatusPedido.CANCELADO,
                usuario_id=None,
                observacao="Cancelado automaticamente — prazo expirado",
            ))

            from app.core.notifications import NotificationDispatcher
            from app.shared.enums import TipoNotificacao

            await NotificationDispatcher(session).dispatch(
                usuario_id=pedido_lock.responsavel_id,
                titulo="Pedido cancelado automaticamente",
                corpo=(
                    f"O pedido de {pedido_lock.aluno.nome if pedido_lock.aluno else 'seu filho'} "
                    "não foi aprovado a tempo e foi cancelado automaticamente."
                ),
                canal="inapp",
                tipo=TipoNotificacao.CANTINA,
                entidade_tipo="pedido",
                entidade_id=pedido_lock.id,
                evento_key=f"pedido-cancelado-auto:{pedido_lock.id}",
            )
            cancelados += 1

        return cancelados

    async def _processar_programacoes(self, session: AsyncSession) -> int:
        result = await session.execute(select(CantinaConfig).limit(1))
        config = result.scalars().first()
        if config is None or not config.aberta:
            return 0

        agora = agora_local(config.timezone)
        hoje = agora.date()
        dia_semana_atual = _DIA_SEMANA_MAP.get(hoje.weekday())
        if dia_semana_atual is None:
            return 0

        if not self._dia_funciona(config, dia_semana_atual):
            return 0

        if not self._dentro_horario(config, agora):
            return 0

        result = await session.execute(
            select(ProgramacaoCantina).where(
                and_(
                    ProgramacaoCantina.ativo.is_(True),
                    (
                        (ProgramacaoCantina.dia_semana == dia_semana_atual)
                        | (ProgramacaoCantina.tipo == TipoProgramacao.GERAL)
                    ),
                )
            )
        )
        programacoes = list(result.scalars().all())

        programacoes_por_aluno: dict[uuid.UUID, list[ProgramacaoCantina]] = {}
        for prog in programacoes:
            programacoes_por_aluno.setdefault(prog.aluno_id, []).append(prog)

        processados = 0
        for aluno_id, progs in programacoes_por_aluno.items():
            ja_tem_pedido = await self._ja_tem_pedido_hoje(session, aluno_id, hoje)
            if ja_tem_pedido:
                continue

            diaria = [
                p for p in progs
                if p.tipo == TipoProgramacao.DIARIA and p.dia_semana == dia_semana_atual
            ]
            geral = [p for p in progs if p.tipo == TipoProgramacao.GERAL]

            # DIARIA sobrescreve GERAL para o dia; GERAL é o padrão da semana.
            programacao_escolhida = diaria[0] if diaria else (geral[0] if geral else None)
            if programacao_escolhida is None:
                continue

            sucesso = await self._criar_pedido_de_programacao(
                session, programacao_escolhida,
            )
            if sucesso:
                processados += 1

        return processados

    async def _criar_pedido_de_programacao(
        self, session: AsyncSession, programacao: ProgramacaoCantina,
    ) -> bool:
        from app.modules.cantina.service import CantinaService

        service = CantinaService(session)
        try:
            pedido = await service._criar_pedido_de_programacao_manual(programacao)
        except Conflict:
            logger.warning(
                "Programação %s: pedido duplicado para aluno %s no dia, ignorando",
                programacao.id, programacao.aluno_id,
            )
            return False
        except (ValidationError, Forbidden, NotFound) as exc:
            logger.warning(
                "Programação %s não convertida para aluno %s: %s",
                programacao.id, programacao.aluno_id, exc.message,
            )
            return False

        logger.info(
            "Pedido %s criado a partir da programação %s para aluno %s",
            pedido.id, programacao.id, programacao.aluno_id,
        )
        return True

    async def _ja_tem_pedido_hoje(
        self, session: AsyncSession, aluno_id: uuid.UUID, hoje: date,
    ) -> bool:
        result = await session.execute(
            select(Pedido.id).where(
                and_(
                    Pedido.aluno_id == aluno_id,
                    Pedido.data_referencia == hoje,
                    Pedido.status != StatusPedido.CANCELADO,
                    Pedido.origem != OrigemPedido.CONSUMO_DIRETO,
                )
            ).limit(1),
        )
        return result.scalar_one_or_none() is not None

    def _dia_funciona(self, config: CantinaConfig, dia: DiaSemana) -> bool:
        if not config.dias_funcionamento:
            return True
        dias_ativos = [d.strip().lower() for d in config.dias_funcionamento.split(",")]
        return dia.value in dias_ativos

    def _dentro_horario(self, config: CantinaConfig, agora: datetime) -> bool:
        hora_atual = agora.time().replace(tzinfo=None)
        if config.horario_abertura:
            try:
                h_abertura = datetime.strptime(config.horario_abertura, "%H:%M").time()
                if hora_atual < h_abertura:
                    return False
            except ValueError:
                pass
        if config.horario_fechamento:
            try:
                h_fechamento = datetime.strptime(config.horario_fechamento, "%H:%M").time()
                if hora_atual > h_fechamento:
                    return False
            except ValueError:
                pass
        return True