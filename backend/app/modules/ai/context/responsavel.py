"""Context builders do RESPONSÁVEL.

Todo acesso parte de `ResponsavelAlunoRepository.get_by_responsavel(usuario_id)`.
A lista de filhos é a RAIZ de todas as consultas: qualquer aluno fora dela é
inexistente para a IA. Não há uma única consulta sem esse filtro.

O que NUNCA entra no contexto: cpf, rg, endereço, telefone, e-mail, data de
nascimento, SenhaCpf e dados de outros alunos.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agenda.models import Evento, EventoDestinatario
from app.modules.ai.context.base import (
    AlunoNoEscopo,
    ResultadoContexto,
    escolher_aluno,
    formatar_data,
    formatar_decimal,
    formatar_enum,
)
from app.modules.ai.context.comum import (
    MAX_LINHAS,
    MediaDisciplina,
    ResumoAluno,
    faltas_recentes,
    matriculas_ativas,
    medias_por_disciplina,
    resumo_aluno,
    resumo_frequencia,
)
from app.modules.allocations.models import Alocacao
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.boletim.models import LiberacaoBoletim
from app.modules.bracelets.models import Bracelet
from app.modules.cantina.models import Pedido
from app.modules.cantina.programacao_models import ProgramacaoCantina
from app.modules.classes.models import Turma
from app.modules.communication.models import (
    Aviso,
    AvisoDestinatario,
    AvisoMensagem,
    Notificacao,
    Ocorrencia,
)
from app.modules.document_requests.models import SolicitacaoDocumento
from app.modules.enrollments.models import Matricula
from app.modules.financial.models import Movimentacao, Wallet
from app.modules.series.models import Serie
from app.modules.students.models import Aluno
from app.modules.students.repository import ResponsavelAlunoRepository
from app.modules.subjects.models import Disciplina
from app.shared.enums import (
    StatusAviso,
    StatusMatricula,
    StatusOcorrencia,
    TipoDestinoEvento,
    TipoMovimentacao,
    TipoProgramacao,
)


async def filhos_do_responsavel(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
) -> list[AlunoNoEscopo]:
    """Única porta de entrada: os filhos vinculados a este responsável."""
    vinculos = await ResponsavelAlunoRepository(session).get_by_responsavel(responsavel_id)
    if not vinculos:
        return []

    alunos_ids = [v.aluno_id for v in vinculos]
    parentesco_por_aluno = {v.aluno_id: v.parentesco for v in vinculos}

    # Traz apenas os alunos JÁ filtrados pelo vínculo (WHERE ... IN ids_autorizados).
    query = (
        select(Aluno, Matricula, Turma, Serie)
        .join(Matricula, Matricula.aluno_id == Aluno.id)
        .join(Turma, Turma.id == Matricula.turma_id)
        .join(Serie, Serie.id == Turma.serie_id)
        .where(
            Aluno.id.in_(alunos_ids),
            Matricula.status == StatusMatricula.ATIVA,
        )
        .order_by(Aluno.nome)
    )
    linhas = (await session.execute(query)).all()

    por_id: dict[uuid.UUID, AlunoNoEscopo] = {}
    for aluno, _matricula, turma, serie in linhas:
        existente = por_id.get(aluno.id)
        if existente is None:
            por_id[aluno.id] = AlunoNoEscopo(
                id=aluno.id,
                nome=aluno.nome,
                turma_nome=turma.nome or turma.codigo,
                serie_nome=serie.nome,
                parentesco=formatar_enum(parentesco_por_aluno.get(aluno.id)),
            )
        else:
            # Aluno com mais de uma matrícula ativa: mantém a primeira turma
            # apenas para identificação textual (o resto vem por matrícula).
            pass

    # Alunos vinculados porém sem matrícula ativa ainda precisam existir no
    # escopo, senão a IA diria "não encontrei" para um filho legítimo.
    faltantes = [i for i in alunos_ids if i not in por_id]
    if faltantes:
        extras = (
            await session.execute(select(Aluno).where(Aluno.id.in_(faltantes)))
        ).scalars().all()
        for aluno in extras:
            por_id[aluno.id] = AlunoNoEscopo(
                id=aluno.id,
                nome=aluno.nome,
                turma_nome=None,
                serie_nome=None,
                parentesco=formatar_enum(parentesco_por_aluno.get(aluno.id)),
            )

    return [por_id[i] for i in alunos_ids if i in por_id]


def _descricao_aluno(aluno: AlunoNoEscopo) -> str:
    partes = [f"Aluno: {aluno.nome}"]
    if aluno.turma_nome:
        partes.append(f"Turma: {aluno.turma_nome}")
    if aluno.serie_nome:
        partes.append(f"Série: {aluno.serie_nome}")
    return " | ".join(partes)


# ---------------------------------------------------------------------------
# 1) notas_aluno_ultima
# ---------------------------------------------------------------------------
async def notas_aluno_ultima(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    filhos = await filhos_do_responsavel(session, responsavel_id)
    aluno = escolher_aluno(
        filhos, nome_candidato, aluno_selecionado_id, mensagem=mensagem,
    )

    # WHERE notas.matricula_id IN (matrículas do aluno DENTRO do escopo)
    matriculas = (
        await session.execute(
            select(Matricula.id)
            .join(Turma, Turma.id == Matricula.turma_id)
            .where(
                Matricula.aluno_id == aluno.id,
                Matricula.status == StatusMatricula.ATIVA,
            )
        )
    ).scalars().all()

    resultado = ResultadoContexto(intencao="notas_aluno_ultima", fontes=["notas", "avaliacoes"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(_descricao_aluno(aluno))

    if not matriculas:
        resultado.vazio = True
        resultado.resumo = f"{aluno.nome} não possui matrícula ativa no ano letivo atual."
        return resultado

    query = (
        select(Nota, Avaliacao, Disciplina)
        .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
        .join(Alocacao, Alocacao.id == Avaliacao.alocacao_id)
        .join(Disciplina, Disciplina.id == Alocacao.disciplina_id)
        .where(Nota.matricula_id.in_(list(matriculas)))
        .order_by(Avaliacao.data_aplicacao.desc(), Nota.created_at.desc())
        .limit(1)
    )
    linha = (await session.execute(query)).first()

    if linha is None:
        resultado.vazio = True
        resultado.resumo = f"Nenhuma nota foi lançada para {aluno.nome} até o momento."
        return resultado

    nota, avaliacao, disciplina = linha
    resultado.adicionar(
        f"Última nota: {formatar_decimal(nota.valor)} "
        f"(de um total de {formatar_decimal(avaliacao.nota_maxima)})"
    )
    resultado.adicionar(f"Disciplina: {disciplina.nome}")
    resultado.adicionar(f"Avaliação: {avaliacao.titulo} (bimestre {avaliacao.bimestre})")
    resultado.adicionar(f"Data da avaliação: {formatar_data(avaliacao.data_aplicacao)}")
    resultado.resumo = (
        f"A última nota de {aluno.nome} foi {formatar_decimal(nota.valor)} "
        f"em {disciplina.nome}."
    )
    return resultado


# ---------------------------------------------------------------------------
# 2) ocorrencias_aluno
# ---------------------------------------------------------------------------
async def ocorrencias_aluno(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    filhos = await filhos_do_responsavel(session, responsavel_id)
    aluno = escolher_aluno(
        filhos, nome_candidato, aluno_selecionado_id, mensagem=mensagem,
    )

    # WHERE ocorrencias.aluno_id = <aluno já autorizado>
    query = (
        select(Ocorrencia)
        .where(Ocorrencia.aluno_id == aluno.id)
        .order_by(Ocorrencia.created_at.desc())
        .limit(10)
    )
    ocorrencias = (await session.execute(query)).scalars().all()

    resultado = ResultadoContexto(intencao="ocorrencias_aluno", fontes=["ocorrencias"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(_descricao_aluno(aluno))

    if not ocorrencias:
        resultado.vazio = True
        resultado.resumo = f"Não há nenhuma ocorrência registrada para {aluno.nome}."
        return resultado

    em_aberto = [o for o in ocorrencias if o.status != StatusOcorrencia.RESOLVIDA]
    resultado.adicionar(f"Total de ocorrências registradas: {len(ocorrencias)}")
    resultado.adicionar(f"Em aberto: {len(em_aberto)}")
    for ocorrencia in ocorrencias:
        resultado.adicionar(
            f"- [{formatar_enum(ocorrencia.status)}] {ocorrencia.titulo} "
            f"({formatar_enum(ocorrencia.severidade)}, "
            f"{formatar_enum(ocorrencia.tipo)}, {formatar_data(ocorrencia.created_at)})"
        )
    resultado.resumo = (
        f"{aluno.nome} tem {len(ocorrencias)} ocorrência(s) registrada(s), "
        f"{len(em_aberto)} em aberto."
    )
    return resultado


# ---------------------------------------------------------------------------
# 3) avisos_nao_lidos
# ---------------------------------------------------------------------------
async def avisos_nao_lidos(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
) -> ResultadoContexto:
    # WHERE avisos_destinatarios.usuario_id = <usuario logado> AND lido_em IS NULL
    query = (
        select(Aviso, AvisoDestinatario)
        .join(AvisoDestinatario, AvisoDestinatario.aviso_id == Aviso.id)
        .where(
            AvisoDestinatario.usuario_id == responsavel_id,
            AvisoDestinatario.lido_em.is_(None),
            Aviso.status == StatusAviso.PUBLICADO,
        )
        .order_by(Aviso.publicado_em.desc())
        .limit(10)
    )
    linhas = (await session.execute(query)).all()

    resultado = ResultadoContexto(
        intencao="avisos_nao_lidos", fontes=["avisos", "avisos_destinatarios"],
    )
    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Você não tem avisos não lidos."
        return resultado

    resultado.adicionar(f"Quantidade de avisos não lidos: {len(linhas)}")
    for aviso, _dest in linhas:
        resultado.adicionar(
            f"- {aviso.titulo} ({formatar_enum(aviso.prioridade)}, "
            f"publicado em {formatar_data(aviso.publicado_em)})"
        )
    resultado.resumo = f"Você tem {len(linhas)} aviso(s) não lido(s)."
    return resultado


# ---------------------------------------------------------------------------
# 4) saldo_carteira
# ---------------------------------------------------------------------------
async def saldo_carteira(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    filhos = await filhos_do_responsavel(session, responsavel_id)
    aluno = escolher_aluno(
        filhos, nome_candidato, aluno_selecionado_id, mensagem=mensagem,
    )

    # WHERE wallets.aluno_id = <aluno já autorizado>
    wallet = (
        await session.execute(select(Wallet).where(Wallet.aluno_id == aluno.id))
    ).scalar_one_or_none()

    resultado = ResultadoContexto(intencao="saldo_carteira", fontes=["wallets"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(_descricao_aluno(aluno))

    if wallet is None:
        resultado.vazio = True
        resultado.resumo = f"{aluno.nome} ainda não possui carteira cadastrada."
        return resultado

    resultado.adicionar(f"Saldo atual: R$ {formatar_decimal(wallet.saldo)}")
    resultado.adicionar(f"Situação da carteira: {formatar_enum(wallet.status)}")
    resultado.resumo = (
        f"O saldo da carteira de {aluno.nome} é de R$ {formatar_decimal(wallet.saldo)}."
    )
    return resultado


# ---------------------------------------------------------------------------
# Helpers compartilhados pelos builders do responsável
# ---------------------------------------------------------------------------


async def _aluno_e_matricula(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None,
    mensagem: str,
) -> tuple[AlunoNoEscopo, Matricula | None]:
    """Resolve o aluno no escopo e devolve a matrícula ativa (se houver).

    Devolver `(aluno, None)` — e não levantar erro — é deliberado nas intenções
    que respondem sobre a SITUAÇÃO DO VÍNCULO ("ele está matriculado?",
    "qual a turma dele?"). Nesses casos a pergunta faz sentido mesmo sem
    matrícula ativa, e a resposta é justamente "não está matriculado".
    """
    filhos = await filhos_do_responsavel(session, responsavel_id)
    aluno = escolher_aluno(
        filhos, nome_candidato, aluno_selecionado_id, mensagem=mensagem,
    )

    matriculas = await matriculas_ativas(session, aluno.id)
    return aluno, (matriculas[0] if matriculas else None)


def _cabecalho_aluno(resultado: ResultadoContexto, resumo: ResumoAluno) -> None:
    """Linha de identificação do aluno. Só dados não sensíveis."""
    resultado.adicionar(f"Aluno: {resumo.nome}")
    resultado.adicionar(
        f"Turma: {resumo.turma_nome} | Série: {resumo.serie_nome} "
        f"| Turno: {resumo.turno}"
    )


def _linhas_medias(
    resultado: ResultadoContexto,
    medias: list[MediaDisciplina],
    *,
    media_geral_valor: float | None,
) -> None:
    """Lista as médias por disciplina, sempre com a média geral ao lado.

    A média geral é derivada das disciplinas com peso de avaliação — não é a
    média aritmética das médias listadas. Escrever as duas com esses rótulos é o
    que impede o modelo de "recalcular" uma média que não existe.
    """
    if media_geral_valor is not None:
        resultado.adicionar(f"Média geral (ponderada): {formatar_decimal(media_geral_valor)}")
    resultado.adicionar("Médias por disciplina:")
    for media in medias:
        bimestres = ", ".join(str(b) for b in media.bimestres) or "-"
        resultado.adicionar(
            f"- {media.disciplina}: {formatar_decimal(media.media)} "
            f"(bimestre(s) {bimestres}, {media.quantidade_notas} nota(s))"
        )


# ---------------------------------------------------------------------------
# media_aluno
# ---------------------------------------------------------------------------
async def media_aluno(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
    *,
    bimestre: int | None = None,
    disciplina: str | None = None,
) -> ResultadoContexto:
    """Média geral + médias por disciplina + situação estimada."""
    aluno, matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(
        intencao="media_aluno",
        fontes=["notas", "avaliacoes", "alocacoes", "matriculas", "configuracoes_academicas"],
    )
    resultado.alunos_autorizados.append(aluno.id)

    if matricula is None:
        resultado.vazio = True
        resultado.adicionar(f"Aluno: {aluno.nome}")
        resultado.resumo = f"{aluno.nome} não possui matrícula ativa no ano letivo atual."
        return resultado

    resumo = await resumo_aluno(session, matricula)
    _cabecalho_aluno(resultado, resumo)
    resultado.turmas_autorizadas.append(matricula.turma_id)

    # Disciplina citada em linguagem natural vira filtro do SQL, nunca do
    # texto do modelo: o builder decide, o LLM não.
    medias = await medias_por_disciplina(session, matricula.id, bimestre=bimestre)
    if disciplina:
        alvo = disciplina.strip().lower()
        filtradas = [m for m in medias if alvo in m.disciplina.lower()]
        if not filtradas:
            resultado.vazio = True
            resultado.resumo = (
                f"Não há notas de '{disciplina}' para {aluno.nome}"
                + (f" no {bimestre}º bimestre." if bimestre else ".")
            )
            return resultado
        medias = filtradas

    if not medias:
        resultado.vazio = True
        resultado.resumo = (
            f"Ainda não há notas lançadas para {aluno.nome}"
            + (f" no {bimestre}º bimestre." if bimestre else ".")
        )
        return resultado

    resultado.adicionar(
        f"Média de aprovação configurada: {formatar_decimal(resumo.media_aprovacao)}"
    )
    _linhas_medias(resultado, medias, media_geral_valor=resumo.media_geral)

    situacao = resumo.situacao_estimada
    if situacao == "sem_dados":
        resultado.adicionar("Situação: ainda sem notas suficientes para avaliar.")
    else:
        resultado.adicionar(f"Situação estimada: {formatar_enum(situacao)}")

    resultado.resumo = (
        f"A média geral de {aluno.nome} é "
        f"{formatar_decimal(resumo.media_geral) if resumo.media_geral is not None else '—'}"
        f" (aprovação a partir de {formatar_decimal(resumo.media_aprovacao)})."
    )
    return resultado


# ---------------------------------------------------------------------------
# notas_aluno_historico
# ---------------------------------------------------------------------------
async def notas_aluno_historico(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
    *,
    bimestre: int | None = None,
    disciplina: str | None = None,
) -> ResultadoContexto:
    """Todas as notas lançadas, agrupadas por disciplina."""
    aluno, matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(
        intencao="notas_aluno_historico",
        fontes=["notas", "avaliacoes", "alocacoes", "disciplinas"],
    )
    resultado.alunos_autorizados.append(aluno.id)

    if matricula is None:
        resultado.vazio = True
        resultado.adicionar(f"Aluno: {aluno.nome}")
        resultado.resumo = f"{aluno.nome} não possui matrícula ativa neste ano letivo."
        return resultado

    filtros = [Nota.matricula_id == matricula.id]
    if bimestre is not None:
        filtros.append(Avaliacao.bimestre == bimestre)
    if disciplina:
        filtros.append(Disciplina.nome.ilike(f"%{disciplina.strip()}%"))

    # WHERE notas.matricula_id IN (matrícula já autorizada no escopo)
    linhas = (
        await session.execute(
            select(Nota, Avaliacao, Disciplina)
            .join(Avaliacao, Avaliacao.id == Nota.avaliacao_id)
            .join(Alocacao, Alocacao.id == Avaliacao.alocacao_id)
            .join(Disciplina, Disciplina.id == Alocacao.disciplina_id)
            .where(*filtros)
            .order_by(Disciplina.nome, Avaliacao.data_aplicacao.desc())
            .limit(MAX_LINHAS * 3)
        )
    ).all()

    if not linhas:
        resultado.vazio = True
        resultado.adicionar(f"Aluno: {aluno.nome}")
        resultado.resumo = "Não há notas lançadas nesse recorte."
        return resultado

    resultado.adicionar(f"Aluno: {aluno.nome}")
    resultado.adicionar(f"Turma: {matricula.turma.nome or matricula.turma.codigo}")
    resultado.adicionar(f"Total de notas encontradas: {len(linhas)}")
    resultado.adicionar("Notas por disciplina:")

    por_disciplina: dict[str, list[str]] = {}
    for nota, avaliacao, disciplina_obj in linhas:
        por_disciplina.setdefault(disciplina_obj.nome, []).append(
            f"{avaliacao.titulo} ({formatar_enum(avaliacao.tipo)}, "
            f"{formatar_decimal(nota.valor)} de "
            f"{formatar_decimal(avaliacao.nota_maxima)}, "
            f"{avaliacao.bimestre}º bimestre, "
            f"{formatar_data(avaliacao.data_aplicacao)})"
        )

    for nome_disciplina, itens in por_disciplina.items():
        resultado.adicionar(f"- {nome_disciplina}:")
        for item in itens[:MAX_LINHAS]:
            resultado.adicionar(f"    {item}")
        if len(itens) > MAX_LINHAS:
            resultado.adicionar(f"    ... e mais {len(itens) - MAX_LINHAS} avaliação(ões).")

    resultado.resumo = (
        f"Foram encontradas {len(linhas)} nota(s) de {aluno.nome} em "
        f"{len(por_disciplina)} disciplina(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# frequencia_aluno
# ---------------------------------------------------------------------------
async def frequencia_aluno(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
    *,
    bimestre: int | None = None,
) -> ResultadoContexto:
    """Frequência percentual, contagem de faltas e datas das faltas recentes."""
    aluno, matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(
        intencao="frequencia_aluno", fontes=["frequencias", "chamadas", "alocacoes"],
    )
    resultado.alunos_autorizados.append(aluno.id)

    if matricula is None:
        resultado.vazio = True
        resultado.adicionar(f"Aluno: {aluno.nome}")
        resultado.resumo = f"{aluno.nome} não possui matrícula ativa neste ano letivo."
        return resultado

    resultado.adicionar(f"Aluno: {aluno.nome}")
    resultado.adicionar(f"Turma: {matricula.turma.nome or matricula.turma.codigo}")
    resultado.turmas_autorizadas.append(matricula.turma_id)

    frequencia = await resumo_frequencia(session, matricula, bimestre=bimestre)
    if frequencia is None:
        resultado.vazio = True
        resultado.resumo = (
            f"Ainda não há registros de chamada para {aluno.nome}"
            + (f" no {bimestre}º bimestre." if bimestre else ".")
        )
        return resultado

    escopo = f"no {bimestre}º bimestre" if bimestre else "no ano letivo atual"
    resultado.adicionar(f"Frequência {escopo}: {formatar_decimal(frequencia.percentual)}%")
    resultado.adicionar(
        f"Faltas: {frequencia.faltas} | Justificadas: {frequencia.faltas_justificadas} "
        f"| Presenças: {frequencia.presencas} | Total de registros: {frequencia.total_registros}"
    )
    if frequencia.minimo is not None:
        resultado.adicionar(f"Frequência mínima exigida: {formatar_decimal(frequencia.minimo)}%")
        resultado.adicionar(
            f"Situação: {'abaixo do mínimo' if frequencia.abaixo_do_minimo else 'dentro do mínimo'}"
        )

    faltas = await faltas_recentes(session, matricula)
    if faltas:
        resultado.adicionar("Faltas mais recentes:")
        for quando, disciplina_nome in faltas:
            resultado.adicionar(f"- {formatar_data(quando)} — {disciplina_nome}")

    resultado.resumo = (
        f"A frequência de {aluno.nome} é de {formatar_decimal(frequencia.percentual)}%"
        + (f" no {bimestre}º bimestre." if bimestre else " no ano letivo atual.")
    )
    return resultado


# ---------------------------------------------------------------------------
# extrato_carteira
# ---------------------------------------------------------------------------
async def extrato_carteira(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Movimentações da carteira: recargas, consumos e estornos."""
    aluno, _matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(intencao="extrato_carteira", fontes=["movimentacoes"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    wallet = (
        await session.execute(select(Wallet).where(Wallet.aluno_id == aluno.id))
    ).scalar_one_or_none()

    if wallet is None:
        resultado.vazio = True
        resultado.resumo = f"{aluno.nome} ainda não possui carteira cadastrada."
        return resultado

    resultado.adicionar(f"Saldo atual: R$ {formatar_decimal(wallet.saldo)}")

    # WHERE movimentacoes.wallet_id = <carteira do aluno já autorizado>
    movimentacoes = (
        await session.execute(
            select(Movimentacao)
            .where(Movimentacao.wallet_id == wallet.id)
            .order_by(Movimentacao.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    if not movimentacoes:
        resultado.vazio = True
        resultado.resumo = f"Não há movimentações na carteira de {aluno.nome}."
        return resultado

    recargas = sum(1 for m in movimentacoes if m.tipo == TipoMovimentacao.RECARGA)
    consumos = sum(1 for m in movimentacoes if m.tipo == TipoMovimentacao.CONSUMO)
    estornos = sum(1 for m in movimentacoes if m.tipo == TipoMovimentacao.ESTORNO)
    resultado.adicionar(
        f"Movimentações encontradas: {len(movimentacoes)} "
        f"(recargas: {recargas}, consumos: {consumos}, estornos: {estornos})"
    )
    resultado.adicionar("Últimas movimentações:")
    for movimentacao in movimentacoes:
        resultado.adicionar(
            f"- {formatar_data(movimentacao.created_at)} | "
            f"{formatar_enum(movimentacao.tipo)} | R$ {formatar_decimal(movimentacao.valor)}"
            + (f" | {movimentacao.descricao}" if movimentacao.descricao else "")
        )

    resultado.resumo = (
        f"O saldo atual da carteira de {aluno.nome} é R$ {formatar_decimal(wallet.saldo)}, "
        f"com {len(movimentacoes)} movimentação(ões) recente(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# pedidos_cantina
# ---------------------------------------------------------------------------
async def pedidos_cantina(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Pedidos de lanche do aluno, com o status de cada um."""
    aluno, _matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(intencao="pedidos_cantina", fontes=["pedidos", "itens_pedido"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    # WHERE pedidos.aluno_id = <aluno já autorizado>
    pedidos = (
        await session.execute(
            select(Pedido)
            .where(Pedido.aluno_id == aluno.id)
            .order_by(Pedido.data_referencia.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    if not pedidos:
        resultado.vazio = True
        resultado.resumo = f"Não há pedidos de lanche registrados para {aluno.nome}."
        return resultado

    resultado.adicionar(f"Total de pedidos encontrados: {len(pedidos)}")
    for pedido in pedidos:
        itens = ", ".join(
            f"{item.quantidade}x {item.produto.nome}" for item in pedido.itens
        )
        resultado.adicionar(
            f"- {formatar_data(pedido.data_referencia)} | "
            f"{formatar_enum(pedido.status)} | R$ {formatar_decimal(pedido.valor_total)}"
            + (f" | {itens}" if itens else "")
        )

    hoje = date.today()
    de_hoje = [p for p in pedidos if p.data_referencia == hoje]
    resultado.resumo = (
        f"{aluno.nome} tem {len(pedidos)} pedido(s) de lanche registrado(s); "
        + (
            f"o pedido de hoje está {formatar_enum(de_hoje[0].status)}."
            if de_hoje
            else "nenhum pedido para hoje."
        )
    )
    return resultado


# ---------------------------------------------------------------------------
# programacao_cantina
# ---------------------------------------------------------------------------
async def programacao_cantina(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Programação semanal de lanches do aluno."""
    aluno, _matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(
        intencao="programacao_cantina", fontes=["programacao_cantina", "programacao_itens"],
    )
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    # WHERE programacao_cantina.aluno_id = <aluno já autorizado>
    programacoes = (
        await session.execute(
            select(ProgramacaoCantina)
            .where(
                ProgramacaoCantina.aluno_id == aluno.id,
                ProgramacaoCantina.ativo.is_(True),
            )
        )
    ).scalars().all()

    if not programacoes:
        resultado.vazio = True
        resultado.resumo = f"Não há programação de lanche cadastrada para {aluno.nome}."
        return resultado

    for programacao in programacoes:
        itens = ", ".join(
            f"{item.quantidade}x {item.produto.nome}" for item in programacao.itens
        )
        dia = "todos os dias" if programacao.tipo == TipoProgramacao.GERAL else "específico"
        resultado.adicionar(
            f"- {formatar_enum(programacao.dia_semana)} ({dia}, "
            f"{formatar_enum(programacao.tipo)}): {itens or 'sem itens'}"
        )

    resultado.resumo = (
        f"A programação semanal de lanche de {aluno.nome} tem "
        f"{len(programacoes)} dia(s) cadastrado(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# documentos_solicitacoes
# ---------------------------------------------------------------------------
async def documentos_solicitacoes(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Situação das solicitações de documento feitas pelo responsável.

    O filtro é duplo e ambos os lados importam: `responsavel_id` (quem pediu,
    vindo do token) E `aluno_id` dentro do escopo. Pedir pelo `responsavel_id`
    só já seria suficiente, mas os dois juntos tornam impossível um aluno de
    outro responsável aparecer aqui.
    """
    filhos = await filhos_do_responsavel(session, responsavel_id)
    aluno = escolher_aluno(filhos, nome_candidato, aluno_selecionado_id, mensagem=mensagem)

    resultado = ResultadoContexto(
        intencao="documentos_solicitacoes", fontes=["solicitacoes_documento"],
    )
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    # WHERE responsavel_id = <token> AND aluno_id = <aluno já autorizado>
    solicitacoes = (
        await session.execute(
            select(SolicitacaoDocumento)
            .where(
                SolicitacaoDocumento.responsavel_id == responsavel_id,
                SolicitacaoDocumento.aluno_id == aluno.id,
            )
            .order_by(SolicitacaoDocumento.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    if not solicitacoes:
        resultado.vazio = True
        resultado.resumo = f"Não há solicitações de documentos registradas para {aluno.nome}."
        return resultado

    resultado.adicionar(f"Total de solicitações: {len(solicitacoes)}")
    for solicitacao in solicitacoes:
        linha = (
            f"- {formatar_enum(solicitacao.tipo)} | "
            f"{formatar_enum(solicitacao.status)} | "
            f"solicitado em {formatar_data(solicitacao.created_at)}"
        )
        if solicitacao.atendido_em:
            linha += f" | atendido em {formatar_data(solicitacao.atendido_em)}"
        resultado.adicionar(linha)
        # A resposta da secretaria é texto do usuário e pode tentar injetar
        # instrução; entra como dado delimitado, nunca como comando.
        if solicitacao.resposta:
            resultado.adicionar(f"    Resposta da secretaria: {solicitacao.resposta}")

    pendentes = [
        s for s in solicitacoes
        if s.status.value in ("pendente", "em_analise")
    ]
    resultado.resumo = (
        f"Há {len(solicitacoes)} solicitação(ões) de documento para {aluno.nome}, "
        f"{len(pendentes)} ainda pendente(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# agenda_eventos
# ---------------------------------------------------------------------------
async def agenda_eventos(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    perfil,
) -> ResultadoContexto:
    """Próximos eventos da agenda do usuário.

    O `Evento` é global (a escola inteira tem uma agenda), então o recorte é
    duplo: `perfil_criador == perfil` (o que este perfil criou) OU o usuário
    está na lista de destinatários. Sem os dois lados, um responsável veria a
    agenda da direção.
    """
    resultado = ResultadoContexto(
        intencao="agenda_eventos", fontes=["eventos", "evento_destinatarios"],
    )
    agora = datetime.now(UTC)

    destino_por_perfil = {
        "professor": TipoDestinoEvento.PROFESSOR,
        "responsavel": TipoDestinoEvento.RESPONSAVEL,
        "turma": TipoDestinoEvento.TURMA,
        # Coordinator/admin/cantineiro don't have a destino enum. They see the
        # events they created themselves.
    }.get(str(getattr(perfil, "value", perfil)))

    filtros = [
        Evento.ativo.is_(True),
        Evento.data_inicio >= agora - timedelta(days=1),
    ]
    if destino_por_perfil is not None:
        filtros.append(
            Evento.id.in_(
                select(EventoDestinatario.evento_id).where(
                    EventoDestinatario.tipo_destino == destino_por_perfil,
                    EventoDestinatario.destino_id == usuario_id,
                )
            )
            | (Evento.perfil_criador == perfil)
        )
    else:
        filtros.append(Evento.perfil_criador == perfil)

    # WHERE evento ativo E (destinatário do usuário OU criado pelo mesmo perfil)
    eventos = (
        await session.execute(
            select(Evento).where(*filtros).order_by(Evento.data_inicio).limit(MAX_LINHAS)
        )
    ).scalars().all()

    if not eventos:
        resultado.vazio = True
        resultado.resumo = "Não há eventos previstos na sua agenda."
        return resultado

    resultado.adicionar(f"Eventos encontrados: {len(eventos)}")
    for evento in eventos:
        linha = (
            f"- {evento.titulo} | {formatar_data(evento.data_inicio)}"
            f" às {evento.data_inicio.strftime('%H:%M')}"
        )
        if evento.local:
            linha += f" | local: {evento.local}"
        resultado.adicionar(linha)
        if evento.descricao:
            resultado.adicionar(f"    {evento.descricao}")

    resultado.resumo = f"Há {len(eventos)} evento(s) previsto(s) na sua agenda."
    return resultado


# ---------------------------------------------------------------------------
# pulseira_aluno
# ---------------------------------------------------------------------------
async def pulseira_aluno(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Situação da pulseira de identificação do aluno."""
    aluno, _matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(intencao="pulseira_aluno", fontes=["bracelets"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    # WHERE bracelets.aluno_id = <aluno já autorizado>
    pulseira = (
        await session.execute(select(Bracelet).where(Bracelet.aluno_id == aluno.id))
    ).scalar_one_or_none()

    if pulseira is None:
        resultado.vazio = True
        resultado.resumo = f"{aluno.nome} não possui pulseira vinculada no momento."
        return resultado

    resultado.adicionar(f"Situação da pulseira: {formatar_enum(pulseira.status)}")
    resultado.adicionar(f"Código: {pulseira.codigo}")
    resultado.resumo = (
        f"A pulseira de {aluno.nome} está {formatar_enum(pulseira.status).lower()}."
    )
    return resultado


# ---------------------------------------------------------------------------
# matricula_aluno
# ---------------------------------------------------------------------------
async def matricula_aluno(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Situação da matrícula e a turma/série do aluno."""
    aluno, matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(intencao="matricula_aluno", fontes=["matriculas"])
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    if matricula is None:
        resultado.vazio = True
        resultado.resumo = f"{aluno.nome} não possui matrícula ativa no ano letivo atual."
        return resultado

    resultado.adicionar(f"Turma: {matricula.turma.nome or matricula.turma.codigo}")
    if matricula.turma.serie:
        resultado.adicionar(f"Série: {matricula.turma.serie.nome}")
    if matricula.turma.ano_letivo:
        resultado.adicionar(f"Ano letivo: {matricula.turma.ano_letivo.ano}")
    resultado.adicionar(f"Situação da matrícula: {formatar_enum(matricula.status)}")
    resultado.adicionar(f"Data da matrícula: {formatar_data(matricula.data_matricula)}")

    resultado.resumo = (
        f"{aluno.nome} está matriculado na turma "
        f"{matricula.turma.nome or matricula.turma.codigo}."
    )
    return resultado


# ---------------------------------------------------------------------------
# historico_escolar
# ---------------------------------------------------------------------------
async def historico_escolar(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
) -> ResultadoContexto:
    """Histórico de matrículas do aluno, com situação ao sair de cada período."""
    aluno, _matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(
        intencao="historico_escolar", fontes=["matriculas", "turmas", "anos_letivos"],
    )
    resultado.alunos_autorizados.append(aluno.id)
    resultado.adicionar(f"Aluno: {aluno.nome}")

    # WHERE matriculas.aluno_id = <aluno já autorizado>
    matriculas = (
        await session.execute(
            select(Matricula)
            .where(Matricula.aluno_id == aluno.id)
            .order_by(Matricula.data_matricula.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    if not matriculas:
        resultado.vazio = True
        resultado.resumo = f"Não há histórico de matrículas para {aluno.nome}."
        return resultado

    resultado.adicionar(f"Períodos registrados: {len(matriculas)}")
    for matricula in matriculas:
        ano = matricula.turma.ano_letivo.ano if matricula.turma.ano_letivo else "-"
        linha = (
            f"- {ano} | turma: {matricula.turma.nome or matricula.turma.codigo} "
            f"| {formatar_enum(matricula.status)}"
            f" | matrícula em {formatar_data(matricula.data_matricula)}"
        )
        if matricula.data_saida:
            linha += f" | saída em {formatar_data(matricula.data_saida)}"
        resultado.adicionar(linha)

    resultado.resumo = (
        f"O histórico escolar de {aluno.nome} tem {len(matriculas)} período(s) registrado(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# notificacoes_nao_lidas
# ---------------------------------------------------------------------------
async def notificacoes_nao_lidas(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
) -> ResultadoContexto:
    """Notificações não lidas do usuário."""
    # WHERE notificacoes.destinatario_id = <usuario logado> AND lida = false
    linhas = (
        await session.execute(
            select(Notificacao)
            .where(
                Notificacao.destinatario_id == responsavel_id,
                Notificacao.lida.is_(False),
            )
            .order_by(Notificacao.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado = ResultadoContexto(intencao="notificacoes_nao_lidas", fontes=["notificacoes"])

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Você não tem notificações não lidas."
        return resultado

    resultado.adicionar(f"Notificações não lidas: {len(linhas)}")
    for notificacao in linhas:
        resultado.adicionar(
            f"- [{formatar_enum(notificacao.tipo)}] {notificacao.titulo} "
            f"({formatar_data(notificacao.created_at)})"
        )
        if notificacao.mensagem:
            resultado.adicionar(f"    {notificacao.mensagem}")

    resultado.resumo = f"Você tem {len(linhas)} notificação(ões) não lida(s)."
    return resultado


# ---------------------------------------------------------------------------
# respostas_aviso
# ---------------------------------------------------------------------------
async def respostas_aviso(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    referencia_aviso: str | None = None,
) -> ResultadoContexto:
    """Respostas da secretaria em um aviso, dentro do escopo do responsável.

    O filtro de destinatário garante que o responsável só leia as respostas de
    avisos endereçados a ele (ou replies em que ele é o destinatário).
    """
    filtros = [AvisoDestinatario.usuario_id == responsavel_id]
    if referencia_aviso:
        filtros.append(Aviso.titulo.ilike(f"%{referencia_aviso}%"))

    linhas = (
        await session.execute(
            select(AvisoMensagem, Aviso)
            .join(Aviso, Aviso.id == AvisoMensagem.aviso_id)
            .join(AvisoDestinatario, AvisoDestinatario.aviso_id == Aviso.id)
            .where(*filtros)
            .order_by(AvisoMensagem.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).all()

    resultado = ResultadoContexto(
        intencao="respostas_aviso",
        fontes=["avisos_mensagens", "avisos", "avisos_destinatarios"],
    )

    if not linhas:
        resultado.vazio = True
        resultado.resumo = (
            "Não há respostas da secretaria para os avisos que você recebeu."
        )
        return resultado

    resultado.adicionar(f"Respostas encontradas: {len(linhas)}")
    for mensagem, aviso in linhas:
        resultado.adicionar(f"- Aviso: {aviso.titulo}")
        resultado.adicionar(
            f"    {formatar_data(mensagem.created_at)}: {mensagem.conteudo}"
        )

    resultado.resumo = f"Há {len(linhas)} resposta(s) da secretaria para seus avisos."
    return resultado


# ---------------------------------------------------------------------------
# boletim_aluno
# ---------------------------------------------------------------------------
async def boletim_aluno(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    mensagem: str = "",
    *,
    bimestre: int | None = None,
) -> ResultadoContexto:
    """Boletim bimestral — mas SÓ o que a escola já liberou.

    Esta é a única parte do sistema onde o horário importa de verdade: o
    `liberacoes_boletim` marca o que o professor já liberou, e o relatório
    (`reports/service.py:73`) esconde do responsável tudo que ainda não foi
    liberado. Aqui a IA respeita exatamente a mesma regra — perguntar sobre um
    bimestre não liberado responde "ainda não liberado", não a nota.

    Sem isso, a assistente seria o caminho mais fácil de burlar a data de
    publicação do boletim.
    """
    aluno, matricula = await _aluno_e_matricula(
        session, responsavel_id, nome_candidato, aluno_selecionado_id, mensagem,
    )

    resultado = ResultadoContexto(
        intencao="boletim_aluno",
        fontes=["liberacoes_boletim", "notas", "avaliacoes"],
    )
    resultado.alunos_autorizados.append(aluno.id)

    if matricula is None:
        resultado.vazio = True
        resultado.adicionar(f"Aluno: {aluno.nome}")
        resultado.resumo = f"{aluno.nome} não possui matrícula ativa neste ano letivo."
        return resultado

    resultado.adicionar(f"Aluno: {aluno.nome}")
    resultado.adicionar(f"Turma: {matricula.turma.nome or matricula.turma.codigo}")

    # WHERE liberacoes_boletim.turma_id = <turma já autorizada>
    filtros = [
        LiberacaoBoletim.turma_id == matricula.turma_id,
        LiberacaoBoletim.ativo.is_(True),
    ]
    if bimestre is not None:
        filtros.append(LiberacaoBoletim.bimestre == bimestre)

    liberacoes = (
        await session.execute(
            select(LiberacaoBoletim).where(*filtros).order_by(
                LiberacaoBoletim.bimestre.desc(),
            )
        )
    ).scalars().all()

    if not liberacoes:
        resultado.vazio = True
        resultado.resumo = (
            f"O boletim de {aluno.nome}"
            + (f" do {bimestre}º bimestre" if bimestre else "")
            + " ainda não foi liberado pela escola."
        )
        return resultado

    bimestres_liberados = sorted({liberacao.bimestre for liberacao in liberacoes})
    resultado.adicionar(
        "Bimestres liberados: " + ", ".join(str(b) for b in bimestres_liberados)
    )

    for bimestre_liberado in bimestres_liberados:
        resultado.adicionar(f"Notas do {bimestre_liberado}º bimestre:")
        medias = await medias_por_disciplina(
            session, matricula.id, bimestre=bimestre_liberado,
        )
        if not medias:
            resultado.adicionar("  (sem notas lançadas neste bimestre)")
            continue
        for media in medias:
            resultado.adicionar(
                f"  - {media.disciplina}: {formatar_decimal(media.media)}"
            )

    resultado.resumo = (
        f"O boletim de {aluno.nome} está liberado para o(s) bimestre(s) "
        + ", ".join(str(b) for b in bimestres_liberados)
        + "."
    )
    return resultado
