from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, func, select, extract, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.models import Aluno
from app.modules.teachers.models import ProfessorProfile
from app.modules.classes.models import Turma
from app.modules.series.models import Serie
from app.modules.enrollments.models import Matricula
from app.modules.allocations.models import Alocacao
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.users.models import Usuario
from app.modules.subjects.models import Disciplina
from app.shared.enums import StatusMatricula, StatusFrequencia, TipoAvaliacao


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_alunos_ativos(self) -> int:
        result = await self._session.execute(
            select(func.count(Aluno.id)).where(Aluno.ativo.is_(True)),
        )
        return result.scalar_one()

    async def count_professores_ativos(self) -> int:
        result = await self._session.execute(
            select(func.count(ProfessorProfile.usuario_id)).where(
                ProfessorProfile.ativo.is_(True),
            ),
        )
        return result.scalar_one()

    async def count_turmas_ativas(self) -> int:
        result = await self._session.execute(
            select(func.count(Turma.id)).where(Turma.ativo.is_(True)),
        )
        return result.scalar_one()

    async def count_matriculas_ativas(self) -> int:
        result = await self._session.execute(
            select(func.count(Matricula.id)).where(
                Matricula.status == StatusMatricula.ATIVA,
            ),
        )
        return result.scalar_one()

    async def ultimas_matriculas(self, limit: int = 5) -> list[dict]:
        query = (
            select(Matricula, Aluno.nome, Turma.codigo)
            .join(Aluno, Matricula.aluno_id == Aluno.id)
            .join(Turma, Matricula.turma_id == Turma.id)
            .order_by(Matricula.data_matricula.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [
            {
                "id": m.Matricula.id,
                "aluno_nome": m.nome,
                "turma_codigo": m.codigo,
                "data_matricula": m.Matricula.data_matricula,
                "status": m.Matricula.status.value,
            }
            for m in result.all()
        ]

    async def ultimas_alocacoes(self, limit: int = 5) -> list[dict]:
        query = (
            select(
                Alocacao,
                Usuario.nome.label("professor_nome"),
                Turma.codigo.label("turma_codigo"),
                Disciplina.nome.label("disciplina_nome"),
            )
            .join(Usuario, Alocacao.professor_id == Usuario.id)
            .join(Turma, Alocacao.turma_id == Turma.id)
            .join(Disciplina, Alocacao.disciplina_id == Disciplina.id)
            .order_by(Alocacao.data_inicio.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [
            {
                "id": r.Alocacao.id,
                "professor_nome": r.professor_nome,
                "turma_codigo": r.turma_codigo,
                "disciplina_nome": r.disciplina_nome,
                "data_inicio": r.Alocacao.data_inicio,
            }
            for r in result.all()
        ]

    async def top_ocupacao(self, limit: int = 10) -> list[dict]:
        subq = (
            select(
                Matricula.turma_id,
                func.count(Matricula.id).label("matriculas_ativas"),
            )
            .where(Matricula.status == StatusMatricula.ATIVA)
            .group_by(Matricula.turma_id)
            .subquery()
        )
        query = (
            select(
                Turma.id,
                Turma.codigo,
                Turma.vagas_total,
                func.coalesce(subq.c.matriculas_ativas, 0).label("matriculas_ativas"),
            )
            .outerjoin(subq, Turma.id == subq.c.turma_id)
            .where(Turma.ativo.is_(True))
        )
        result = await self._session.execute(query)
        rows = result.all()

        data = []
        for r in rows:
            taxa = (r.matriculas_ativas / r.vagas_total * 100) if r.vagas_total > 0 else 0
            data.append({
                "turma_id": r.id,
                "turma_codigo": r.codigo,
                "vagas_total": r.vagas_total,
                "matriculas_ativas": r.matriculas_ativas,
                "taxa_ocupacao": round(taxa, 2),
            })
        data.sort(key=lambda x: x["taxa_ocupacao"], reverse=True)
        return data[:limit]

    async def alunos_por_serie(self) -> list[dict]:
        query = (
            select(
                Serie.id,
                Serie.nome,
                func.count(Matricula.id).label("quantidade"),
            )
            .select_from(Matricula)
            .join(Turma, Matricula.turma_id == Turma.id)
            .join(Serie, Turma.serie_id == Serie.id)
            .where(Matricula.status == StatusMatricula.ATIVA)
            .group_by(Serie.id, Serie.nome)
            .order_by(Serie.nome)
        )
        result = await self._session.execute(query)
        return [
            {"serie_id": r.id, "serie_nome": r.nome, "quantidade": r.quantidade}
            for r in result.all()
        ]

    async def count_matriculas_ano(self, ano: int) -> int:
        result = await self._session.execute(
            select(func.count(Matricula.id)).where(
                extract("year", Matricula.data_matricula) == ano,
            ),
        )
        return result.scalar_one()

    async def alunos_sem_matricula(self) -> int:
        subq = select(Matricula.aluno_id).where(
            Matricula.status == StatusMatricula.ATIVA,
        )
        result = await self._session.execute(
            select(func.count(Aluno.id)).where(
                and_(Aluno.ativo.is_(True), ~Aluno.id.in_(subq)),
            ),
        )
        return result.scalar_one()

    async def turmas_lotadas(self) -> list[dict]:
        subq = (
            select(
                Matricula.turma_id,
                func.count(Matricula.id).label("matriculas_ativas"),
            )
            .where(Matricula.status == StatusMatricula.ATIVA)
            .group_by(Matricula.turma_id)
            .subquery()
        )
        query = (
            select(
                Turma.id,
                Turma.codigo,
                Turma.vagas_total,
                func.coalesce(subq.c.matriculas_ativas, 0).label("matriculas_ativas"),
            )
            .outerjoin(subq, Turma.id == subq.c.turma_id)
            .where(
                and_(
                    Turma.ativo.is_(True),
                    func.coalesce(subq.c.matriculas_ativas, 0) >= Turma.vagas_total,
                ),
            )
            .order_by(Turma.codigo)
        )
        result = await self._session.execute(query)
        return [
            {
                "turma_id": r.id,
                "turma_codigo": r.codigo,
                "vagas_total": r.vagas_total,
                "matriculas_ativas": r.matriculas_ativas,
            }
            for r in result.all()
        ]

    async def count_minhas_turmas(self, professor_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(func.distinct(Alocacao.turma_id))).where(
                and_(
                    Alocacao.professor_id == professor_id,
                    Alocacao.data_fim.is_(None),
                ),
            ),
        )
        return result.scalar_one()

    async def count_minhas_disciplinas(self, professor_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(func.distinct(Alocacao.disciplina_id))).where(
                and_(
                    Alocacao.professor_id == professor_id,
                    Alocacao.data_fim.is_(None),
                ),
            ),
        )
        return result.scalar_one()

    async def count_chamadas_realizadas(self, professor_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(Chamada.id))
            .join(Alocacao, Chamada.alocacao_id == Alocacao.id)
            .where(Alocacao.professor_id == professor_id),
        )
        return result.scalar_one()

    async def count_avaliacoes_cadastradas(self, professor_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(Avaliacao.id))
            .join(Alocacao, Avaliacao.alocacao_id == Alocacao.id)
            .where(Alocacao.professor_id == professor_id),
        )
        return result.scalar_one()

    async def proximas_avaliacoes(
        self, professor_id: uuid.UUID, limit: int = 5,
    ) -> list[dict]:
        today = date.today()
        query = (
            select(
                Avaliacao,
                Disciplina.nome.label("disciplina_nome"),
                Turma.codigo.label("turma_codigo"),
            )
            .join(Alocacao, Avaliacao.alocacao_id == Alocacao.id)
            .join(Disciplina, Alocacao.disciplina_id == Disciplina.id)
            .join(Turma, Alocacao.turma_id == Turma.id)
            .where(
                and_(
                    Alocacao.professor_id == professor_id,
                    Avaliacao.data_aplicacao >= today,
                ),
            )
            .order_by(Avaliacao.data_aplicacao)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [
            {
                "id": r.Avaliacao.id,
                "titulo": r.Avaliacao.titulo,
                "disciplina_nome": r.disciplina_nome,
                "turma_codigo": r.turma_codigo,
                "data_aplicacao": r.Avaliacao.data_aplicacao,
                "bimestre": r.Avaliacao.bimestre,
            }
            for r in result.all()
        ]

    async def ultimas_chamadas(
        self, professor_id: uuid.UUID, limit: int = 5,
    ) -> list[dict]:
        query = (
            select(
                Chamada,
                Disciplina.nome.label("disciplina_nome"),
                Turma.codigo.label("turma_codigo"),
            )
            .join(Alocacao, Chamada.alocacao_id == Alocacao.id)
            .join(Disciplina, Alocacao.disciplina_id == Disciplina.id)
            .join(Turma, Alocacao.turma_id == Turma.id)
            .where(Alocacao.professor_id == professor_id)
            .order_by(Chamada.data_hora_aula.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [
            {
                "id": r.Chamada.id,
                "disciplina_nome": r.disciplina_nome,
                "turma_codigo": r.turma_codigo,
                "data_hora_aula": r.Chamada.data_hora_aula,
            }
            for r in result.all()
        ]

    async def get_matriculas_ativas_por_aluno(
        self, aluno_ids: list[uuid.UUID],
    ) -> dict:
        if not aluno_ids:
            return {}
        result = await self._session.execute(
            select(Matricula, Turma.codigo)
            .join(Turma, Matricula.turma_id == Turma.id)
            .where(
                and_(
                    Matricula.aluno_id.in_(aluno_ids),
                    Matricula.status == StatusMatricula.ATIVA,
                ),
            ),
        )
        return {
            r.Matricula.aluno_id: {
                "matricula_id": r.Matricula.id,
                "turma_codigo": r.codigo,
                "matricula": r.Matricula,
            }
            for r in result.all()
        }

    async def media_geral_matricula(
        self, matricula_id: uuid.UUID,
        exclude_recuperacao: bool = False,
    ) -> float | None:
        query = (
            select(
                func.sum(Nota.valor * Avaliacao.peso).label("soma_ponderada"),
                func.sum(Avaliacao.peso).label("total_pesos"),
            )
            .select_from(Nota)
            .join(Avaliacao, Nota.avaliacao_id == Avaliacao.id)
            .join(Alocacao, Avaliacao.alocacao_id == Alocacao.id)
            .where(
                and_(
                    Nota.matricula_id == matricula_id,
                    Alocacao.turma_id == select(Matricula.turma_id).where(
                        Matricula.id == matricula_id,
                    ).scalar_subquery(),
                ),
            )
        )
        if exclude_recuperacao:
            query = query.where(Avaliacao.tipo != TipoAvaliacao.RECUPERACAO)

        result = await self._session.execute(query)
        row = result.one()
        if row.total_pesos and row.total_pesos > 0:
            return round(float(row.soma_ponderada) / float(row.total_pesos), 2)
        return None

    async def frequencia_media_matricula(
        self, matricula_id: uuid.UUID,
    ) -> float | None:
        chamada_ids_subq = (
            select(Chamada.id)
            .join(Alocacao, Chamada.alocacao_id == Alocacao.id)
            .where(Alocacao.turma_id == (
                select(Matricula.turma_id).where(Matricula.id == matricula_id)
            ).scalar_subquery())
        ).subquery()

        count_query = select(func.count(Frequencia.id)).where(
            and_(
                Frequencia.matricula_id == matricula_id,
                Frequencia.chamada_id.in_(select(chamada_ids_subq)),
            ),
        )
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()
        if total == 0:
            return None

        presente_query = select(func.count(Frequencia.id)).where(
            and_(
                Frequencia.matricula_id == matricula_id,
                Frequencia.chamada_id.in_(select(chamada_ids_subq)),
                Frequencia.status.in_([
                    StatusFrequencia.PRESENTE,
                    StatusFrequencia.FALTA_JUSTIFICADA,
                ]),
            ),
        )
        presente_result = await self._session.execute(presente_query)
        presentes = presente_result.scalar_one()

        return round(presentes / total * 100, 2)
