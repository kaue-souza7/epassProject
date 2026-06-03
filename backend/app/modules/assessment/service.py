from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationError
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.assessment.repository import AvaliacaoRepository, NotaRepository
from app.modules.assessment.schemas import AvaliacaoCreate, AvaliacaoUpdate, NotaLancar
from app.modules.allocations.service import AlocacaoService
from app.modules.enrollments.models import Matricula
from app.modules.enrollments.repository import MatriculaRepository


class AvaliacaoService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AvaliacaoRepository(session)
        self._nota_repo = NotaRepository(session)
        self._alocacao_service = AlocacaoService(session)
        self._matricula_repo = MatriculaRepository(session)

    async def criar(self, data: AvaliacaoCreate) -> Avaliacao:
        await self._alocacao_service.get_by_id(data.alocacao_id)

        if await self._repo.exists_by_alocacao_titulo_bimestre(
            data.alocacao_id, data.titulo, data.bimestre,
        ):
            raise Conflict("Já existe avaliação com este título no mesmo bimestre")

        avaliacao = Avaliacao(
            alocacao_id=data.alocacao_id,
            titulo=data.titulo,
            tipo=data.tipo,
            peso=data.peso,
            nota_maxima=data.nota_maxima,
            bimestre=data.bimestre,
            data_aplicacao=data.data_aplicacao,
            observacoes=data.observacoes,
        )
        return await self._repo.create(avaliacao)

    async def atualizar(self, avaliacao_id: uuid.UUID, data: AvaliacaoUpdate) -> Avaliacao:
        avaliacao = await self._repo.get_by_id(avaliacao_id)
        if avaliacao is None:
            raise NotFound("Avaliação não encontrada")

        if data.titulo is not None:
            avaliacao.titulo = data.titulo
        if data.data_aplicacao is not None:
            avaliacao.data_aplicacao = data.data_aplicacao
        if data.observacoes is not None:
            avaliacao.observacoes = data.observacoes

        return await self._repo.update(avaliacao)

    async def lancar_notas(
        self, avaliacao_id: uuid.UUID, notas: list[NotaLancar],
    ) -> list[Nota]:
        avaliacao = await self._repo.get_by_id(avaliacao_id)
        if avaliacao is None:
            raise NotFound("Avaliação não encontrada")

        alocacao = await self._alocacao_service.get_by_id(avaliacao.alocacao_id)
        matriculas_turma = await self._matricula_repo.get_by_turma(alocacao.turma_id)
        matriculas_ids = {m.id for m in matriculas_turma if m.status == "ativa"}

        criadas = []
        for item in notas:
            if item.valor > avaliacao.nota_maxima:
                raise ValidationError(
                    f"Valor {item.valor} ultrapassa nota máxima {avaliacao.nota_maxima}",
                )
            if item.matricula_id not in matriculas_ids:
                raise ValidationError(
                    f"Matrícula {item.matricula_id} não pertence à turma desta avaliação",
                )

            existente = await self._nota_repo.get_by_avaliacao_matricula(
                avaliacao_id, item.matricula_id,
            )
            if existente is not None:
                existente.valor = item.valor
                existente.observacoes = item.observacoes
                await self._nota_repo.update(existente)
                criadas.append(existente)
            else:
                nota = Nota(
                    avaliacao_id=avaliacao.id,
                    matricula_id=item.matricula_id,
                    valor=item.valor,
                    observacoes=item.observacoes,
                )
                criadas.append(nota)

        if all(n.id is None for n in criadas):
            return await self._nota_repo.bulk_create(criadas)
        return criadas

    async def corrigir_nota(
        self, nota_id: uuid.UUID, novo_valor, observacoes: str | None = None,
    ) -> Nota:
        nota = await self._nota_repo.get_by_id(nota_id)
        if nota is None:
            raise NotFound("Nota não encontrada")

        avaliacao = await self._repo.get_by_id(nota.avaliacao_id)
        if novo_valor > avaliacao.nota_maxima:
            raise ValidationError(
                f"Valor {novo_valor} ultrapassa nota máxima {avaliacao.nota_maxima}",
            )

        nota.valor = novo_valor
        if observacoes is not None:
            nota.observacoes = observacoes
        return await self._nota_repo.update(nota)

    async def obter_avaliacao(self, avaliacao_id: uuid.UUID) -> Avaliacao:
        avaliacao = await self._repo.get_by_id(avaliacao_id)
        if avaliacao is None:
            raise NotFound("Avaliação não encontrada")
        return avaliacao

    async def obter_notas_da_avaliacao(self, avaliacao_id: uuid.UUID) -> list[Nota]:
        avaliacao = await self.obter_avaliacao(avaliacao_id)
        return await self._nota_repo.get_by_avaliacao(avaliacao.id)

    async def obter_notas_com_alunos(
        self, avaliacao_id: uuid.UUID,
    ) -> tuple[Avaliacao, list[tuple[Nota | None, Matricula]]]:
        avaliacao = await self.obter_avaliacao(avaliacao_id)
        alocacao = await self._alocacao_service.get_by_id(avaliacao.alocacao_id)
        matriculas = await self._matricula_repo.get_by_turma(alocacao.turma_id)
        notas = await self._nota_repo.get_by_avaliacao(avaliacao.id)

        notas_por_matricula = {n.matricula_id: n for n in notas}

        resultado: list[tuple[Nota | None, Matricula]] = []
        for m in matriculas:
            if m.status != "ativa":
                continue
            nota = notas_por_matricula.get(m.id)
            resultado.append((nota, m))

        return avaliacao, resultado

    async def listar_por_alocacao(
        self, alocacao_id: uuid.UUID, bimestre: int | None = None,
        page: int = 1, size: int = 20,
    ) -> tuple[list[Avaliacao], int]:
        return await self._repo.get_by_alocacao(
            alocacao_id, bimestre=bimestre, page=page, size=size,
        )

    async def listar_por_bimestre(
        self, alocacao_id: uuid.UUID, bimestre: int,
    ) -> list[Avaliacao]:
        return await self._repo.get_by_alocacao_bimestre(alocacao_id, bimestre)
