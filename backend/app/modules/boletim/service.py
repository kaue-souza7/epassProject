from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFound, Forbidden
from app.modules.allocations.models import Alocacao
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.boletim.models import LiberacaoBoletim, PrazoLiberacao
from app.modules.boletim.repository import LiberacaoBoletimRepository, PrazoLiberacaoRepository
from app.modules.boletim.schemas import (
    LiberacaoBoletimRequest,
    LiberacaoBoletimResponse,
    LiberacaoStatusResponse,
    DisciplinaLiberacaoStatus,
    PrazoLiberacaoRequest,
    PrazoLiberacaoResponse,
    PrazoLiberacaoUpdate,
)
from app.modules.classes.models import Turma

logger = logging.getLogger(__name__)


class LiberacaoBoletimService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._liberacao_repo = LiberacaoBoletimRepository(session)
        self._prazo_repo = PrazoLiberacaoRepository(session)
        self._alocacao_repo = AlocacaoRepository(session)

    async def liberar(
        self,
        professor_id: uuid.UUID,
        body: LiberacaoBoletimRequest,
    ) -> list[LiberacaoBoletimResponse]:
        alocacoes, _ = await self._alocacao_repo.search(
            professor_id=professor_id,
            turma_id=body.turma_id,
            only_active=True,
            size=100,
        )

        if not alocacoes:
            raise NotFound("Nenhuma alocação ativa encontrada para esta turma")

        ano_letivo_id = alocacoes[0].turma.ano_letivo_id

        liberacoes_criadas = []
        for aloc in alocacoes:
            existente = await self._liberacao_repo.get_by_alocacao_bimestre(
                aloc.id, body.bimestre,
            )
            if existente is not None:
                continue

            liberacao = LiberacaoBoletim(
                professor_id=professor_id,
                turma_id=body.turma_id,
                disciplina_id=aloc.disciplina_id,
                alocacao_id=aloc.id,
                ano_letivo_id=ano_letivo_id,
                bimestre=body.bimestre,
            )
            liberacao = await self._liberacao_repo.create(liberacao)
            liberacoes_criadas.append(liberacao)

        if liberacoes_criadas:
            await self._notificar_liberacao(
                turma=alocacoes[0].turma,
                professor_id=professor_id,
                bimestre=body.bimestre,
            )

        return [
            LiberacaoBoletimResponse(
                id=l.id,
                professor_id=l.professor_id,
                turma_id=l.turma_id,
                disciplina_id=l.disciplina_id,
                disciplina_nome=l.alocacao.disciplina.nome,
                alocacao_id=l.alocacao_id,
                ano_letivo_id=l.ano_letivo_id,
                bimestre=l.bimestre,
                liberado_em=l.liberado_em,
                ativo=l.ativo,
            )
            for l in liberacoes_criadas
        ]

    async def obter_status(
        self,
        professor_id: uuid.UUID,
        turma_id: uuid.UUID,
        bimestre: int,
    ) -> LiberacaoStatusResponse:
        alocacoes, _ = await self._alocacao_repo.search(
            professor_id=professor_id,
            turma_id=turma_id,
            only_active=True,
            size=100,
        )

        if not alocacoes:
            raise NotFound("Nenhuma alocação ativa encontrada para esta turma")

        liberacoes = await self._liberacao_repo.get_by_professor_turma_bimestre(
            professor_id, turma_id, bimestre,
        )
        liberadas_map = {l.alocacao_id: l for l in liberacoes}

        disciplinas_status = []
        for aloc in alocacoes:
            liberada = aloc.id in liberadas_map
            liberacao = liberadas_map.get(aloc.id)
            disciplinas_status.append(DisciplinaLiberacaoStatus(
                disciplina_id=aloc.disciplina_id,
                disciplina_nome=aloc.disciplina.nome,
                liberada=liberada,
                liberado_em=liberacao.liberado_em if liberacao else None,
            ))

        return LiberacaoStatusResponse(
            turma_id=turma_id,
            turma_codigo=alocacoes[0].turma.codigo,
            bimestre=bimestre,
            ano_letivo_id=alocacoes[0].turma.ano_letivo_id,
            total_disciplinas_professor=len(alocacoes),
            disciplinas_liberadas=disciplinas_status,
            todas_liberadas=all(d.liberada for d in disciplinas_status),
        )

    async def verificar_liberacao_para_responsavel(
        self,
        alocacao_id: uuid.UUID,
        bimestre: int,
    ) -> bool:
        return await self._liberacao_repo.is_alocacao_liberada(alocacao_id, bimestre)

    async def _notificar_liberacao(
        self,
        turma: Turma,
        professor_id: uuid.UUID,
        bimestre: int,
    ) -> None:
        """Notifica os responsáveis da turma sobre a liberação do boletim.

        Idempotente por (turma, bimestre, professor): repetir a requisição não
        duplica a notificação.
        """
        from sqlalchemy import select

        from app.core.notifications import NotificationDispatcher
        from app.modules.enrollments.models import Matricula
        from app.modules.students.models import ResponsavelAluno
        from app.shared.enums import StatusMatricula, TipoNotificacao

        result = await self._session.execute(
            select(ResponsavelAluno.responsavel_id)
            .distinct()
            .join(Matricula, Matricula.aluno_id == ResponsavelAluno.aluno_id)
            .where(
                Matricula.turma_id == turma.id,
                Matricula.status == StatusMatricula.ATIVA,
            ),
        )
        responsaveis = list(result.scalars().all())
        if not responsaveis:
            return

        dispatcher = NotificationDispatcher(self._session)
        for responsavel_id in responsaveis:
            await dispatcher.dispatch(
                usuario_id=responsavel_id,
                titulo="Boletim liberado",
                corpo=f"O boletim do {bimestre}º bimestre da turma {turma.codigo} está disponível.",
                canal="inapp",
                tipo=TipoNotificacao.BOLETIM,
                entidade_tipo="turma",
                entidade_id=turma.id,
                evento_key=f"boletim-liberado:{turma.id}:{bimestre}:{professor_id}:{responsavel_id}",
            )


class PrazoLiberacaoService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._prazo_repo = PrazoLiberacaoRepository(session)

    async def criar(self, body: PrazoLiberacaoRequest) -> PrazoLiberacaoResponse:
        existente = await self._prazo_repo.get_by_ano_bimestre(
            body.ano_letivo_id, body.bimestre,
        )
        if existente:
            raise AppException(
                f"Já existe prazo configurado para o bimestre {body.bimestre} neste ano letivo"
            )

        prazo = PrazoLiberacao(
            ano_letivo_id=body.ano_letivo_id,
            bimestre=body.bimestre,
            data_limite=body.data_limite,
            hora_limite=body.hora_limite,
        )
        prazo = await self._prazo_repo.create(prazo)
        return PrazoLiberacaoResponse.model_validate(prazo)

    async def listar_por_ano(
        self,
        ano_letivo_id: uuid.UUID,
    ) -> list[PrazoLiberacaoResponse]:
        prazos = await self._prazo_repo.get_by_ano_letivo(ano_letivo_id)
        return [PrazoLiberacaoResponse.model_validate(p) for p in prazos]

    async def atualizar(
        self,
        prazo_id: uuid.UUID,
        body: PrazoLiberacaoUpdate,
    ) -> PrazoLiberacaoResponse:
        from sqlalchemy import select

        result = await self._session.execute(
            select(PrazoLiberacao).where(PrazoLiberacao.id == prazo_id),
        )
        prazo = result.scalar_one_or_none()
        if prazo is None:
            raise NotFound("Prazo não encontrado")

        if body.data_limite is not None:
            prazo.data_limite = body.data_limite
        if body.hora_limite is not None:
            prazo.hora_limite = body.hora_limite
        if body.ativo is not None:
            prazo.ativo = body.ativo

        prazo = await self._prazo_repo.update(prazo)
        return PrazoLiberacaoResponse.model_validate(prazo)

    async def marcar_notificado(
        self,
        prazo_id: uuid.UUID,
    ) -> None:
        from sqlalchemy import select

        result = await self._session.execute(
            select(PrazoLiberacao).where(PrazoLiberacao.id == prazo_id),
        )
        prazo = result.scalar_one_or_none()
        if prazo:
            prazo.notificado_em = datetime.now(timezone.utc)
            await self._prazo_repo.update(prazo)
