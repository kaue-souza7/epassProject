"""Context builders de SECRETARIA e ADMIN.

Escopo: institucional (o que o RBAC já permite a esses perfis). Ainda assim,
o builder NÃO faz `SELECT *` em tabela sensível: consulta apenas contagens e
listas com os campos necessários para a pergunta.

NÃO é reutilizado por outros perfis: a allowlist em `intent.py` impede que
coordenador/cantineiro alcancem estas intenções.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.context.base import (
    ResultadoContexto,
    formatar_data,
    formatar_decimal,
    formatar_enum,
)
from app.modules.ai.context.comum import MAX_LINHAS
from app.modules.allocations.models import Alocacao
from app.modules.cantina.models import Pedido, Produto
from app.modules.classes.models import Turma
from app.modules.communication.models import Aviso, AvisoDestinatario, Ocorrencia
from app.modules.document_requests.models import SolicitacaoDocumento
from app.modules.enrollments.models import Matricula
from app.modules.series.models import Serie
from app.modules.students.models import Aluno
from app.modules.subjects.models import Disciplina
from app.modules.teachers.models import ProfessorProfile
from app.modules.users.models import Usuario
from app.shared.enums import (
    Perfil,
    StatusAviso,
    StatusMatricula,
    StatusOcorrencia,
    StatusPedido,
    StatusSolicitacaoDocumento,
)


# ---------------------------------------------------------------------------
# 7) matriculas_contagem
# ---------------------------------------------------------------------------
async def matriculas_contagem(session: AsyncSession) -> ResultadoContexto:
    resultado = ResultadoContexto(
        intencao="matriculas_contagem", fontes=["matriculas", "alunos"],
    )

    total_matriculas = (
        await session.execute(
            select(func.count())
            .select_from(Matricula)
            .where(Matricula.status == StatusMatricula.ATIVA)
        )
    ).scalar_one()

    alunos_distintos = (
        await session.execute(
            select(func.count(func.distinct(Matricula.aluno_id)))
            .where(Matricula.status == StatusMatricula.ATIVA)
        )
    ).scalar_one()

    alunos_ativos = (
        await session.execute(
            select(func.count()).select_from(Aluno).where(Aluno.ativo.is_(True))
        )
    ).scalar_one()

    resultado.adicionar(f"Alunos matriculados (matrícula ativa): {alunos_distintos}")
    resultado.adicionar(f"Total de matrículas ativas: {total_matriculas}")
    resultado.adicionar(f"Alunos com cadastro ativo: {alunos_ativos}")
    resultado.resumo = (
        f"Há {alunos_distintos} aluno(s) com matrícula ativa e "
        f"{alunos_ativos} aluno(s) com cadastro ativo."
    )
    return resultado


# ---------------------------------------------------------------------------
# 8) avisos_nao_lidos_por_responsavel
# ---------------------------------------------------------------------------
async def avisos_nao_lidos_por_responsavel(
    session: AsyncSession,
    referencia_aviso: str | None = None,
) -> ResultadoContexto:
    """Responsáveis que ainda NÃO visualizaram o(s) aviso(s) publicado(s).

    Escopo institucional: é uma informação agregada, não dados de um
    responsável específico. Ainda assim, só agrega CONTAGENS e NOME+TÍTULO —
    nunca o conteúdo integral dos avisos nem dados de contato.

    `referencia_aviso` vem da linguagem natural ("... o aviso da reunião de
    pais?"). Quando presente, o filtro entra no WHERE: só o aviso citado é
    consultado. Sem ela, o escopo é "todos os avisos publicados" — que ainda é
    um recorte institucional autorizado, não um `SELECT *` de tabela sensível.
    """
    resultado = ResultadoContexto(
        intencao="avisos_nao_lidos_por_responsavel",
        fontes=["avisos", "avisos_destinatarios", "usuarios"],
    )

    filtros = [
        Usuario.perfil == Perfil.RESPONSAVEL,
        Aviso.status == StatusAviso.PUBLICADO,
        AvisoDestinatario.lido_em.is_(None),
    ]
    if referencia_aviso:
        filtros.append(Aviso.titulo.ilike(f"%{referencia_aviso}%"))

    query = (
        select(Aviso, Usuario)
        .join(AvisoDestinatario, AvisoDestinatario.aviso_id == Aviso.id)
        .join(Usuario, Usuario.id == AvisoDestinatario.usuario_id)
        .where(*filtros)
        .order_by(Aviso.publicado_em.desc(), Usuario.nome)
    )
    linhas = (await session.execute(query)).all()

    if not linhas:
        resultado.vazio = True
        if referencia_aviso:
            resultado.resumo = (
                f"Não há responsáveis sem visualização para o aviso "
                f"'{referencia_aviso}'."
            )
        else:
            resultado.resumo = (
                "Não há avisos publicados com responsáveis pendentes de leitura."
            )
        return resultado

    por_aviso: dict[uuid.UUID, dict] = {}
    for aviso, usuario in linhas:
        registro = por_aviso.setdefault(
            aviso.id,
            {
                "titulo": aviso.titulo,
                "publicado_em": aviso.publicado_em,
                "pendentes": 0,
                "nomes": [],
            },
        )
        if len(registro["nomes"]) < MAX_LINHAS:
            registro["nomes"].append(usuario.nome)
        registro["pendentes"] += 1

    resultado.adicionar(f"Quantidade de avisos no escopo: {len(por_aviso)}")
    for _aviso_id, registro in por_aviso.items():
        resultado.adicionar(
            f"- Aviso: {registro['titulo']} "
            f"(publicado em {formatar_data(registro['publicado_em'])}) — "
            f"{registro['pendentes']} responsável(is) ainda não visualizaram",
        )
        resultado.adicionar(
            f"  Responsáveis pendentes (até {MAX_LINHAS}): "
            + ", ".join(registro["nomes"])
        )

    total_pendentes = sum(r["pendentes"] for r in por_aviso.values())
    resultado.resumo = (
        f"Há {total_pendentes} visualização(ões) pendente(s) de avisos "
        f"por responsáveis, em {len(por_aviso)} aviso(s)."
    )
    return resultado


# ---------------------------------------------------------------------------
# alunos_sem_matricula
# ---------------------------------------------------------------------------
async def alunos_sem_matricula(session: AsyncSession) -> ResultadoContexto:
    """Alunos com cadastro ativo que não têm matrícula ativa.

    Este é o relatório que a secretaria mais usa no dia a dia: é a lista de
    quem está no cadastro mas sem turma, e portanto sem nota, sem frequência e
    sem boletim.
    """
    matriculados = select(Matricula.aluno_id).where(
        Matricula.status == StatusMatricula.ATIVA,
    )
    linhas = (
        await session.execute(
            select(Aluno.id, Aluno.nome, Aluno.data_entrada)
            .where(Aluno.ativo.is_(True), Aluno.id.notin_(matriculados))
            .order_by(Aluno.nome)
            .limit(MAX_LINHAS)
        )
    ).all()

    resultado = ResultadoContexto(
        intencao="alunos_sem_matricula", fontes=["alunos", "matriculas"],
    )

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Todos os alunos ativos possuem matrícula ativa."
        return resultado

    resultado.adicionar(f"Alunos ativos sem matrícula ativa: {len(linhas)}")
    for _aluno_id, nome, data_entrada in linhas:
        resultado.adicionar(
            f"- {nome} (entrada em {formatar_data(data_entrada)})"
        )

    resultado.resumo = (
        f"Há {len(linhas)} aluno(s) ativo(s) sem matrícula ativa."
    )
    return resultado


# ---------------------------------------------------------------------------
# turmas_ocupacao
# ---------------------------------------------------------------------------
async def turmas_ocupacao(session: AsyncSession) -> ResultadoContexto:
    """Ocupação e vagas de cada turma ativa."""
    linhas = (
        await session.execute(
            select(
                Turma.id, Turma.codigo, Turma.nome, Turma.vagas_total,
                Turma.turno, Serie.nome, func.count(Matricula.id),
            )
            .join(Serie, Serie.id == Turma.serie_id)
            .outerjoin(
                Matricula,
                (Matricula.turma_id == Turma.id)
                & (Matricula.status == StatusMatricula.ATIVA),
            )
            .where(Turma.ativo.is_(True))
            # `serie.numero` entra no GROUP BY porque aparece no ORDER BY:
            # o PostgreSQL exige toda coluna de ordenação agregada no grupo.
            .group_by(
                Turma.id, Turma.codigo, Turma.nome, Turma.vagas_total,
                Turma.turno, Serie.nome, Serie.numero,
            )
            .order_by(Serie.numero, Turma.codigo)
            .limit(MAX_LINHAS)
        )
    ).all()

    resultado = ResultadoContexto(
        intencao="turmas_ocupacao", fontes=["turmas", "matriculas", "series"],
    )

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Não há turmas ativas cadastradas."
        return resultado

    total_matriculas = 0
    lotadas: list[str] = []
    resultado.adicionar(f"Turmas ativas: {len(linhas)}")
    for turma_id, codigo, nome, vagas, turno, serie_nome, matriculas in linhas:
        resultado.turmas_autorizadas.append(turma_id)
        total_matriculas += int(matriculas)
        resultado.adicionar(
            f"- {nome or codigo} ({serie_nome}, {formatar_enum(turno)}): "
            f"{matriculas} de {vagas} vagas ocupadas"
        )
        if int(matriculas) >= int(vagas):
            lotadas.append(nome or codigo)

    resultado.adicionar(f"Total de matrículas ativas nessas turmas: {total_matriculas}")
    resultado.adicionar(f"Turmas lotadas: {len(lotadas)}")
    if lotadas:
        resultado.adicionar("Turmas lotadas: " + ", ".join(lotadas))

    resultado.resumo = (
        f"Há {len(linhas)} turma(s) ativa(s), {len(lotadas)} delas lotada(s), "
        f"com {total_matriculas} matrícula(s) no total."
    )
    return resultado


# ---------------------------------------------------------------------------
# alunos_por_serie
# ---------------------------------------------------------------------------
async def alunos_por_serie(session: AsyncSession) -> ResultadoContexto:
    """Distribuição de alunos e turmas por série."""
    linhas = (
        await session.execute(
            select(
                Serie.numero, Serie.nome,
                func.count(func.distinct(Matricula.aluno_id)),
                func.count(Matricula.id),
            )
            .select_from(Serie)
            .join(Turma, Turma.serie_id == Serie.id)
            .join(
                Matricula,
                (Matricula.turma_id == Turma.id)
                & (Matricula.status == StatusMatricula.ATIVA),
            )
            .where(Serie.ativo.is_(True), Turma.ativo.is_(True))
            .group_by(Serie.numero, Serie.nome)
            .order_by(Serie.numero)
        )
    ).all()

    resultado = ResultadoContexto(
        intencao="alunos_por_serie", fontes=["series", "turmas", "matriculas"],
    )

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Não há séries com turmas ativas."
        return resultado

    resultado.adicionar(f"Séries com turmas ativas: {len(linhas)}")
    for numero, nome, alunos_distintos, total_matriculas in linhas:
        resultado.adicionar(
            f"- {nome} ({numero}º ano): {alunos_distintos} aluno(s), "
            f"{total_matriculas} matrícula(s)"
        )

    resultado.resumo = (
        f"Há alunos matriculados em {len(linhas)} série(s) distintas."
    )
    return resultado


# ---------------------------------------------------------------------------
# documentos_pendentes
# ---------------------------------------------------------------------------
async def documentos_pendentes(session: AsyncSession) -> ResultadoContexto:
    """Fila de solicitações de documentos aguardando atendimento."""
    pendentes = (
        await session.execute(
            select(SolicitacaoDocumento)
            .where(
                SolicitacaoDocumento.status.in_([
                    StatusSolicitacaoDocumento.PENDENTE,
                    StatusSolicitacaoDocumento.EM_ANALISE,
                ]),
            )
            .order_by(SolicitacaoDocumento.created_at)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    total = (
        await session.execute(
            select(func.count())
            .select_from(SolicitacaoDocumento)
            .where(
                SolicitacaoDocumento.status.in_([
                    StatusSolicitacaoDocumento.PENDENTE,
                    StatusSolicitacaoDocumento.EM_ANALISE,
                ]),
            )
        )
    ).scalar_one()

    resultado = ResultadoContexto(
        intencao="documentos_pendentes", fontes=["solicitacoes_documento"],
    )

    if not pendentes:
        resultado.vazio = True
        resultado.resumo = "Não há solicitações de documentos pendentes."
        return resultado

    resultado.adicionar(f"Solicitações aguardando atendimento: {total}")
    for solicitacao in pendentes:
        resultado.adicionar(
            f"- {formatar_enum(solicitacao.tipo)} | {formatar_enum(solicitacao.status)} "
            f"| {solicitacao.aluno.nome} | pedido em "
            f"{formatar_data(solicitacao.created_at)}"
        )

    resultado.resumo = (
        f"Há {total} solicitação(ões) de documento aguardando atendimento."
    )
    return resultado


# ---------------------------------------------------------------------------
# ocorrencias_abertas
# ---------------------------------------------------------------------------
async def ocorrencias_abertas(session: AsyncSession) -> ResultadoContexto:
    """Ocorrências abertas na instituição, agregadas por severidade."""
    por_severidade = (
        await session.execute(
            select(Ocorrencia.severidade, func.count(Ocorrencia.id))
            .where(
                Ocorrencia.status.in_([
                    StatusOcorrencia.ABERTA,
                    StatusOcorrencia.EM_ANDAMENTO,
                ]),
            )
            .group_by(Ocorrencia.severidade)
        )
    ).all()

    total = sum(int(total_) for _severidade, total_ in por_severidade)

    resultado = ResultadoContexto(
        intencao="ocorrencias_abertas", fontes=["ocorrencias"],
    )

    if total == 0:
        resultado.vazio = True
        resultado.resumo = "Não há ocorrências em aberto na instituição."
        return resultado

    resultado.adicionar(f"Ocorrências em aberto: {total}")
    for severidade, quantidade in por_severidade:
        resultado.adicionar(
            f"- Severidade {formatar_enum(severidade)}: {quantidade}"
        )

    linhas = (
        await session.execute(
            select(Ocorrencia, Aluno)
            .join(Aluno, Aluno.id == Ocorrencia.aluno_id, isouter=True)
            .where(
                Ocorrencia.status.in_([
                    StatusOcorrencia.ABERTA,
                    StatusOcorrencia.EM_ANDAMENTO,
                ]),
            )
            .order_by(Ocorrencia.severidade.desc(), Ocorrencia.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).all()

    resultado.adicionar("Ocorrências mais recentes:")
    for ocorrencia, aluno in linhas:
        resultado.adicionar(
            f"- {aluno.nome if aluno else '(turma)'} | {ocorrencia.titulo} "
            f"[{formatar_enum(ocorrencia.severidade)}, "
            f"{formatar_enum(ocorrencia.tipo)}, "
            f"{formatar_enum(ocorrencia.status)}]"
        )

    resultado.resumo = f"Há {total} ocorrência(s) em aberto na instituição."
    return resultado


# ---------------------------------------------------------------------------
# matriculas_recentes
# ---------------------------------------------------------------------------
async def matriculas_recentes(session: AsyncSession) -> ResultadoContexto:
    """Matrículas mais recentes."""
    linhas = (
        await session.execute(
            select(Matricula)
            .where(Matricula.status == StatusMatricula.ATIVA)
            .order_by(Matricula.data_matricula.desc(), Matricula.created_at.desc())
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado = ResultadoContexto(
        intencao="matriculas_recentes", fontes=["matriculas", "alunos", "turmas"],
    )

    if not linhas:
        resultado.vazio = True
        resultado.resumo = "Não há matrículas ativas registradas."
        return resultado

    resultado.adicionar(f"Matrículas ativas encontradas: {len(linhas)}")
    for matricula in linhas:
        resultado.adicionar(
            f"- {matricula.aluno.nome} | turma: "
            f"{matricula.turma.nome or matricula.turma.codigo} | "
            f"matrícula em {formatar_data(matricula.data_matricula)}"
        )

    resultado.resumo = f"Foram listadas {len(linhas)} matrícula(s) recente(s)."
    return resultado


# ---------------------------------------------------------------------------
# professores_alocacoes
# ---------------------------------------------------------------------------
async def professores_alocacoes(session: AsyncSession) -> ResultadoContexto:
    """Corpo docente ativo e cobertura de alocações."""
    total_professores = (
        await session.execute(
            select(func.count())
            .select_from(ProfessorProfile)
            .where(ProfessorProfile.ativo.is_(True))
        )
    ).scalar_one()

    com_alocacao = (
        await session.execute(
            select(func.count(func.distinct(Alocacao.professor_id)))
            .where(Alocacao.data_fim.is_(None))
        )
    ).scalar_one()

    sem_alocacao = max(int(total_professores) - int(com_alocacao), 0)
    total_alocacoes = (
        await session.execute(
            select(func.count()).select_from(Alocacao).where(
                Alocacao.data_fim.is_(None),
            )
        )
    ).scalar_one()

    resultado = ResultadoContexto(
        intencao="professores_alocacoes",
        fontes=["professor_profiles", "alocacoes", "turmas", "disciplinas"],
    )

    if total_professores == 0:
        resultado.vazio = True
        resultado.resumo = "Não há professores cadastrados."
        return resultado

    resultado.adicionar(
        f"Professores ativos: {total_professores} | "
        f"Com alocação ativa: {com_alocacao} | Sem alocação ativa: {sem_alocacao}"
    )
    resultado.adicionar(f"Alocações ativas: {total_alocacoes}")

    # WHERE alocacoes.data_fim IS NULL (alocação ativa)
    linhas = (
        await session.execute(
            select(Alocacao, Usuario, Turma, Disciplina)
            .join(Usuario, Usuario.id == Alocacao.professor_id)
            .join(Turma, Turma.id == Alocacao.turma_id)
            .join(Disciplina, Disciplina.id == Alocacao.disciplina_id)
            .where(Alocacao.data_fim.is_(None))
            .order_by(Usuario.nome)
            .limit(MAX_LINHAS)
        )
    ).all()

    resultado.adicionar("Alocações ativas:")
    for _alocacao, usuario, turma, disciplina in linhas:
        resultado.adicionar(
            f"- {usuario.nome} | {disciplina.nome} | {turma.nome or turma.codigo}"
        )
        resultado.turmas_autorizadas.append(turma.id)

    resultado.resumo = (
        f"Há {total_professores} professor(es) ativo(s), {sem_alocacao} sem "
        f"alocação ativa e {total_alocacoes} alocação(ões) em andamento."
    )
    return resultado


# ---------------------------------------------------------------------------
# pedidos_cantina_pendentes
# ---------------------------------------------------------------------------
async def pedidos_cantina_pendentes(session: AsyncSession) -> ResultadoContexto:
    """Pedidos de lanche aguardando na cantina."""
    por_status = (
        await session.execute(
            select(Pedido.status, func.count(Pedido.id))
            .where(Pedido.status.notin_([StatusPedido.CANCELADO, StatusPedido.RETIRADO]))
            .group_by(Pedido.status)
        )
    ).all()

    total = sum(int(quantidade) for _status, quantidade in por_status)

    resultado = ResultadoContexto(
        intencao="pedidos_cantina_pendentes", fontes=["pedidos"],
    )

    if total == 0:
        resultado.vazio = True
        resultado.resumo = "Não há pedidos de lanche pendentes na cantina."
        return resultado

    resultado.adicionar(f"Pedidos não finalizados: {total}")
    for status, quantidade in por_status:
        resultado.adicionar(f"- {formatar_enum(status)}: {quantidade}")

    linhas = (
        await session.execute(
            select(Pedido)
            .where(Pedido.status.notin_([StatusPedido.CANCELADO, StatusPedido.RETIRADO]))
            .order_by(Pedido.data_referencia, Pedido.created_at)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado.adicionar("Pedidos na fila:")
    for pedido in linhas:
        resultado.adicionar(
            f"- {formatar_data(pedido.data_referencia)} | "
            f"{formatar_enum(pedido.status)} | {pedido.aluno.nome} | "
            f"R$ {formatar_decimal(pedido.valor_total)}"
        )

    resultado.resumo = f"Há {total} pedido(s) de lanche não finalizado(s)."
    return resultado


# ---------------------------------------------------------------------------
# estoque_baixo
# ---------------------------------------------------------------------------
async def estoque_baixo(session: AsyncSession) -> ResultadoContexto:
    """Produtos da cantina com estoque zerado ou abaixo do mínimo."""
    zerados = (
        await session.execute(
            select(Produto)
            .where(Produto.ativo.is_(True), Produto.estoque_atual == 0)
            .order_by(Produto.nome)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    total_zerados = (
        await session.execute(
            select(func.count()).select_from(Produto).where(
                Produto.ativo.is_(True), Produto.estoque_atual == 0,
            )
        )
    ).scalar_one()

    abaixo = (
        await session.execute(
            select(Produto)
            .where(
                Produto.ativo.is_(True),
                Produto.estoque_atual > 0,
                Produto.estoque_atual <= Produto.estoque_minimo,
            )
            .order_by(Produto.nome)
            .limit(MAX_LINHAS)
        )
    ).scalars().all()

    resultado = ResultadoContexto(intencao="estoque_baixo", fontes=["produtos"])

    if not abaixo and not total_zerados:
        resultado.vazio = True
        resultado.resumo = "Nenhum produto está com estoque baixo."
        return resultado

    # Os esgotados são listados pelo NOME, não só contados: a pergunta é "quais
    # produtos estão acabando", e a resposta "1 produto" não permite pedir a
    # reposição de nada.
    resultado.adicionar(f"Produtos esgotados: {total_zerados}")
    if zerados:
        resultado.adicionar("Produtos esgotados:")
        for produto in zerados[:MAX_LINHAS]:
            resultado.adicionar(
                f"  - {produto.nome} ({formatar_enum(produto.categoria)}): "
                f"0 em estoque, mínimo {produto.estoque_minimo}"
            )

    if abaixo:
        resultado.adicionar(f"Produtos abaixo do estoque mínimo: {len(abaixo)}")
        for produto in abaixo:
            resultado.adicionar(
                f"  - {produto.nome} ({formatar_enum(produto.categoria)}): "
                f"{produto.estoque_atual} em estoque, mínimo {produto.estoque_minimo}"
            )

    resultado.resumo = (
        f"Há {total_zerados} produto(s) esgotado(s) e {len(abaixo)} abaixo do estoque mínimo."
    )
    return resultado
