"""Consultas de domínio compartilhadas pelos context builders.

POR QUE ESTE MÓDULO EXISTE
---------------------------
A cobertura da Atena é "responder qualquer pergunta sobre o ePass", e isso
significa que as MESMAS contas aparecem em várias intenções: a média do aluno
aparece para o responsável ("como está meu filho?"), para o professor ("como
está o João na minha disciplina?") e para a coordenação ("quais turmas estão
críticas?").

Se cada builder reescrevesse a média ponderada, teríamos três lugares com três
versões do mesmo cálculo — e o dia em que uma delas divergir, a IA passaria a
dar nota diferente da que o boletim mostra. Aqui o cálculo existe UMA vez e
todos consomem o mesmo resultado.

REGRA
----
Estes helpers NÃO autorizam nada: eles recebem identificadores que o builder
já resolveu dentro do escopo e apenas calculam. A autorização é responsabilidade
do builder chamador (é ele que monta o `WHERE` com o escopo do usuário).

Os cálculos espelham a fonte de verdade do sistema (`reports/service.py` e
`dashboard/repository.py`) de propósito. Se um dia a regra mudar lá, muda aqui
também — a IA não pode discordar do boletim.
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.academic_years.models import AnoLetivo
from app.modules.allocations.models import Alocacao
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.classes.models import Turma
from app.modules.enrollments.models import Matricula
from app.modules.students.models import Aluno
from app.modules.subjects.models import Disciplina
from app.shared.enums import (
    SituacaoAluno,
    StatusFrequencia,
    StatusMatricula,
    TipoAvaliacao,
)

# Teto padrão de linhas listadas por contexto. A janela de 4k do modelo é o
# limite real; 15 linhas é o ponto em que a lista ainda cabe com o cabeçalho,
# o resumo e as instruções.
MAX_LINHAS = 15

# Meses do bimestre. Mesma regra do `reports/service.py`: 1o bimestre = meses
# 1 a 3, e assim por diante.
_MESES_POR_BIMESTRE = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}

# Avaliações de recuperação não entram na média: elas corrigem, não compõem.
_TIPOS_EXCLUIDOS_DA_MEDIA = (TipoAvaliacao.RECUPERACAO,)


@dataclass
class MediaDisciplina:
    """Média de UMA disciplina — nunca mistura disciplinas diferentes."""

    disciplina: str
    alocacao_id: uuid.UUID
    media: float
    quantidade_notas: int
    bimestres: list[int]


@dataclass
class ResumoFrequencia:
    """Frequência de um aluno. `faltas_justificadas` conta como presença."""

    percentual: float
    presencas: int
    faltas: int
    faltas_justificadas: int
    total_registros: int
    minimo: float | None = None

    @property
    def abaixo_do_minimo(self) -> bool:
        """Abaixo do mínimo configurado. Sem mínimo configurado, nunca."""
        return self.minimo is not None and self.percentual < self.minimo


@dataclass
class ResumoAluno:
    """Retrato consolidado de um aluno — usado por várias intenções."""

    aluno_id: uuid.UUID
    nome: str
    matricula_id: uuid.UUID
    turma_nome: str
    serie_nome: str
    turno: str
    media_geral: float | None
    media_aprovacao: float
    frequencia: ResumoFrequencia | None
    frequencia_minima: float
    situacao_estimada: str


# ---------------------------------------------------------------------------
# Regras acadêmicas
# ---------------------------------------------------------------------------


async def regras_academicas(
    session: AsyncSession,
    ano_letivo_id: uuid.UUID,
) -> tuple[float, float]:
    """`(media_aprovacao, frequencia_minima)` do ano letivo.

    O fallback (7,0 / 75,0) é o mesmo adotado pelo resto do sistema quando a
    configuração ainda não existe: a IA nunca inventa uma regra, ela adota a
    mesma regra que o relatório usaria.
    """
    config = (
        await session.execute(
            select(ConfiguracaoAcademica).where(
                ConfiguracaoAcademica.ano_letivo_id == ano_letivo_id,
            )
        )
    ).scalar_one_or_none()
    if config is None:
        return 7.0, 75.0
    return float(config.media_aprovacao), float(config.frequencia_minima)


# ---------------------------------------------------------------------------
# Matrículas
# ---------------------------------------------------------------------------


async def matriculas_ativas(
    session: AsyncSession,
    aluno_id: uuid.UUID,
) -> list[Matricula]:
    """Matrículas ATIVAS de um aluno. Toda nota/frequência de um aluno sai daqui."""
    return list(
        (
            await session.execute(
                select(Matricula).where(
                    Matricula.aluno_id == aluno_id,
                    Matricula.status == StatusMatricula.ATIVA,
                )
            )
        ).scalars().all()
    )


async def alunos_da_turma(
    session: AsyncSession,
    turma_id: uuid.UUID,
) -> list[tuple[Aluno, Matricula]]:
    """Alunos matriculados numa turma. Usado SEMPRE após o escopo resolver a
    turma — o `turma_id` chega aqui já autorizado pelo builder."""
    linhas = (
        await session.execute(
            select(Aluno, Matricula)
            .join(Matricula, Matricula.aluno_id == Aluno.id)
            .where(
                Matricula.turma_id == turma_id,
                Matricula.status == StatusMatricula.ATIVA,
            )
            .order_by(Aluno.nome)
        )
    ).all()
    return [(aluno, matricula) for aluno, matricula in linhas]


# ---------------------------------------------------------------------------
# Médias
# ---------------------------------------------------------------------------


async def medias_por_disciplina(
    session: AsyncSession,
    matricula_id: uuid.UUID,
    *,
    bimestre: int | None = None,
) -> list[MediaDisciplina]:
    """Média ponderada por disciplina (`sum(nota*peso)/sum(peso)`).

    A ponderação pelo peso da avaliação é o que o `reports/service.py` faz, e o
    que o professor se entende por "média". Recuperações ficam de fora.

    O cálculo roda em SQL (`SUM`/`COUNT`), não em Python: assim o banco devolve
    já agregado e o processador não precisa carregar linha por linha.
    """
    filtros = [Nota.matricula_id == matricula_id]
    if bimestre is not None:
        filtros.append(Avaliacao.bimestre == bimestre)

    # O agrupamento inclui `Avaliacao.bimestre` e a reagrupação final é feita em
    # Python de propósito. A alternativa seria `func.group_concat`/`string_agg`,
    # mas o nome da função difere entre PostgreSQL e SQLite — e o primeiro nome
    # que try/except deixaria passar seria um erro em produção, no Postgres.
    linhas = (
        await session.execute(
            select(
                Disciplina.nome,
                Alocacao.id,
                Avaliacao.bimestre,
                func.sum(Nota.valor * Avaliacao.peso),
                func.sum(Avaliacao.peso),
                func.count(Nota.id),
            )
            .select_from(Nota)
            .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
            .join(Alocacao, Alocacao.id == Avaliacao.alocacao_id)
            .join(Disciplina, Disciplina.id == Alocacao.disciplina_id)
            .where(*filtros, Avaliacao.tipo.notin_(_TIPOS_EXCLUIDOS_DA_MEDIA))
            .group_by(Disciplina.nome, Alocacao.id, Avaliacao.bimestre)
            .order_by(Disciplina.nome, Avaliacao.bimestre)
        )
    ).all()

    # Acumula as SOMAS, nunca as médias: média de média ponderada não fecha.
    # Só no fim divide. É o mesmo cálculo do `reports/service.py`, que também
    # acumula os pesos antes de dividir.
    acumulado: dict[tuple[str, uuid.UUID], dict] = {}
    for disciplina_nome, alocacao_id, bimestre, soma, total_pesos, qtd in linhas:
        if not total_pesos or float(total_pesos) <= 0:
            continue
        entrada = acumulado.setdefault(
            (disciplina_nome, alocacao_id),
            {"soma": 0.0, "pesos": 0.0, "notas": 0, "bimestres": set()},
        )
        entrada["soma"] += float(soma)
        entrada["pesos"] += float(total_pesos)
        entrada["notas"] += int(qtd)
        entrada["bimestres"].add(int(bimestre))

    medias = [
        MediaDisciplina(
            disciplina=chave[0],
            alocacao_id=chave[1],
            media=round(dados["soma"] / dados["pesos"], 2),
            quantidade_notas=dados["notas"],
            bimestres=sorted(dados["bimestres"]),
        )
        for chave, dados in acumulado.items()
    ]
    return sorted(medias, key=lambda m: m.disciplina)


async def media_geral(
    session: AsyncSession,
    matricula_id: uuid.UUID,
    *,
    bimestre: int | None = None,
) -> float | None:
    """Média geral ponderada de TODAS as disciplinas.

    Atenção: a média geral NÃO é a média das médias por disciplina. Cada
    disciplina entra com o peso das suas avaliações, que é como o
    `dashboard` calcula. Misturar as duas coisas daria um número que não
    corresponde a nenhum lugar do ePass.
    """
    filtros = [Nota.matricula_id == matricula_id]
    if bimestre is not None:
        filtros.append(Avaliacao.bimestre == bimestre)

    linha = (
        await session.execute(
            select(func.sum(Nota.valor * Avaliacao.peso), func.sum(Avaliacao.peso))
            .select_from(Nota)
            .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
            .where(*filtros, Avaliacao.tipo.notin_(_TIPOS_EXCLUIDOS_DA_MEDIA))
        )
    ).one()

    if not linha[1] or float(linha[1]) <= 0:
        return None
    return round(float(linha[0]) / float(linha[1]), 2)


# ---------------------------------------------------------------------------
# Frequência
# ---------------------------------------------------------------------------


async def resumo_frequencia(
    session: AsyncSession,
    matricula: Matricula,
    *,
    bimestre: int | None = None,
) -> ResumoFrequencia | None:
    """Frequência percentual do aluno na turma da matrícula.

    Quando `bimestre` vem preenchido, filtra pelas chamadas dentro da janela de
    meses do bimestre (mesma regra do relatório). Sem bimestre, considera todas
    as chamadas da turma.

    `falta_justificada` conta como presença — igual ao relatório.
    """
    turma_id = matricula.turma_id

    filtros_chamada = [Alocacao.turma_id == turma_id]
    if bimestre is not None and bimestre in _MESES_POR_BIMESTRE:
        mes_ini, mes_fim = _MESES_POR_BIMESTRE[bimestre]
        ano = await _ano_da_turma(session, turma_id)
        if ano is None:
            return None
        ultimo_dia = calendar.monthrange(ano, mes_fim)[1]
        filtros_chamada.append(
            func.date(Chamada.data_hora_aula).between(
                date(ano, mes_ini, 1), date(ano, mes_fim, ultimo_dia),
            )
        )

    contagens = (
        await session.execute(
            select(Frequencia.status, func.count(Frequencia.id))
            .select_from(Frequencia)
            .join(Chamada, Chamada.id == Frequencia.chamada_id)
            .join(Alocacao, Alocacao.id == Chamada.alocacao_id)
            .where(Frequencia.matricula_id == matricula.id, *filtros_chamada)
            .group_by(Frequencia.status)
        )
    ).all()

    por_status = {status: int(total) for status, total in contagens}
    presencas = por_status.get(StatusFrequencia.PRESENTE, 0)
    justificadas = por_status.get(StatusFrequencia.FALTA_JUSTIFICADA, 0)
    faltas = por_status.get(StatusFrequencia.FALTA, 0)
    total = presencas + justificadas + faltas

    if total == 0:
        return None

    percentual = round((presencas + justificadas) / total * 100, 2)
    _, minimo = await regras_academicas(session, matricula.turma.ano_letivo_id)
    return ResumoFrequencia(
        percentual=percentual,
        presencas=presencas,
        faltas=faltas,
        faltas_justificadas=justificadas,
        total_registros=total,
        minimo=minimo,
    )


async def _ano_da_turma(session: AsyncSession, turma_id: uuid.UUID) -> int | None:
    """Ano letivo da turma. `None` quando a turma não existe mais."""
    return (
        await session.execute(
            select(AnoLetivo.ano)
            .join(Turma, Turma.ano_letivo_id == AnoLetivo.id)
            .where(Turma.id == turma_id)
        )
    ).scalar_one_or_none()


async def faltas_recentes(
    session: AsyncSession,
    matricula: Matricula,
    limite: int = 10,
) -> list[tuple[date, str]]:
    """Datas das faltas (não justificadas) mais recentes — `(data, disciplina)`."""
    linhas = (
        await session.execute(
            select(
                func.date(Chamada.data_hora_aula),
                Disciplina.nome,
            )
            .select_from(Frequencia)
            .join(Chamada, Chamada.id == Frequencia.chamada_id)
            .join(Alocacao, Alocacao.id == Chamada.alocacao_id)
            .join(Disciplina, Disciplina.id == Alocacao.disciplina_id)
            .where(
                Frequencia.matricula_id == matricula.id,
                Frequencia.status == StatusFrequencia.FALTA,
            )
            .order_by(Chamada.data_hora_aula.desc())
            .limit(limite)
        )
    ).all()
    return [(quando, disciplina) for quando, disciplina in linhas]


# ---------------------------------------------------------------------------
# Situação
# ---------------------------------------------------------------------------


def classificar_situacao(
    media: float | None,
    percentual_frequencia: float | None,
    media_aprovacao: float,
    frequencia_minima: float,
) -> str:
    """Situação estimada de um aluno — a MESMA regra do `reports/service.py`.

    Regras, em ordem:
      - frequência abaixo do mínimo reprova, independente da média;
      - sem nota suficiente para calcular, fica "sem dados";
      - média abaixo da corte reprova;
      - em cima da corte, aprovado.

    A diferença em relação ao relatório é que aqui não há conceito de
    recuperação anual (que depende dos 4 bimestres). Por isso o rótulo é
    "estimada": a Atena diz a leitura, e o boletim diz o oficial.
    """
    if percentual_frequencia is not None and percentual_frequencia < frequencia_minima:
        return SituacaoAluno.REPROVADO.value
    if media is None:
        return "sem_dados"
    if media < media_aprovacao:
        return SituacaoAluno.REPROVADO.value
    return SituacaoAluno.APROVADO.value


async def resumo_aluno(
    session: AsyncSession,
    matricula: Matricula,
) -> ResumoAluno:
    """Retrato consolidado: média, frequência e situação estimada."""
    media_aprovacao, frequencia_minima = await regras_academicas(
        session, matricula.turma.ano_letivo_id,
    )
    media = await media_geral(session, matricula.id)
    frequencia = await resumo_frequencia(session, matricula)

    return ResumoAluno(
        aluno_id=matricula.aluno_id,
        nome=matricula.aluno.nome,
        matricula_id=matricula.id,
        turma_nome=matricula.turma.nome or matricula.turma.codigo,
        serie_nome=matricula.turma.serie.nome if matricula.turma.serie else "-",
        turno=formatar_turno(matricula.turma.turno),
        media_geral=media,
        media_aprovacao=media_aprovacao,
        frequencia=frequencia,
        frequencia_minima=frequencia_minima,
        situacao_estimada=classificar_situacao(
            media,
            frequencia.percentual if frequencia else None,
            media_aprovacao,
            frequencia_minima,
        ),
    )


def formatar_turno(turno) -> str:
    return {
        "manha": "Manhã",
        "tarde": "Tarde",
        "integral": "Integral",
    }.get(getattr(turno, "value", str(turno)), "-")
