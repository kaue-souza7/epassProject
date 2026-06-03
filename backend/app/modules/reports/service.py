from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound
from app.modules.academic_config.service import ConfiguracaoAcademicaService
from app.modules.reports.schemas import (
    BoletimAnual,
    BoletimBimestral,
    DisciplinaBoletim,
)
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.assessment.repository import AvaliacaoRepository, NotaRepository
from app.modules.attendance.repository import ChamadaRepository, FrequenciaRepository
from app.shared.enums import StatusFrequencia, SituacaoAluno, TipoAvaliacao


class BoletimService:
    def __init__(self, session: AsyncSession) -> None:
        self._matricula_repo = MatriculaRepository(session)
        self._alocacao_repo = AlocacaoRepository(session)
        self._avaliacao_repo = AvaliacaoRepository(session)
        self._nota_repo = NotaRepository(session)
        self._chamada_repo = ChamadaRepository(session)
        self._freq_repo = FrequenciaRepository(session)

        self._config_service = ConfiguracaoAcademicaService(session)

        self._matricula_cache: dict[str, object | None] = {}
        self._alocacoes_cache: dict[str, list[object]] = {}
        self._media_cache: dict[tuple[str, str, int], float] = {}
        self._freq_cache: dict[tuple[str, str, int], float | None] = {}
        self._config_cache: dict[str, object | None] = {}

    async def _get_matricula(self, matricula_id):
        key = str(matricula_id)
        if key not in self._matricula_cache:
            self._matricula_cache[key] = await self._matricula_repo.get_by_id(matricula_id)
        return self._matricula_cache[key]

    async def _get_alocacoes(self, turma_id):
        key = str(turma_id)
        if key not in self._alocacoes_cache:
            items, _ = await self._alocacao_repo.search(turma_id=turma_id, size=100)
            self._alocacoes_cache[key] = items
        return self._alocacoes_cache[key]

    async def _get_configuracao(self, matricula_id):
        key = str(matricula_id)
        if key not in self._config_cache:
            self._config_cache[key] = await self._config_service.obter_por_matricula(matricula_id)
        return self._config_cache[key]

    async def gerar_boletim_bimestral(
        self, matricula_id, bimestre: int,
    ) -> BoletimBimestral:
        matricula = await self._get_matricula(matricula_id)
        if matricula is None:
            raise NotFound("Matrícula não encontrada")

        turma = matricula.turma
        alocacoes = await self._get_alocacoes(turma.id)

        disciplinas = []
        for aloc in alocacoes:
            media = await self._calcular_media(matricula_id, aloc.id, bimestre)
            frequencia = await self._calcular_frequencia(matricula_id, aloc.id, bimestre, turma.ano_letivo.ano)

            disciplinas.append(DisciplinaBoletim(
                disciplina_id=aloc.disciplina_id,
                disciplina_nome=aloc.disciplina.nome,
                media=media,
                frequencia=frequencia,
            ))

        return BoletimBimestral(
            matricula_id=matricula.id,
            aluno_nome=matricula.aluno.nome,
            turma_codigo=turma.codigo,
            serie_nome=turma.serie.nome,
            ano_letivo=turma.ano_letivo.ano,
            bimestre=bimestre,
            disciplinas=disciplinas,
        )

    async def gerar_boletim_anual(self, matricula_id) -> BoletimAnual:
        matricula = await self._get_matricula(matricula_id)
        if matricula is None:
            raise NotFound("Matrícula não encontrada")

        alocacoes = await self._get_alocacoes(matricula.turma_id)
        recovery_notas = await self._nota_repo.get_recuperacao_by_matricula(matricula_id)
        recovery_map: dict[str, float] = {}
        for n in recovery_notas:
            aloc = n.avaliacao.alocacao
            recovery_map[str(aloc.disciplina_id)] = float(n.valor)

        bimestres = []
        for b in range(1, 5):
            boletim = await self.gerar_boletim_bimestral(matricula_id, b)
            for disc in boletim.disciplinas:
                disc_key = str(disc.disciplina_id)
                if disc_key in recovery_map:
                    disc.nota_recuperacao = recovery_map[disc_key]
                    disc.media_pos_recuperacao = recovery_map[disc_key]
            bimestres.append(boletim)

        situacao, media_pre, media_pos, _ = await self._calcular_situacao_final(matricula_id)

        primeiro = bimestres[0]
        return BoletimAnual(
            matricula_id=primeiro.matricula_id,
            aluno_nome=primeiro.aluno_nome,
            turma_codigo=primeiro.turma_codigo,
            serie_nome=primeiro.serie_nome,
            ano_letivo=primeiro.ano_letivo,
            bimestres=bimestres,
            situacao_final=situacao,
            media_pre_recuperacao=media_pre,
            media_pos_recuperacao=media_pos,
        )

    async def _calcular_media(
        self, matricula_id, alocacao_id, bimestre: int,
    ):
        key = (str(matricula_id), str(alocacao_id), bimestre)
        if key in self._media_cache:
            return self._media_cache[key]

        avaliacoes = await self._avaliacao_repo.get_by_alocacao_bimestre(
            alocacao_id, bimestre,
        )
        avaliacoes = [a for a in avaliacoes if a.tipo != TipoAvaliacao.RECUPERACAO]
        if not avaliacoes:
            self._media_cache[key] = 0
            return 0

        notas = await self._nota_repo.get_by_matricula_bimestre(matricula_id, bimestre)
        notas_map = {n.avaliacao_id: n for n in notas}

        soma_pesos = 0
        soma_notas = 0
        for a in avaliacoes:
            if a.id in notas_map:
                soma_pesos += a.peso
                soma_notas += float(notas_map[a.id].valor) * a.peso

        resultado = round(soma_notas / soma_pesos, 2) if soma_pesos > 0 else 0
        self._media_cache[key] = resultado
        return resultado

    async def _calcular_frequencia(
        self, matricula_id, alocacao_id, bimestre: int, ano: int,
    ):
        key = (str(matricula_id), str(alocacao_id), bimestre)
        if key in self._freq_cache:
            return self._freq_cache[key]

        mes_ini = (bimestre - 1) * 3 + 1
        mes_fim = bimestre * 3
        ultimo_dia = calendar.monthrange(ano, mes_fim)[1]
        data_ini = date(ano, mes_ini, 1)
        data_fim = date(ano, mes_fim, ultimo_dia)

        chamadas = await self._chamada_repo.get_by_alocacao_periodo(
            alocacao_id, data_ini, data_fim,
        )
        if not chamadas:
            self._freq_cache[key] = None
            return None

        chamada_ids = [c.id for c in chamadas]
        frequencias = await self._freq_repo.get_by_matricula_and_chamadas(matricula_id, chamada_ids)

        presentes = sum(
            1 for f in frequencias
            if f.status in (StatusFrequencia.PRESENTE, StatusFrequencia.FALTA_JUSTIFICADA)
        )

        resultado = presentes / len(chamadas) * 100
        self._freq_cache[key] = resultado
        return resultado

    async def _calcular_situacao_final(
        self, matricula_id,
    ) -> tuple[SituacaoAluno, float | None, float | None, float | None]:
        matricula = await self._get_matricula(matricula_id)
        if matricula is None:
            return SituacaoAluno.REPROVADO, None, None, None

        ano = matricula.turma.ano_letivo.ano
        config = await self._get_configuracao(matricula_id)

        medias_anuais = []
        medias_por_alocacao_bimestre: dict[tuple, float] = {}
        alocacoes = await self._get_alocacoes(matricula.turma_id)
        for b in range(1, 5):
            for aloc in alocacoes:
                media = await self._calcular_media(matricula_id, aloc.id, b)
                medias_anuais.append(media)
                medias_por_alocacao_bimestre[(str(aloc.id), b)] = media

        if not medias_anuais:
            return SituacaoAluno.REPROVADO, None, None, None

        media_pre = sum(medias_anuais) / len(medias_anuais)

        total_presencas = 0
        total_aulas = 0
        for b in range(1, 5):
            for aloc in alocacoes:
                freq = await self._calcular_frequencia(matricula_id, aloc.id, b, ano)
                if freq is not None:
                    total_presencas += freq
                    total_aulas += 1

        frequencia_final = total_presencas / total_aulas if total_aulas > 0 else 0

        freq_val = round(frequencia_final, 2) if frequencia_final is not None else None

        if media_pre >= float(config.media_aprovacao) and frequencia_final >= float(config.frequencia_minima):
            return SituacaoAluno.APROVADO, None, None, freq_val
        elif frequencia_final < float(config.frequencia_minima):
            return SituacaoAluno.REPROVADO, None, None, freq_val
        elif not config.possui_recuperacao:
            return SituacaoAluno.REPROVADO, None, None, freq_val
        elif config.media_minima_recuperacao is not None and media_pre < float(config.media_minima_recuperacao):
            return SituacaoAluno.REPROVADO, None, None, freq_val

        recovery_notas = await self._nota_repo.get_recuperacao_by_matricula(matricula_id)
        if not recovery_notas:
            return SituacaoAluno.RECUPERACAO, None, None, freq_val

        recovery_map: dict[str, float] = {}
        for n in recovery_notas:
            aval = n.avaliacao
            recovery_map[str(aval.alocacao_id)] = float(n.valor)

        medias_pos_list = []
        for (aloc_key, b), pre_media in medias_por_alocacao_bimestre.items():
            if aloc_key in recovery_map:
                medias_pos_list.append(recovery_map[aloc_key])
            else:
                medias_pos_list.append(pre_media)

        media_pos = sum(medias_pos_list) / len(medias_pos_list) if medias_pos_list else 0

        if media_pos >= float(config.media_aprovacao):
            return SituacaoAluno.APROVADO_POS_RECUPERACAO, media_pre, media_pos, freq_val
        else:
            return SituacaoAluno.REPROVADO_POS_RECUPERACAO, media_pre, media_pos, freq_val
