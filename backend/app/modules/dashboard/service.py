from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    AdminCards,
    AdminDashboardResponse,
    AlocacaoResumo,
    AlunosPorSerie,
    AvaliacaoResumo,
    ChamadaResumo,
    FilhoResumo,
    MatriculaResumo,
    OcupacaoTurma,
    ProfessorCards,
    ProfessorDashboardResponse,
    ResponsavelCards,
    ResponsavelDashboardResponse,
    SecretariaCards,
    SecretariaDashboardResponse,
    TurmaLotada,
)
from app.modules.academic_config.service import ConfiguracaoAcademicaService
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.students.repository import ResponsavelAlunoRepository
from app.shared.enums import SituacaoAluno, TipoAvaliacao
from sqlalchemy import and_, select


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DashboardRepository(session)
        self._matricula_repo = MatriculaRepository(session)
        self._resp_repo = ResponsavelAlunoRepository(session)

    async def admin_dashboard(self) -> AdminDashboardResponse:
        cards = AdminCards(
            total_alunos_ativos=await self._repo.count_alunos_ativos(),
            total_professores_ativos=await self._repo.count_professores_ativos(),
            total_turmas_ativas=await self._repo.count_turmas_ativas(),
            total_matriculas_ativas=await self._repo.count_matriculas_ativas(),
        )
        ultimas_matriculas = [
            MatriculaResumo(**m) for m in await self._repo.ultimas_matriculas()
        ]
        ultimas_alocacoes = [
            AlocacaoResumo(**a) for a in await self._repo.ultimas_alocacoes()
        ]
        top_ocupacao = [
            OcupacaoTurma(**t) for t in await self._repo.top_ocupacao()
        ]
        alunos_por_serie = [
            AlunosPorSerie(**s) for s in await self._repo.alunos_por_serie()
        ]
        return AdminDashboardResponse(
            cards=cards,
            ultimas_matriculas=ultimas_matriculas,
            ultimas_alocacoes=ultimas_alocacoes,
            top_ocupacao=top_ocupacao,
            alunos_por_serie=alunos_por_serie,
        )

    async def secretaria_dashboard(self) -> SecretariaDashboardResponse:
        cards = SecretariaCards(
            matriculas_ativas=await self._repo.count_matriculas_ativas(),
            matriculas_ano=await self._repo.count_matriculas_ano(2026),
            turmas_ativas=await self._repo.count_turmas_ativas(),
            alunos_sem_matricula=await self._repo.alunos_sem_matricula(),
        )
        matriculas_recentes = [
            MatriculaResumo(**m) for m in await self._repo.ultimas_matriculas()
        ]
        turmas_lotadas = [
            TurmaLotada(**t) for t in await self._repo.turmas_lotadas()
        ]
        return SecretariaDashboardResponse(
            cards=cards,
            matriculas_recentes=matriculas_recentes,
            turmas_lotadas=turmas_lotadas,
        )

    async def professor_dashboard(
        self, professor_id: uuid.UUID,
    ) -> ProfessorDashboardResponse:
        cards = ProfessorCards(
            minhas_turmas=await self._repo.count_minhas_turmas(professor_id),
            minhas_disciplinas=await self._repo.count_minhas_disciplinas(professor_id),
            chamadas_realizadas=await self._repo.count_chamadas_realizadas(professor_id),
            avaliacoes_cadastradas=await self._repo.count_avaliacoes_cadastradas(professor_id),
        )
        proximas_avaliacoes = [
            AvaliacaoResumo(**a) for a in await self._repo.proximas_avaliacoes(professor_id)
        ]
        ultimas_chamadas = [
            ChamadaResumo(**c) for c in await self._repo.ultimas_chamadas(professor_id)
        ]
        return ProfessorDashboardResponse(
            cards=cards,
            proximas_avaliacoes=proximas_avaliacoes,
            ultimas_chamadas=ultimas_chamadas,
        )

    async def responsavel_dashboard(
        self, responsavel_id: uuid.UUID,
    ) -> ResponsavelDashboardResponse:
        vinculos = await self._resp_repo.get_by_responsavel(responsavel_id)
        aluno_ids = [v.aluno_id for v in vinculos]
        quantidade_filhos = len(aluno_ids)

        matricula_map = await self._repo.get_matriculas_ativas_por_aluno(aluno_ids)
        matriculas_ativas_count = len(matricula_map)

        config_service = ConfiguracaoAcademicaService(self._matricula_repo._session)

        medias = []
        frequencias = []
        filhos = []

        for aluno_id in aluno_ids:
            info = matricula_map.get(aluno_id)
            matricula_id = info["matricula_id"] if info else None
            turma_codigo = info["turma_codigo"] if info else None

            filho = FilhoResumo(
                aluno_id=aluno_id,
                aluno_nome=next(
                    (v for v in vinculos if v.aluno_id == aluno_id),
                    None,
                ).aluno.nome if any(v.aluno_id == aluno_id for v in vinculos) else "desconhecido",
                matricula_id=matricula_id,
                turma_codigo=turma_codigo,
            )

            if matricula_id:
                media = await self._repo.media_geral_matricula(matricula_id)
                media_sem_rec = await self._repo.media_geral_matricula(matricula_id, exclude_recuperacao=True)
                freq = await self._repo.frequencia_media_matricula(matricula_id)
                filho.media_geral = media
                filho.frequencia_media = freq

                if media is not None:
                    medias.append(media)
                if freq is not None:
                    frequencias.append(freq)

                try:
                    config = await config_service.obter_por_matricula(matricula_id)
                    if media_sem_rec is not None and freq is not None:
                        if media_sem_rec >= float(config.media_aprovacao) and freq >= float(config.frequencia_minima):
                            filho.situacao = SituacaoAluno.APROVADO
                        elif freq < float(config.frequencia_minima):
                            filho.situacao = SituacaoAluno.REPROVADO
                        elif not config.possui_recuperacao:
                            filho.situacao = SituacaoAluno.REPROVADO
                        elif config.media_minima_recuperacao is not None and media_sem_rec < float(config.media_minima_recuperacao):
                            filho.situacao = SituacaoAluno.REPROVADO
                        else:
                            recovery_result = await self._matricula_repo._session.execute(
                                select(Nota)
                                .join(Avaliacao, Nota.avaliacao_id == Avaliacao.id)
                                .where(
                                    and_(
                                        Nota.matricula_id == matricula_id,
                                        Avaliacao.tipo == TipoAvaliacao.RECUPERACAO,
                                    ),
                                ),
                            )
                            recovery_list = list(recovery_result.scalars().all())
                            if not recovery_list:
                                filho.situacao = SituacaoAluno.RECUPERACAO
                            else:
                                recovery_valor = max(float(n.valor) for n in recovery_list)
                                if media is not None and media >= float(config.media_aprovacao):
                                    filho.situacao = SituacaoAluno.APROVADO_POS_RECUPERACAO
                                else:
                                    filho.situacao = SituacaoAluno.REPROVADO_POS_RECUPERACAO
                    else:
                        filho.situacao = SituacaoAluno.REPROVADO
                except Exception:
                    filho.situacao = SituacaoAluno.REPROVADO
            else:
                filho.situacao = SituacaoAluno.REPROVADO

            filhos.append(filho)

        media_geral = round(sum(medias) / len(medias), 2) if medias else None
        frequencia_media = round(sum(frequencias) / len(frequencias), 2) if frequencias else None

        cards = ResponsavelCards(
            quantidade_filhos=quantidade_filhos,
            matriculas_ativas=matriculas_ativas_count,
            media_geral=media_geral,
            frequencia_media=frequencia_media,
        )

        return ResponsavelDashboardResponse(cards=cards, filhos=filhos)
