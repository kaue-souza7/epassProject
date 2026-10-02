"""Context builders da COORDENAÇÃO.

O coordenador é o único perfil do sistema que enxerga a escola INTEIRA com
olho pedagógico. O RBAC (`app/core/permissions.py`) já dá a ele leitura de
aluno, turma, professor, nota, frequência, ocorrência, aviso e financeiro — em
escopo "all". A allowlist de `intent.py` apenas reflete esse papel.

O que a coordenação quer não é o dado bruto: é "onde está o problema". Por isso
os builders deste arquivo são agregações que respondem pergunta de RISCO, não
de consulta: quais turmas estão mal, quais alunos combinam nota baixa com
frequência baixa, o que está aberto.

Limite respeitado: só agregados e nominal próprio. A coordenação tem visão
institucional, mas a mesma régua anti-alucinação numérica vale aqui — e o
princípio de dados mínimos também: contagens e nomes de aluno, nunca CPF,
endereço, telefone ou o conteúdo integral de documentos.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.academic_years.models import AnoLetivo
from app.modules.ai.context.base import (
    ResultadoContexto,
    formatar_decimal,
)
from app.modules.ai.context.comum import MAX_LINHAS, media_geral, resumo_frequencia
from app.modules.allocations.models import Alocacao
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.classes.models import Turma
from app.modules.enrollments.models import Matricula
from app.modules.series.models import Serie
from app.modules.students.models import Aluno
from app.modules.teachers.models import ProfessorProfile
from app.shared.enums import StatusMatricula, TipoAvaliacao


# ---------------------------------------------------------------------------
# panorama_escolar
# ---------------------------------------------------------------------------
async def panorama_escolar(session: AsyncSession) -> ResultadoContexto:
    """Números que abrem a conversa com a coordenação.

    Tudo agregado e com rótulo explícito de onde veio o número, para que o modelo
    não some nem deduplique: "alunos matriculados" e "cadastros ativos" são
    coisas diferentes, e misturá-las produziria um número que não existe.
    """
    total_alunos = (
        await session.execute(
            select(func.count()).select_from(Aluno).where(Aluno.ativo.is_(True))
        )
    ).scalar_one()

    alunos_matriculados = (
        await session.execute(
            select(func.count(func.distinct(Matricula.aluno_id))).where(
                Matricula.status == StatusMatricula.ATIVA,
            )
        )
    ).scalar_one()

    total_turmas = (
        await session.execute(
            select(func.count()).select_from(Turma).where(Turma.ativo.is_(True))
        )
    ).scalar_one()

    total_series = (
        await session.execute(
            select(func.count()).select_from(Serie).where(Serie.ativo.is_(True))
        )
    ).scalar_one()

    total_professores = (
        await session.execute(
            select(func.count()).select_from(ProfessorProfile).where(
                ProfessorProfile.ativo.is_(True),
            )
        )
    ).scalar_one()

    total_alocacoes = (
        await session.execute(
            select(func.count()).select_from(Alocacao).where(
                Alocacao.data_fim.is_(None),
            )
        )
    ).scalar_one()

    resultado = ResultadoContexto(
        intencao="panorama_escolar",
        fontes=[
            "alunos", "matriculas", "turmas", "series",
            "professor_profiles", "alocacoes",
        ],
    )

    if total_alunos == 0 and total_turmas == 0:
        resultado.vazio = True
        resultado.resumo = "Não há alunos nem turmas cadastrados."
        return resultado

    resultado.adicionar(
        f"Alunos cadastrados e ativos: {total_alunos}\n"
        f"Alunos com matrícula ativa: {alunos_matriculados}\n"
        f"Turmas ativas: {total_turmas}\n"
        f"Séries ativas: {total_series}\n"
        f"Professores ativos: {total_professores}\n"
        f"Alocações de disciplina ativas: {total_alocacoes}"
    )

    resultado.resumo = (
        f"A escola tem {alunos_matriculados} aluno(s) matriculados em "
        f"{total_turmas} turma(s) ativas, com {total_professores} professor(es) ativo(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# Regras acadêmicas do ano ativo
# ---------------------------------------------------------------------------
async def _config_do_ano_ativo(session: AsyncSession) -> ConfiguracaoAcademica | None:
    """Configuração acadêmica do ano letivo ativo — a fonte das regras.

    Ordena pelo ano mais RECENTE de propósito. O banco pode ter mais de um ano
    letivo marcado como ativo (transição de calendário, carga de dado antigo),
    e sem `ORDER BY` o PostgreSQL devolve uma linha qualquer: a mesma pergunta
    passaria a dar respostas diferentes em dias diferentes, e a régua de
    reprovação mudaria sem que nada tivesse mudado no ePass.

    Escolher o ano mais recente é a mesma regra do resto do sistema para "ano
    letivo corrente".
    """
    return (
        await session.execute(
            select(ConfiguracaoAcademica)
            .join(AnoLetivo, AnoLetivo.id == ConfiguracaoAcademica.ano_letivo_id)
            .where(AnoLetivo.ativo.is_(True))
            .order_by(AnoLetivo.ano.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# turmas_criticas
# ---------------------------------------------------------------------------
async def turmas_criticas(session: AsyncSession) -> ResultadoContexto:
    """Turmas com mais alunos abaixo da média de corte.

    O cálculo é o mesmo do `relatorio`/`dashboard`: média ponderada por
    avaliação, excluindo recuperação, comparada com `media_aprovacao` da
    configuração do ano. O que muda aqui é o AGREGADO — a coordenação precisa
    saber onde concentra o problema, não a lista dos alunos de uma turma.
    """
    config = await _config_do_ano_ativo(session)
    media_corte = float(config.media_aprovacao) if config else 7.0

    resultado = ResultadoContexto(
        intencao="turmas_criticas",
        fontes=["notas", "avaliacoes", "alocacoes", "matriculas", "turmas", "series"],
    )
    resultado.adicionar(f"Média de corte configurada: {formatar_decimal(media_corte)}")

    # Média por (turma, aluno) — uma disciplina por vez, nunca misturadas.
    linhas = (
        await session.execute(
            select(
                Turma.id, Turma.codigo, Turma.nome, Serie.nome,
                Aluno.id, Aluno.nome,
                func.sum(Nota.valor * Avaliacao.peso) / func.nullif(
                    func.sum(Avaliacao.peso), 0,
                ),
            )
            .select_from(Nota)
            .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
            .join(Alocacao, Alocacao.id == Avaliacao.alocacao_id)
            .join(Turma, Turma.id == Alocacao.turma_id)
            .join(Serie, Serie.id == Turma.serie_id)
            .join(Matricula, Matricula.id == Nota.matricula_id)
            .join(Aluno, Aluno.id == Matricula.aluno_id)
            .where(
                Matricula.status == StatusMatricula.ATIVA,
                Avaliacao.tipo != TipoAvaliacao.RECUPERACAO,
            )
            .group_by(Turma.id, Turma.codigo, Turma.nome, Serie.nome, Aluno.id, Aluno.nome)
        )
    ).all()

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Ainda não há notas lançadas para calcular o risco das turmas."
        return resultado

    # Acumula por turma: total de alunos com média e quantos estão abaixo.
    por_turma: dict[tuple, dict] = {}
    for turma_id, codigo, nome, serie_nome, aluno_id, aluno_nome, media in linhas:
        chave = (turma_id, codigo, nome, serie_nome)
        entrada = por_turma.setdefault(
            chave, {"abaixo": 0, "total": 0, "alunos": []},
        )
        entrada["total"] += 1
        if media is not None and float(media) < media_corte:
            entrada["abaixo"] += 1
            entrada["alunos"].append((aluno_id, aluno_nome, float(media)))

    resultado.adicionar(f"Turmas com notas lançadas: {len(por_turma)}")

    # Ordena pelo percentage: a primeira linha é onde está o problema maior.
    ranking = sorted(
        por_turma.items(),
        key=lambda item: (item[1]["abaixo"] / item[1]["total"]),
        reverse=True,
    )

    total_com_abaixo = 0
    for (turma_id, codigo, nome, serie_nome), entrada in ranking:
        if entrada["abaixo"] == 0:
            continue
        total_com_abaixo += entrada["abaixo"]
        resultado.turmas_autorizadas.append(turma_id)
        resultado.adicionar(
            f"- {nome or codigo} ({serie_nome}): {entrada['abaixo']} de "
            f"{entrada['total']} aluno(s) abaixo da média de corte"
        )
        for aluno_id, aluno_nome, media in sorted(
            entrada["alunos"], key=lambda item: item[2],
        )[:5]:
            resultado.adicionar(
                f"    {aluno_nome}: média {formatar_decimal(media)}"
            )
            resultado.alunos_autorizados.append(aluno_id)
        if len(entrada["alunos"]) > 5:
            resultado.adicionar(
                f"    ... e mais {len(entrada['alunos']) - 5} aluno(s) abaixo da média."
            )

    if total_com_abaixo == 0:
        resultado.vazio = True
        resultado.resumo = (
            "Nenhum aluno está abaixo da média de corte nas turmas avaliadas."
        )
        return resultado

    resultado.resumo = (
        f"Há {total_com_abaixo} aluno(s) abaixo da média de corte "
        f"({formatar_decimal(media_corte)}) distribuídos em "
        f"{sum(1 for v in por_turma.values() if v['abaixo'] > 0)} turma(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# alunos_atencao_coordenacao
# ---------------------------------------------------------------------------
async def alunos_atencao_coordenacao(session: AsyncSession) -> ResultadoContexto:
    """Alunos que combinam nota baixa E frequência baixa.

    A interseção é o que dá valor a este relatório: um aluno com nota baixa e
    frequência boa é um caso dedidático; um aluno com nota alta e frequência
    baixa é um caso de adaptação. Os dois juntos são o que a coordenação
    normalmente quer saber — e é exatamente o recorte que nenhum outro builder
    entrega.
    """
    config = await _config_do_ano_ativo(session)
    media_corte = float(config.media_aprovacao) if config else 7.0
    frequencia_minima = float(config.frequencia_minima) if config else 75.0

    resultado = ResultadoContexto(
        intencao="alunos_atencao_coordenacao",
        fontes=[
            "notas", "avaliacoes", "alocacoes", "matriculas",
            "turmas", "frequencias", "configuracoes_academicas",
        ],
    )
    resultado.adicionar(
        f"Critérios: média abaixo de {formatar_decimal(media_corte)} "
        f"e frequência abaixo de {formatar_decimal(frequencia_minima)}%"
    )

    # Percorre as matrículas ativas: cada uma pertence a uma turma, e média e
    # frequência saem sempre daquela matrícula — nunca do aluno agregado.
    alunos_ativos = (
        await session.execute(
            select(Matricula).where(Matricula.status == StatusMatricula.ATIVA)
        )
    ).scalars().all()

    if not alunos_ativos:
        resultado.vazio = True
        resultado.resumo = "Não há matrículas ativas para avaliar."
        return resultado

    em_risco: list[str] = []
    avaliados = 0
    for matricula in alunos_ativos:
        media = await media_geral(session, matricula.id)
        frequencia = await resumo_frequencia(session, matricula)
        if media is None or frequencia is None:
            continue

        avaliados += 1
        if media >= media_corte or frequencia.percentual >= frequencia_minima:
            continue

        em_risco.append(
            f"- {matricula.aluno.nome} | turma: {matricula.turma.nome or matricula.turma.codigo} "
            f"| média {formatar_decimal(media)} | "
            f"frequência {formatar_decimal(frequencia.percentual)}% "
            f"({frequencia.faltas} falta(s))"
        )
        resultado.alunos_autorizados.append(matricula.aluno_id)
        resultado.turmas_autorizadas.append(matricula.turma_id)

    resultado.adicionar(f"Alunos avaliados: {avaliados}")

    if not em_risco:
        resultado.vazio = True
        resultado.resumo = (
            "Nenhum aluno reúne média e frequência abaixo do mínimo ao mesmo tempo."
        )
        return resultado

    resultado.adicionar(f"Alunos que combinam nota e frequência baixas: {len(em_risco)}")
    resultado.fatos.extend(em_risco[:MAX_LINHAS])
    if len(em_risco) > MAX_LINHAS:
        resultado.adicionar(f"... e mais {len(em_risco) - MAX_LINHAS} aluno(s).")

    resultado.resumo = (
        f"Há {len(em_risco)} aluno(s) com média e frequência abaixo do mínimo "
        f"ao mesmo tempo."
    )
    return resultado
