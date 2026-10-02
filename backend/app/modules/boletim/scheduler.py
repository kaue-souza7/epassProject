from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.allocations.models import Alocacao
from app.modules.boletim.email import enviar_email
from app.modules.boletim.models import LiberacaoBoletim, PrazoLiberacao
from app.modules.boletim.repository import LiberacaoBoletimRepository, PrazoLiberacaoRepository
from app.modules.boletim.service import PrazoLiberacaoService

logger = logging.getLogger(__name__)


def _calcular_datetime_expiracao(prazo: PrazoLiberacao) -> datetime:
    """Combina data_limite + hora_limite em um datetime UTC."""
    return datetime.combine(prazo.data_limite, prazo.hora_limite, tzinfo=timezone.utc)


class PrazoScheduler:
    """Agendador de notificações com disparo exato por prazo.

    Cada prazo ganha uma task asyncio individual que dorme até o momento
    exato do vencimento e então processa a notificação.

    - Na inicialização (ou restart), todos os prazos ativos e não notificados
      são carregados do banco e agendados.
    - Na criação/edição/ativação de prazo pelo admin, o agendamento é atualizado.
    - Na desativação/remoção, o agendamento é cancelado.
    - Se o prazo já está vencido ao ser carregado, é processado imediatamente.
    """

    def __init__(self) -> None:
        self._tasks: dict[uuid.UUID, asyncio.Task] = {}
        self._session_factory = None

    async def start(self, session_factory) -> None:
        """Carrega todos os prazos ativos não notificados e agenda cada um."""
        self._session_factory = session_factory
        await self._load_and_schedule_all()

    async def _load_and_schedule_all(self) -> None:
        async with self._session_factory() as session:
            repo = PrazoLiberacaoRepository(session)
            prazos = await repo.get_all_active_unnotified()
            for prazo in prazos:
                self._schedule_prazo(prazo)
        logger.info("Scheduler de prazos iniciado com %d prazo(s) agendado(s)", len(self._tasks))

    def _schedule_prazo(self, prazo: PrazoLiberacao) -> None:
        """Agenda (ou re-agenda) a task de notificação para um prazo."""
        if prazo.id in self._tasks:
            self._tasks[prazo.id].cancel()

        expire_dt = _calcular_datetime_expiracao(prazo)
        now = datetime.now(timezone.utc)
        delay = (expire_dt - now).total_seconds()

        if delay <= 0:
            logger.info("Prazo %s já vencido — processando imediatamente", prazo.id)
            task = asyncio.create_task(self._process_prazo(prazo.id), name=f"prazo-{prazo.id}")
        else:
            logger.info(
                "Prazo %s agendado para %s (daqui %.0fs)",
                prazo.id, expire_dt.isoformat(), delay,
            )
            task = asyncio.create_task(
                self._delayed_process(prazo.id, delay),
                name=f"prazo-{prazo.id}",
            )

        self._tasks[prazo.id] = task

    async def _delayed_process(self, prazo_id: uuid.UUID, delay: float) -> None:
        """Dorme pelo delay exato e então processa o prazo."""
        await asyncio.sleep(delay)
        await self._process_prazo(prazo_id)

    async def _process_prazo(self, prazo_id: uuid.UUID) -> None:
        """Processa um único prazo vencido: verifica pendências e envia e-mail."""
        try:
            async with self._session_factory() as session:
                prazo_repo = PrazoLiberacaoRepository(session)
                prazo = await prazo_repo.get_by_id(prazo_id)
                if prazo is None or prazo.notificado_em is not None:
                    return

                liberacao_repo = LiberacaoBoletimRepository(session)
                prazo_service = PrazoLiberacaoService(session)
                await _processar_prazo_vencido(session, prazo, liberacao_repo, prazo_service)
                await session.commit()
                logger.info("Prazo %s processado com sucesso", prazo_id)
        except Exception:
            logger.exception("Erro ao processar prazo %s", prazo_id)
        finally:
            self._tasks.pop(prazo_id, None)

    def schedule_prazo(self, prazo: PrazoLiberacao) -> None:
        """Agenda ou re-agenda um prazo (chamado pelo admin CRUD)."""
        if not prazo.ativo or prazo.notificado_em is not None:
            self.unschedule_prazo(prazo.id)
            return
        self._schedule_prazo(prazo)

    def unschedule_prazo(self, prazo_id: uuid.UUID) -> None:
        """Cancela o agendamento de um prazo."""
        task = self._tasks.pop(prazo_id, None)
        if task and not task.done():
            task.cancel()
            logger.info("Agendamento do prazo %s cancelado", prazo_id)

    async def shutdown(self) -> None:
        """Cancela todas as tasks ao desligar."""
        for prazo_id in list(self._tasks):
            self.unschedule_prazo(prazo_id)
        logger.info("Scheduler de prazos desligado")


async def _processar_prazo_vencido(
    session: AsyncSession,
    prazo: PrazoLiberacao,
    liberacao_repo: LiberacaoBoletimRepository,
    prazo_service: PrazoLiberacaoService,
) -> None:
    from app.modules.allocations.repository import AlocacaoRepository
    from app.modules.system_config.repository import ConfiguracaoSistemaRepository

    alocacao_repo = AlocacaoRepository(session)

    all_alocacoes, _ = await alocacao_repo.search(only_active=True, size=1000)

    alocacoes_por_professor_turma: dict[tuple[str, str], list[Alocacao]] = {}
    for aloc in all_alocacoes:
        key = (str(aloc.professor_id), str(aloc.turma_id))
        alocacoes_por_professor_turma.setdefault(key, []).append(aloc)

    email_content_parts = []

    for (prof_id, turma_id), alocacoes in alocacoes_por_professor_turma.items():
        disciplinas_nao_liberadas = []

        for aloc in alocacoes:
            liberacao = await liberacao_repo.get_by_alocacao_bimestre(
                aloc.id, prazo.bimestre,
            )
            if liberacao is None:
                disciplinas_nao_liberadas.append(aloc.disciplina.nome)

        if not disciplinas_nao_liberadas:
            continue

        turma_codigo = alocacoes[0].turma.codigo
        ano_letivo = alocacoes[0].turma.ano_letivo.ano
        professor_nome = alocacoes[0].professor.usuario.nome

        email_content_parts.append({
            "professor_nome": professor_nome,
            "turma_codigo": turma_codigo,
            "ano_letivo": ano_letivo,
            "disciplinas": disciplinas_nao_liberadas,
        })

    if not email_content_parts:
        await prazo_service.marcar_notificado(prazo.id)
        return

    from app.modules.users.repository import UsuarioRepository

    usuario_repo = UsuarioRepository(session)
    admin = await usuario_repo.get_admin_user()

    if admin is None or not admin.email:
        logger.warning("Nenhum admin com e-mail encontrado para notificação de prazo")
        return

    smtp_repo = ConfiguracaoSistemaRepository(session)
    smtp_config = await smtp_repo.get_all_smtp()

    corpo_html = _montar_html_notificacao(prazo, email_content_parts)
    assunto = f"[ePass] Prazo de liberação de boletim vencido - {prazo.bimestre}º bimestre"

    # Notificação in-app para os administradores (independente do e-mail).
    from app.core.notifications import NotificationDispatcher
    from app.shared.enums import Perfil, TipoNotificacao

    for usuario in await UsuarioRepository(session).get_by_perfis([Perfil.ADMIN]):
        await NotificationDispatcher(session).dispatch(
            usuario_id=usuario.id,
            titulo="Prazo de liberação de boletim vencido",
            corpo=(
                f"O prazo do {prazo.bimestre}º bimestre venceu com "
                f"{len(email_content_parts)} professor(es) com disciplinas pendentes."
            ),
            canal="inapp",
            tipo=TipoNotificacao.BOLETIM,
            entidade_tipo="prazo_liberacao",
            entidade_id=prazo.id,
            evento_key=f"prazo-boletim:{prazo.id}:{usuario.id}",
        )

    enviou = await asyncio.to_thread(
        enviar_email,
        destinatario=admin.email,
        assunto=assunto,
        corpo_html=corpo_html,
        smtp_config=smtp_config,
    )

    if enviou:
        await prazo_service.marcar_notificado(prazo.id)
    else:
        logger.warning("Falha ao enviar notificação de prazo vencido para %s — notificado_em não preenchido", admin.email)


def _montar_html_notificacao(
    prazo: PrazoLiberacao,
    pendencias: list[dict],
) -> str:
    linhas = ""
    for p in pendencias:
        disciplinas = ", ".join(p["disciplinas"])
        linhas += f"""
        <tr>
          <td style="padding:8px;border:1px solid #ddd">{p['professor_nome']}</td>
          <td style="padding:8px;border:1px solid #ddd">{p['turma_codigo']}</td>
          <td style="padding:8px;border:1px solid #ddd">{p['ano_letivo']}</td>
          <td style="padding:8px;border:1px solid #ddd">{disciplinas}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif">
      <h2>Liberação de Boletim - Prazo Vencido</h2>
      <p>O prazo para liberação do <strong>{prazo.bimestre}º bimestre</strong> foi vencido em <strong>{prazo.data_limite.strftime('%d/%m/%Y')} às {prazo.hora_limite.strftime('%H:%M')}</strong>.</p>
      <p>Os seguintes professores ainda possuem disciplinas não liberadas:</p>
      <table style="border-collapse:collapse;width:100%">
        <thead>
          <tr>
            <th style="padding:8px;border:1px solid #ddd;background:#f5f5f5">Professor</th>
            <th style="padding:8px;border:1px solid #ddd;background:#f5f5f5">Turma</th>
            <th style="padding:8px;border:1px solid #ddd;background:#f5f5f5">Ano Letivo</th>
            <th style="padding:8px;border:1px solid #ddd;background:#f5f5f5">Disciplinas Pendentes</th>
          </tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
    </body>
    </html>
    """


async def verificar_prazos_liberacao(session: AsyncSession) -> None:
    """Compat: chamada pelo scheduler antigo se ainda existir. Não é mais usada."""
    pass
