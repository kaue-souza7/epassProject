from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.allocations.models import Alocacao
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.assessment.repository import AvaliacaoRepository, NotaRepository
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.attendance.repository import ChamadaRepository, FrequenciaRepository
from app.modules.classes.models import Turma
from app.modules.enrollments.models import Matricula
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.subjects.models import Disciplina
from app.shared.enums import StatusFrequencia


class ProfessorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._alocacao_repo = AlocacaoRepository(session)
        self._matricula_repo = MatriculaRepository(session)
        self._chamada_repo = ChamadaRepository(session)
        self._freq_repo = FrequenciaRepository(session)
        self._avaliacao_repo = AvaliacaoRepository(session)
        self._nota_repo = NotaRepository(session)

    async def get_turmas(self, professor_id: uuid.UUID) -> list[dict]:
        alocacoes, _ = await self._alocacao_repo.search(
            professor_id=professor_id,
            only_active=True,
            size=100,
        )
        result = []
        for aloc in alocacoes:
            turma = aloc.turma
            disciplina = aloc.disciplina
            total = await self._matricula_repo.count_active_by_turma(turma.id)
            result.append({
                "alocacao_id": str(aloc.id),
                "turma_id": str(turma.id),
                "turma_codigo": turma.codigo,
                "turma_nome": turma.nome,
                "disciplina_id": str(disciplina.id),
                "disciplina_nome": disciplina.nome,
                "serie_nome": turma.serie.nome if turma.serie else "",
                "ano_letivo": turma.ano_letivo.ano if turma.ano_letivo else 0,
                "turno": turma.turno.value if turma.turno else "",
                "total_alunos": total,
            })
        return result

    async def get_turma_alunos(self, turma_id: uuid.UUID) -> list[dict]:
        rows, _ = await self._matricula_repo.search(
            turma_id=turma_id,
            size=100,
        )
        result = []
        for matricula, aluno_nome, _ in rows:
            if matricula.status != "ativa":
                continue
            result.append({
                "matricula_id": str(matricula.id),
                "aluno_id": str(matricula.aluno_id),
                "aluno_nome": aluno_nome,
                "numero_chamada": None,
            })
        return result

    async def get_avaliacoes(
        self, alocacao_id: uuid.UUID, bimestre: int | None = None,
    ) -> list[dict]:
        query = select(Avaliacao).where(Avaliacao.alocacao_id == alocacao_id)
        if bimestre is not None:
            query = query.where(Avaliacao.bimestre == bimestre)
        query = query.order_by(Avaliacao.data_aplicacao.desc())
        result = await self._session.execute(query)
        avaliacoes = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "alocacao_id": str(a.alocacao_id),
                "titulo": a.titulo,
                "tipo": a.tipo.value,
                "peso": a.peso,
                "nota_maxima": float(a.nota_maxima),
                "bimestre": a.bimestre,
                "data_aplicacao": a.data_aplicacao.isoformat(),
            }
            for a in avaliacoes
        ]

    async def salvar_frequencia(
        self, professor_id: uuid.UUID, turma_id: uuid.UUID,
        data: date, presencas: list[dict],
    ) -> dict:
        query = (
            select(Alocacao)
            .where(
                and_(
                    Alocacao.professor_id == professor_id,
                    Alocacao.turma_id == turma_id,
                    Alocacao.data_fim.is_(None),
                ),
            )
            .limit(1)
        )
        result = await self._session.execute(query)
        alocacao = result.scalar_one_or_none()
        if alocacao is None:
            raise ValueError("Nenhuma alocação ativa encontrada para esta turma")

        data_hora = datetime.combine(data, datetime.min.time(), tzinfo=timezone.utc)

        # Verificar se já existe uma chamada para esta alocação e data
        query_chamada = (
            select(Chamada)
            .where(
                and_(
                    Chamada.alocacao_id == alocacao.id,
                    Chamada.data_hora_aula == data_hora,
                )
            )
            .limit(1)
        )
        res_chamada = await self._session.execute(query_chamada)
        chamada = res_chamada.scalar_one_or_none()

        if chamada is None:
            chamada = Chamada(
                alocacao_id=alocacao.id,
                data_hora_aula=data_hora,
            )
            chamada = await self._chamada_repo.create(chamada)

            frequencias = []
            for item in presencas:
                val = item["matricula_id"]
                matricula_id = val if isinstance(val, uuid.UUID) else uuid.UUID(val)
                freq = Frequencia(
                    chamada_id=chamada.id,
                    matricula_id=matricula_id,
                    status=StatusFrequencia.PRESENTE if item["presente"] else StatusFrequencia.FALTA,
                )
                frequencias.append(freq)
            await self._freq_repo.bulk_create(frequencias)
        else:
            # Obter frequências existentes para esta chamada
            existing_freqs = await self._freq_repo.get_by_chamada(chamada.id)
            existing_map = {f.matricula_id: f for f in existing_freqs}

            for item in presencas:
                val = item["matricula_id"]
                matricula_id = val if isinstance(val, uuid.UUID) else uuid.UUID(val)
                status = StatusFrequencia.PRESENTE if item["presente"] else StatusFrequencia.FALTA

                if matricula_id in existing_map:
                    freq = existing_map[matricula_id]
                    freq.status = status
                    await self._freq_repo.update(freq)
                else:
                    new_freq = Frequencia(
                        chamada_id=chamada.id,
                        matricula_id=matricula_id,
                        status=status,
                    )
                    self._session.add(new_freq)
            
            await self._session.flush()

        return {"chamada_id": str(chamada.id), "message": "Frequência salva com sucesso"}

    async def salvar_notas(
        self, avaliacao_id: uuid.UUID, notas: list[dict],
    ) -> None:
        avaliacao = await self._avaliacao_repo.get_by_id(avaliacao_id)
        if avaliacao is None:
            raise ValueError("Avaliação não encontrada")

        existing = await self._nota_repo.get_by_avaliacao(avaliacao_id)
        existing_map = {n.matricula_id: n for n in existing}

        for item in notas:
            val = item["matricula_id"]
            matricula_id = val if isinstance(val, uuid.UUID) else uuid.UUID(val)
            valor = item["valor"]
            if matricula_id in existing_map:
                nota = existing_map[matricula_id]
                nota.valor = valor
                await self._nota_repo.update(nota)
            else:
                nota = Nota(
                    avaliacao_id=avaliacao_id,
                    matricula_id=matricula_id,
                    valor=valor,
                )
                self._session.add(nota)

        await self._session.flush()
