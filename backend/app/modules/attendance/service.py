from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.attendance.repository import ChamadaRepository, FrequenciaRepository
from app.modules.attendance.schemas import ChamadaAbrir, FrequenciaRegistrar
from app.modules.allocations.service import AlocacaoService
from app.modules.enrollments.repository import MatriculaRepository
from app.shared.enums import StatusFrequencia


class ChamadaService:
    def __init__(self, session: AsyncSession) -> None:
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
