"""Context builders do PROFESSOR.

Escopo: `Alocacao.professor_id = <usuario logado>` → turmas → matrículas ativas
dessas turmas → alunos. Todas as consultas usam essa cadeia como filtro no
WHERE. O professor não vê turmas em que não leciona, nem notas de outras
disciplinas, nem dados administrativos.

Bug pré-existente EVITADO de propósito: `GET /professor/turmas/{id}/alunos` e os
endpoints de `assessment`/`attendance` não validam `alocacao.professor_id`
(achado na análise de arquitetura). Aqui a validação é feita na raiz do escopo,
então a IA não herda o problema. Ver relatório, item "Problemas encontrados".
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.ai.context.base import (
    ResultadoContexto,
    formatar_data,
    formatar_decimal,
    formatar_enum,
)
from app.modules.ai.context.comum import (
    MAX_LINHAS,
    alunos_da_turma,
    resumo_frequencia,
)
from app.modules.allocations.models import Alocacao
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.boletim.models import LiberacaoBoletim, PrazoLiberacao
from app.modules.classes.models import Turma
from app.modules.communication.models import Aviso, Ocorrencia
from app.modules.enrollments.models import Matricula
from app.modules.series.models import Serie
from app.modules.students.models import Aluno
from app.modules.subjects.models import Disciplina
from app.shared.enums import StatusAviso, StatusMatricula, StatusOcorrencia


async def turmas_do_professor(
    session: AsyncSession,
    professor_id: uuid.UUID,
) -> list[tuple[Alocacao, Turma, Serie | None, Disciplina]]:
    """Alocações ATIVAS do professor, com a turma e disciplina de cada uma.

    É a raiz do escopo: nenhuma consulta é feita sem passar por aqui.
    """
    alocacoes, _ = await AlocacaoRepository(session).search(
        professor_id=professor_id,
        only_active=True,
        size=200,
    )
    if not alocacoes:
        return []

    turmas = {
        t.id: t
        for t in (
            await session.execute(
                select(Turma).where(Turma.id.in_({a.turma_id for a in alocacoes}))
            )
        ).scalars().all()
    }
    series = {
        s.id: s
        for s in (
            await session.execute(
                select(Serie).where(Serie.id.in_({t.serie_id for t in turmas.values()}))
            )
        ).scalars().all()
    }
    disciplinas = {
        d.id: d
        for d in (
            await session.execute(
                select(Disciplina).where(
                    Disciplina.id.in_({a.disciplina_id for a in alocacoes}),
                )
            )
        ).scalars().all()
    }

    escopo = []
    for alocacao in alocacoes:
        turma = turmas.get(alocacao.turma_id)
        disciplina = disciplinas.get(alocacao.disciplina_id)
        if turma is not None and disciplina is not None:
            escopo.append((alocacao, turma, series.get(turma.serie_id), disciplina))
    return escopo


def _rotulo_turma(turma: Turma, serie: Serie | None) -> str:
    return f"{turma.nome or turma.codigo}{f' ({serie.nome})' if serie else ''}"


async def _media_de_corte(session: AsyncSession, ano_letivo_id: uuid.UUID) -> float:
    """Média de corte da configuração acadêmica (fonte da verdade).

    O LLM nunca calcula média: o cálculo é feito aqui/SQL.
    """
    config = (
        await session.execute(
            select(ConfiguracaoAcademica).where(
                ConfiguracaoAcademica.ano_letivo_id == ano_letivo_id,
            )
        )
    ).scalar_one_or_none()
    return float(config.media_aprovacao) if config else 7.0


# ---------------------------------------------------------------------------
# 5) alunos_abaixo_media
# ---------------------------------------------------------------------------
async def alunos_abaixo_media(
    session: AsyncSession,
    professor_id: uuid.UUID,
) -> ResultadoContexto:
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="alunos_abaixo_media",
        fontes=["notas", "avaliacoes", "alocacoes", "matriculas", "turmas"],
    )

    if not escopo:
        resultado.vazio = True
        resultado.resumo = "Você não possui alocações (turmas) ativas neste ano letivo."
        return resultado

    resultado.adicionar("Turmas sob sua responsabilidade:")
    for _alocacao, turma, serie, disciplina in escopo:
        resultado.adicionar(
            f"- {_rotulo_turma(turma, serie)} — disciplina: {disciplina.nome}",
        )
        resultado.turmas_autorizadas.append(turma.id)

    media_corte = await _media_de_corte(session, escopo[0][1].ano_letivo_id)
    resultado.adicionar(f"Média de corte configurada: {formatar_decimal(media_corte)}")

    total_abaixo = 0
    for alocacao, turma, serie, disciplina in escopo:
        # Uma disciplina por vez: a média nunca mistura disciplinas diferentes.
        linhas = (
            await session.execute(
                select(Aluno.id, Aluno.nome, func.avg(Nota.valor), func.count(Nota.id))
                .select_from(Matricula)
                .join(Nota, Nota.matricula_id == Matricula.id)
                .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
                .join(Aluno, Aluno.id == Matricula.aluno_id)
                .where(
                    Matricula.turma_id == turma.id,
                    Matricula.status == StatusMatricula.ATIVA,
                    Avaliacao.alocacao_id == alocacao.id,
                )
                .group_by(Aluno.id, Aluno.nome)
            )
        ).all()

        abaixo = sorted(
            (
                (aluno_id, nome, float(media))
                for aluno_id, nome, media, _n in linhas
                if media is not None and float(media) < media_corte
            ),
            key=lambda item: item[2],
        )
        if not abaixo:
            continue

        resultado.adicionar(
            f"Alunos abaixo da média em {_rotulo_turma(turma, serie)} ({disciplina.nome}):",
        )
        for aluno_id, nome, media in abaixo[:MAX_LINHAS]:
            resultado.adicionar(f"  {nome}: média {formatar_decimal(media)}")
            resultado.alunos_autorizados.append(aluno_id)
        total_abaixo += len(abaixo)
        if len(abaixo) > MAX_LINHAS:
            resultado.adicionar(
                f"  ... e mais {len(abaixo) - MAX_LINHAS} aluno(s) nesta disciplina.",
            )

    if total_abaixo == 0:
        resultado.vazio = True
        resultado.resumo = (
            "Nenhum aluno das suas turmas está abaixo da média de corte "
            "nas disciplinas sob sua responsabilidade."
        )
        return resultado

    resultado.resumo = (
        f"{total_abaixo} aluno(s) abaixo da média de corte "
        f"({formatar_decimal(media_corte)}) nas suas disciplinas."
    )
    return resultado


# ---------------------------------------------------------------------------
# 6) ocorrencias_pendentes
# ---------------------------------------------------------------------------
async def ocorrencias_pendentes(
    session: AsyncSession,
    professor_id: uuid.UUID,
) -> ResultadoContexto:
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(intencao="ocorrencias_pendentes", fontes=["ocorrencias"])

    if not escopo:
        resultado.vazio = True
        resultado.resumo = "Você não possui alocações (turmas) ativas neste ano letivo."
        return resultado

    turma_ids = [turma.id for _a, turma, _s, _d in escopo]
    rotulos = {turma.id: _rotulo_turma(turma, serie) for _a, turma, serie, _d in escopo}
    resultado.turmas_autorizadas.extend(turma_ids)

    resultado.adicionar("Turmas sob sua responsabilidade:")
    for _a, turma, serie, _d in escopo:
        resultado.adicionar(f"- {_rotulo_turma(turma, serie)}")

    # WHERE ocorrencias.turma_id IN (turmas do professor) AND status não resolvido
    linhas = (
        await session.execute(
            select(Ocorrencia, Aluno)
            .join(Aluno, Aluno.id == Ocorrencia.aluno_id, isouter=True)
            .where(
                Ocorrencia.turma_id.in_(turma_ids),
                Ocorrencia.status.notin_(
                    [StatusOcorrencia.RESOLVIDA, StatusOcorrencia.ARQUIVADA],
                ),
            )
            .order_by(Ocorrencia.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).all()

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Não há ocorrências em aberto nas suas turmas."
        return resultado

    resultado.adicionar(f"Ocorrências em aberto: {len(linhas)}")
    for ocorrencia, aluno in linhas:
        nome_aluno = aluno.nome if aluno is not None else "(ocorrência de turma)"
        resultado.adicionar(
            f"- {nome_aluno} | {ocorrencia.titulo} "
            f"[{formatar_enum(ocorrencia.status)}, "
            f"{formatar_enum(ocorrencia.severidade)}, "
            f"{rotulos.get(ocorrencia.turma_id, '-')}, "
            f"{formatar_data(ocorrencia.created_at)}]",
        )

    resultado.resumo = f"Você tem {len(linhas)} ocorrência(s) em aberto nas suas turmas."
    return resultado


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------


def _escopo_resumido(resultado: ResultadoContexto, escopo) -> None:
    """Lista as turmas/disciplinas do professor (cabeçalho de contexto)."""
    resultado.adicionar("Turmas sob sua responsabilidade:")
    for _alocacao, turma, serie, disciplina in escopo:
        resultado.adicionar(f"- {_rotulo_turma(turma, serie)} — disciplina: {disciplina.nome}")
        resultado.turmas_autorizadas.append(turma.id)


def _sem_escopo(resultado: ResultadoContexto, intencao: str) -> ResultadoContexto:
    """Recusa padronizada para professor sem alocação."""
    resultado.intencao = intencao
    resultado.vazio = True
    resultado.resumo = "Você não possui alocações (turmas) ativas neste ano letivo."
    return resultado


async def _turmas_citadas(
    escopo, nome_turma: str | None, mensagem: str
) -> list:
    """Filtra o escopo do professor pelas turmas citadas na pergunta.

    Filtra SEMPRE dentro do escopo (`escopo` já vem das alocações ativas do
    professor). Pedir uma turma que ele não leciona simplesmente não casa —
    e como o filtro acontece antes de qualquer consulta, não existe caminho
    para alcançar alunos de outra turma.
    """
    if not nome_turma:
        return list(escopo)

    alvo = nome_turma.lower()
    citadas = [
        item for item in escopo
        if alvo in (item[1].nome or "").lower() or alvo in (item[1].codigo or "").lower()
    ]
    if citadas:
        return citadas

    # Segundo passo: casa pelo nome citado solto na mensagem.
    candidatos = [
        item for item in escopo
        if any(
            p in mensagem.lower()
            for p in (
                (item[1].nome or "").lower().split(),
                (item[1].codigo or "").lower().split(),
            )
            if len(p) >= 3
        )
    ]
    return candidatos if candidatos else []


# ---------------------------------------------------------------------------
# minhas_turmas
# ---------------------------------------------------------------------------
async def minhas_turmas(session: AsyncSession, professor_id: uuid.UUID) -> ResultadoContexto:
    """Turmas, séries e disciplinas sob responsabilidade."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="minhas_turmas", fontes=["alocacoes", "turmas", "series", "disciplinas"],
    )

    if not escopo:
        return _sem_escopo(resultado, "minhas_turmas")

    turmas_unicas: dict[uuid.UUID, tuple[Turma, Serie | None, list[str]]] = {}
    for _alocacao, turma, serie, disciplina in escopo:
        entrada = turmas_unicas.setdefault(turma.id, (turma, serie, []))
        entrada[2].append(disciplina.nome)
        resultado.turmas_autorizadas.append(turma.id)

    resultado.adicionar(
        f"Total de turmas: {len(turmas_unicas)} | "
        f"Total de alocações (turma+disciplina): {len(escopo)}"
    )
    resultado.adicionar("Detalhamento:")
    for _turma_id, (turma, serie, disciplinas) in turmas_unicas.items():
        resultado.adicionar(
            f"- {_rotulo_turma(turma, serie)} | turno: {formatar_enum(turma.turno)} "
            f"| disciplinas: {', '.join(sorted(disciplinas))}"
        )

    resultado.resumo = (
        f"Você leciona em {len(turmas_unicas)} turma(s), em {len(escopo)} "
        f"combinações de turma e disciplina."
    )
    return resultado


# ---------------------------------------------------------------------------
# lista_alunos_turma
# ---------------------------------------------------------------------------
async def lista_alunos_turma(
    session: AsyncSession,
    professor_id: uuid.UUID,
    nome_turma: str | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Alunos matriculados nas turmas do professor."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="lista_alunos_turma", fontes=["matriculas", "alunos", "turmas"],
    )

    if not escopo:
        return _sem_escopo(resultado, "lista_alunos_turma")

    citadas = await _turmas_citadas(escopo, nome_turma, mensagem)
    if not citadas:
        resultado.vazio = True
        resultado.resumo = "Não encontrei essa turma entre as suas alocações ativas."
        return resultado

    total = 0
    for _alocacao, turma, serie, _disciplina in citadas:
        resultado.turmas_autorizadas.append(turma.id)
        # WHERE matriculas.turma_id = <turma já autorizada>
        alunos = (
            await session.execute(
                select(Aluno.id, Aluno.nome)
                .select_from(Matricula)
                .join(Aluno, Aluno.id == Matricula.aluno_id)
                .where(
                    Matricula.turma_id == turma.id,
                    Matricula.status == StatusMatricula.ATIVA,
                )
                .order_by(Aluno.nome)
            )
        ).all()

        total += len(alunos)
        resultado.adicionar(
            f"{_rotulo_turma(turma, serie)} — {len(alunos)} aluno(s) matriculado(s)"
        )
        for aluno_id, nome in alunos[:MAX_LINHAS]:
            resultado.adicionar(f"  - {nome}")
            resultado.alunos_autorizados.append(aluno_id)
        if len(alunos) > MAX_LINHAS:
            resultado.adicionar(
                f"  ... e mais {len(alunos) - MAX_LINHAS} aluno(s) nesta turma."
            )

    if total == 0:
        resultado.vazio = True
        resultado.resumo = "Não há alunos matriculados nas turmas indicadas."
        return resultado

    resultado.adicionar(f"Total de alunos matriculados: {total}")
    resultado.resumo = (
        f"Há {total} aluno(s) matriculado(s) nas suas turmas indicadas."
    )
    return resultado


# ---------------------------------------------------------------------------
# avaliacoes_sem_notas
# ---------------------------------------------------------------------------
async def avaliacoes_sem_notas(
    session: AsyncSession,
    professor_id: uuid.UUID,
    nome_turma: str | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Avaliações criadas pelo professor que ainda têm alunos sem nota.

    "Sem nota" é literalmente isso: existe matrícula ativa na turma e não existe
    linha em `notas` para a avaliação. Avaliações sem NENHUM aluno matriculado
    também entram, porque nesse caso o problema é a avaliação, não a turma.
    """
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="avaliacoes_sem_notas", fontes=["avaliacoes", "notas", "matriculas"],
    )

    if not escopo:
        return _sem_escopo(resultado, "avaliacoes_sem_notas")

    citadas = await _turmas_citadas(escopo, nome_turma, mensagem)
    if not citadas:
        resultado.vazio = True
        resultado.resumo = "Não encontrei essa turma entre as suas alocações ativas."
        return resultado

    alocacoes_ids = [alocacao.id for alocacao, _t, _s, _d in citadas]
    resultado.turmas_autorizadas.extend(t.id for _a, t, _s, _d in citadas)

    # WHERE avaliacoes.alocacao_id IN (alocações do professor já filtradas).
    # Só colunas escalares: selecionar a entidade `Avaliacao` junto com um
    # agregado exigiria listar todas as colunas dela no GROUP BY, e o
    # PostgreSQL rejeita a query.
    avaliacoes = (
        await session.execute(
            select(
                Avaliacao.id, Avaliacao.titulo, Avaliacao.tipo,
                Avaliacao.bimestre, Avaliacao.data_aplicacao,
                Avaliacao.alocacao_id, Alocacao.turma_id,
            )
            .join(Alocacao, Alocacao.id == Avaliacao.alocacao_id)
            .where(Avaliacao.alocacao_id.in_(alocacoes_ids))
            .order_by(Avaliacao.data_aplicacao.desc())
            .limit(MAX_LINHAS * 2)
        )
    ).all()

    if not avaliacoes:
        resultado.vazio = True
        resultado.resumo = "Você ainda não criou avaliações nas suas turmas."
        return resultado

    linhas: list[str] = []
    total_pendentes = 0
    for (
        _id, titulo, tipo, bimestre, data_aplicacao, _alocacao_id, turma_id,
    ) in avaliacoes:
        # Quantos alunos têm matrícula ativa na turma desta avaliação.
        total_alunos = (
            await session.execute(
                select(func.count(Matricula.id)).where(
                    Matricula.turma_id == turma_id,
                    Matricula.status == StatusMatricula.ATIVA,
                )
            )
        ).scalar_one()
        # Quantos já têm nota lançada NESTA avaliação.
        lancadas = (
            await session.execute(
                select(func.count(Nota.id)).where(Nota.avaliacao_id == _id)
            )
        ).scalar_one()

        pendentes = max(int(total_alunos) - int(lancadas), 0)
        if pendentes > 0:
            total_pendentes += pendentes
            linhas.append(
                f"- {titulo} ({formatar_enum(tipo)}, "
                f"{bimestre}º bimestre, {formatar_data(data_aplicacao)}): "
                f"{pendentes} de {total_alunos} aluno(s) sem nota"
            )

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Todas as suas avaliações têm notas lançadas."
        return resultado

    resultado.adicionar(f"Avaliações com notas pendentes: {len(linhas)}")
    resultado.adicionar(f"Total de notas faltantes: {total_pendentes}")
    resultado.fatos.extend(linhas[:MAX_LINHAS])
    if len(linhas) > MAX_LINHAS:
        resultado.adicionar(f"... e mais {len(linhas) - MAX_LINHAS} avaliação(ões).")

    resultado.resumo = (
        f"Você tem {len(linhas)} avaliação(ões) com notas pendentes, "
        f"totalizando {total_pendentes} nota(s) a lançar."
    )
    return resultado


# ---------------------------------------------------------------------------
# media_disciplina_turma
# ---------------------------------------------------------------------------
async def media_disciplina_turma(
    session: AsyncSession,
    professor_id: uuid.UUID,
    nome_turma: str | None = None,
    mensagem: str = "",
    *,
    bimestre: int | None = None,
) -> ResultadoContexto:
    """Média por aluno em cada disciplina do professor."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="media_disciplina_turma",
        fontes=["notas", "avaliacoes", "alocacoes", "matriculas"],
    )

    if not escopo:
        return _sem_escopo(resultado, "media_disciplina_turma")

    citadas = await _turmas_citadas(escopo, nome_turma, mensagem)
    if not citadas:
        resultado.vazio = True
        resultado.resumo = "Não encontrei essa turma entre as suas alocações ativas."
        return resultado

    escopo_txt = f"no {bimestre}º bimestre" if bimestre else "no ano letivo"
    total_turmas = 0
    for alocacao, turma, serie, disciplina in citadas:
        resultado.turmas_autorizadas.append(turma.id)

        filtros = [
            Matricula.turma_id == turma.id,
            Matricula.status == StatusMatricula.ATIVA,
            Avaliacao.alocacao_id == alocacao.id,
        ]
        if bimestre is not None:
            filtros.append(Avaliacao.bimestre == bimestre)

        # WHERE ... AND avaliacoes.alocacao_id = <alocação do professor>
        linhas = (
            await session.execute(
                select(Aluno.id, Aluno.nome, func.avg(Nota.valor), func.count(Nota.id))
                .select_from(Matricula)
                .join(Nota, Nota.matricula_id == Matricula.id)
                .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
                .join(Aluno, Aluno.id == Matricula.aluno_id)
                .where(*filtros)
                .group_by(Aluno.id, Aluno.nome)
                .order_by(func.avg(Nota.valor))
            )
        ).all()

        if not linhas:
            continue

        total_turmas += 1
        resultado.adicionar(
            f"{_rotulo_turma(turma, serie)} — {disciplina.nome} ({escopo_txt}): "
            f"{len(linhas)} aluno(s) com notas"
        )
        for aluno_id, nome, media, quantidade in linhas[:MAX_LINHAS]:
            resultado.adicionar(
                f"  {nome}: média {formatar_decimal(float(media))} "
                f"({quantidade} nota(s))"
            )
            resultado.alunos_autorizados.append(aluno_id)
        if len(linhas) > MAX_LINHAS:
            resultado.adicionar(
                f"  ... e mais {len(linhas) - MAX_LINHAS} aluno(s)."
            )

    if total_turmas == 0:
        resultado.vazio = True
        resultado.resumo = (
            "Não há notas lançadas nas suas disciplinas"
            + (f" no {bimestre}º bimestre" if bimestre else " neste ano letivo")
            + "."
        )
        return resultado

    resultado.resumo = (
        f"Foram calculadas as médias de {total_turmas} turma(s) nas suas disciplinas."
    )
    return resultado


# ---------------------------------------------------------------------------
# frequencia_turma
# ---------------------------------------------------------------------------
async def frequencia_turma(
    session: AsyncSession,
    professor_id: uuid.UUID,
    nome_turma: str | None = None,
    mensagem: str = "",
    *,
    bimestre: int | None = None,
) -> ResultadoContexto:
    """Frequência dos alunos das turmas do professor."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="frequencia_turma", fontes=["frequencias", "chamadas", "alocacoes"],
    )

    if not escopo:
        return _sem_escopo(resultado, "frequencia_turma")

    citadas = await _turmas_citadas(escopo, nome_turma, mensagem)
    if not citadas:
        resultado.vazio = True
        resultado.resumo = "Não encontrei essa turma entre as suas alocações ativas."
        return resultado

    turmas_ids = [t.id for _a, t, _s, _d in citadas]
    resultado.turmas_autorizadas.extend(turmas_ids)

    media_aprovacao, minimo = await _media_de_corte(
        session, citadas[0][1].ano_letivo_id,
    )
    resultado.adicionar(f"Frequência mínima exigida: {formatar_decimal(minimo)}%")

    total_registros_geral = 0
    turmas_com_dados = 0

    for _alocacao, turma, serie, _disciplina in citadas:
        for aluno, matricula in await alunos_da_turma(session, turma.id):
            resumo = await resumo_frequencia(
                session, matricula, bimestre=bimestre,
            )
            if resumo is None:
                continue
            total_registros_geral += resumo.total_registros
            turmas_com_dados += 1
            sinal = "abaixo do mínimo" if resumo.abaixo_do_minimo else "ok"
            resultado.adicionar(
                f"- {turma.nome or turma.codigo} | {aluno.nome}: "
                f"{formatar_decimal(resumo.percentual)}% "
                f"(faltas: {resumo.faltas}, justificadas: {resumo.faltas_justificadas}) "
                f"[{sinal}]"
            )
            resultado.alunos_autorizados.append(aluno.id)

    if turmas_com_dados == 0:
        resultado.vazio = True
        resultado.resumo = (
            "Ainda não há registros de chamada nas suas turmas"
            + (f" para o {bimestre}º bimestre" if bimestre else "")
            + "."
        )
        return resultado

    resultado.adicionar(f"Alunos com frequência registrada: {turmas_com_dados}")
    resultado.resumo = (
        f"Há frequência registrada para {turmas_com_dados} aluno(s) nas suas turmas, "
        f"com mínimo de {formatar_decimal(minimo)}%."
    )
    return resultado


# ---------------------------------------------------------------------------
# avisos_turma
# ---------------------------------------------------------------------------
async def avisos_turma(
    session: AsyncSession,
    professor_id: uuid.UUID,
    nome_turma: str | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Avisos publicados para as turmas do professor."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(intencao="avisos_turma", fontes=["avisos"])

    if not escopo:
        return _sem_escopo(resultado, "avisos_turma")

    citadas = await _turmas_citadas(escopo, nome_turma, mensagem)
    if not citadas:
        resultado.vazio = True
        resultado.resumo = "Não encontrei essa turma entre as suas alocações ativas."
        return resultado

    turmas_ids = [t.id for _a, t, _s, _d in citadas]
    resultado.turmas_autorizadas.extend(turmas_ids)

    # WHERE avisos.destinatario_turma_id IN (turmas do professor)
    avisos = (
        await session.execute(
            select(Aviso)
            .where(
                Aviso.status == StatusAviso.PUBLICADO,
                Aviso.destinatario_turma_id.in_(turmas_ids),
            )
            .order_by(Aviso.publicado_em.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    if not avisos:
        resultado.vazio = True
        resultado.resumo = "Não há avisos publicados para as suas turmas."
        return resultado

    resultado.adicionar(f"Avisos encontrados: {len(avisos)}")
    for aviso in avisos:
        rotulo_turma = next(
            (t.nome or t.codigo for _a, t, _s, _d in citadas
             if t.id == aviso.destinatario_turma_id),
            "-",
        )
        resultado.adicionar(
            f"- {aviso.titulo} (turma: {rotulo_turma}, "
            f"{formatar_enum(aviso.prioridade)}, "
            f"{formatar_data(aviso.publicado_em)})"
        )

    resultado.resumo = f"Há {len(avisos)} aviso(s) publicado(s) para as suas turmas."
    return resultado


# ---------------------------------------------------------------------------
# prazos_boletim
# ---------------------------------------------------------------------------
async def prazos_boletim(session: AsyncSession, professor_id: uuid.UUID) -> ResultadoContexto:
    """Prazos de liberação de boletim e o que o professor já liberou."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="prazos_boletim", fontes=["prazos_liberacao", "liberacoes_boletim"],
    )

    if not escopo:
        return _sem_escopo(resultado, "prazos_boletim")

    turmas_ids = [t.id for _a, t, _s, _d in escopo]
    resultado.turmas_autorizadas.extend(turmas_ids)

    # Prazos: WHERE ano_letivo_id IN (anos das turmas do professor)
    anos_ids = {t.ano_letivo_id for _a, t, _s, _d in escopo}
    prazos = (
        await session.execute(
            select(PrazoLiberacao)
            .where(
                PrazoLiberacao.ano_letivo_id.in_(list(anos_ids)),
                PrazoLiberacao.ativo.is_(True),
            )
            .order_by(PrazoLiberacao.bimestre)
        )
    ).scalars().all()

    # Liberações: WHERE professor_id = <token> AND turma_id IN (turmas)
    liberacoes = (
        await session.execute(
            select(LiberacaoBoletim, Disciplina)
            .join(Disciplina, Disciplina.id == LiberacaoBoletim.disciplina_id)
            .where(
                LiberacaoBoletim.professor_id == professor_id,
                LiberacaoBoletim.turma_id.in_(turmas_ids),
                LiberacaoBoletim.ativo.is_(True),
            )
            .order_by(LiberacaoBoletim.bimestre.desc(), LiberacaoBoletim.liberado_em.desc())
        )
    ).all()

    if not prazos and not liberacoes:
        resultado.vazio = True
        resultado.resumo = "Não há prazos nem liberações de boletim configurados."
        return resultado

    if prazos:
        resultado.adicionar("Prazos de liberação:")
        for prazo in prazos:
            resultado.adicionar(
                f"- {prazo.bimestre}º bimestre: até "
                f"{formatar_data(prazo.data_limite)} às {prazo.hora_limite.strftime('%H:%M')}"
            )

    if liberacoes:
        resultado.adicionar(f"Liberações já feitas por você: {len(liberacoes)}")
        for liberacao, disciplina in liberacoes[:MAX_LINHAS]:
            resultado.adicionar(
                f"- {disciplina.nome} | {liberacao.bimestre}º bimestre | "
                f"liberado em {formatar_data(liberacao.liberado_em)}"
            )

    resultado.resumo = (
        f"Há {len(prazos)} prazo(s) de liberação configurado(s) e "
        f"{len(liberacoes)} liberação(ões) feita(s) por você."
    )
    return resultado


# ---------------------------------------------------------------------------
# chamadas_recentes
# ---------------------------------------------------------------------------
async def chamadas_recentes(
    session: AsyncSession,
    professor_id: uuid.UUID,
) -> ResultadoContexto:
    """Chamadas de presença realizadas pelo professor."""
    escopo = await turmas_do_professor(session, professor_id)
    resultado = ResultadoContexto(
        intencao="chamadas_recentes", fontes=["chamadas", "frequencias"],
    )

    if not escopo:
        return _sem_escopo(resultado, "chamadas_recentes")

    alocacoes_ids = [a.id for a, _t, _s, _d in escopo]
    resultado.turmas_autorizadas.extend(t.id for _a, t, _s, _d in escopo)

    # WHERE chamadas.alocacao_id IN (alocações ativas do professor).
    # A contagem de registros vem de um SUBQUERY correlacionado em vez de um
    # `GROUP BY` sobre as entidades: assim só colunas escalares entram no
    # SELECT, que é o que o PostgreSQL exige quando há agregação.
    total_por_chamada = (
        select(func.count(Frequencia.id))
        .where(Frequencia.chamada_id == Chamada.id)
        .correlate(Chamada)
        .scalar_subquery()
    )

    linhas = (
        await session.execute(
            select(
                Chamada.id,
                Chamada.data_hora_aula,
                Disciplina.nome,
                Turma.nome,
                Turma.codigo,
                total_por_chamada.label("total"),
            )
            .join(Alocacao, Alocacao.id == Chamada.alocacao_id)
            .join(Disciplina, Disciplina.id == Alocacao.disciplina_id)
            .join(Turma, Turma.id == Alocacao.turma_id)
            .where(Chamada.alocacao_id.in_(alocacoes_ids))
            .order_by(Chamada.data_hora_aula.desc())
            .limit(MAX_LINHAS)
        )
    ).all()

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Você ainda não realizou nenhuma chamada de presença."
        return resultado

    resultado.adicionar(f"Chamadas encontradas: {len(linhas)}")
    for _chamada_id, quando, disciplina_nome, turma_nome, turma_codigo, total in linhas:
        resultado.adicionar(
            f"- {formatar_data(quando)} "
            f"às {quando.strftime('%H:%M')} | "
            f"{turma_nome or turma_codigo} | {disciplina_nome} | "
            f"{total} registro(s) de presença"
        )

    resultado.resumo = f"Você realizou {len(linhas)} chamada(s) recente(s)."
    return resultado
