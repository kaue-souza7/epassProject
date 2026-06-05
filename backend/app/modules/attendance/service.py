from __future__ import annotations

import uuid
from datetime import date, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.modules.allocations.models import Alocacao
from app.modules.enrollments.models import Matricula
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.attendance.repository import ChamadaRepository, FrequenciaRepository
from app.modules.attendance.schemas import ChamadaAbrir, FrequenciaRegistrar, FrequenciaResumoResponse
from app.modules.allocations.service import AlocacaoService
from app.modules.dashboard.repository import DashboardRepository
from app.modules.enrollments.repository import MatriculaRepository
from app.shared.enums import StatusFrequencia


class ChamadaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ChamadaRepository(session)
        self._freq_repo = FrequenciaRepository(session)
        self._alocacao_service = AlocacaoService(session)
        self._matricula_repo = MatriculaRepository(session)

    async def abrir_chamada(self, data: ChamadaAbrir) -> Chamada:
        await self._alocacao_service.get_by_id(data.alocacao_id)

        if await self._repo.exists_by_aula(data.alocacao_id, data.data_hora_aula):
            raise Conflict("Já existe chamada registrada para esta aula")

        chamada = Chamada(
            alocacao_id=data.alocacao_id,
            data_hora_aula=data.data_hora_aula,
        )
        chamada = await self._repo.create(chamada)

        alocacao = await self._alocacao_service.get_by_id(data.alocacao_id)
        matriculas = await self._matricula_repo.get_by_turma(alocacao.turma_id)
        matriculas_ativas = [m for m in matriculas if m.status == "ativa"]

        frequencias = [
            Frequencia(
                chamada_id=chamada.id,
                matricula_id=m.id,
                status=StatusFrequencia.PRESENTE,
            )
            for m in matriculas_ativas
        ]
        await self._freq_repo.bulk_create(frequencias)
        return chamada

    async def registrar_frequencias(
        self, chamada_id: uuid.UUID, frequencias: list[FrequenciaRegistrar],
    ) -> None:
        chamada = await self._repo.get_by_id(chamada_id)
        if chamada is None:
            raise NotFound("Chamada não encontrada")

        existentes = await self._freq_repo.get_by_chamada(chamada_id)
        for item in frequencias:
            target = next(
                (f for f in existentes if f.matricula_id == item.matricula_id), None,
            )
            if target is not None:
                target.status = item.status
                target.observacoes = item.observacoes
                await self._freq_repo.update(target)

    async def justificar_falta(self, frequencia_id: uuid.UUID, observacoes: str) -> Frequencia:
        target = await self._freq_repo.get_by_id(frequencia_id)
        if target is None:
            raise NotFound("Registro de frequência não encontrado")
        if target.status != StatusFrequencia.FALTA:
            raise Conflict("Apenas faltas podem ser justificadas")
        target.status = StatusFrequencia.FALTA_JUSTIFICADA
        target.observacoes = observacoes
        return await self._freq_repo.update(target)

    async def obter_chamada(self, chamada_id: uuid.UUID) -> Chamada:
        chamada = await self._repo.get_by_id(chamada_id)
        if chamada is None:
            raise NotFound("Chamada não encontrada")
        return chamada

    async def listar_por_alocacao(
        self, alocacao_id: uuid.UUID, page: int = 1, size: int = 20,
    ) -> tuple[list[Chamada], int]:
        return await self._repo.get_by_alocacao(alocacao_id, page=page, size=size)

    async def resumo_frequencia_responsavel(
        self, matricula_id: uuid.UUID,
    ) -> FrequenciaResumoResponse:
        matricula = await self._matricula_repo.get_by_id(matricula_id)
        if matricula is None:
            raise NotFound("Matrícula não encontrada")

        dashboard_repo = DashboardRepository(self._session)

        frequencia_media = await dashboard_repo.frequencia_media_matricula(matricula_id)

        chamada_ids_subq = (
            select(Chamada.id)
            .join(Alocacao, Chamada.alocacao_id == Alocacao.id)
            .where(Alocacao.turma_id == (
                select(Matricula.turma_id).where(Matricula.id == matricula_id)
            ).scalar_subquery())
        ).subquery()

        all_freq = await self._session.execute(
            select(Frequencia).where(
                and_(
                    Frequencia.matricula_id == matricula_id,
                    Frequencia.chamada_id.in_(select(chamada_ids_subq)),
                ),
            ),
        )
        todas = list(all_freq.scalars().all())

        total_aulas = len(todas)
        presencas = sum(1 for f in todas if f.status == StatusFrequencia.PRESENTE)
        faltas = sum(1 for f in todas if f.status == StatusFrequencia.FALTA)
        faltas_justificadas = sum(
            1 for f in todas if f.status == StatusFrequencia.FALTA_JUSTIFICADA
        )

        hoje = date.today()
        freq_hoje = await self._session.execute(
            select(Frequencia)
            .join(Chamada, Frequencia.chamada_id == Chamada.id)
            .where(
                and_(
                    Frequencia.matricula_id == matricula_id,
                    func.date(Chamada.data_hora_aula) == hoje,
                ),
            ),
        )
        freq_hoje_row = freq_hoje.scalar_one_or_none()
        situacao_hoje = freq_hoje_row.status.value if freq_hoje_row else None

        return FrequenciaResumoResponse(
            matricula_id=matricula_id,
            aluno_id=matricula.aluno_id,
            aluno_nome=matricula.aluno.nome if matricula.aluno else None,
            turma_codigo=matricula.turma.codigo if matricula.turma else None,
            frequencia_media=frequencia_media,
            total_aulas=total_aulas,
            presencas=presencas,
            faltas=faltas,
            faltas_justificadas=faltas_justificadas,
            situacao_hoje=situacao_hoje,
        )
