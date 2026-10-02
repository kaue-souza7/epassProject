"""Testes dos context builders da cobertura ampliada da Atena.

Estes testes exercitam os builders DIRETAMENTE (sem passar pelo LLM), porque o
que precisa ser provado aqui não é a redação da resposta — é o ESCOPO do dado
que entra no prompt.

Três invariantes são verificadas em todos os builders:

  1. **Autorização**: o builder nunca devolve dado de fora do escopo. Um
     responsável com dois filhos não enxerga o terceiro aluno de outro
     responsável; um professor não enxerga turma em que não leciona.
  2. **Anti-alucinação mecânica**: todo número que a IA pode falar precisa
     estar no contexto. `test_guardrail_aceita_todo_numero_do_contexto` roda o
     guardrail real sobre um resumo sintético e falha se algum número
     adderado for cortado.
  3. **Vazio ≠ erro**: "consultou e não achou" é uma resposta válida, com
     `vazio=True` — nunca uma exceção.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.modules.ai.context import (
    REGISTRO,
    construir_contexto,
    intencoes_sem_builder,
    verificar_cobertura,
)
from app.modules.ai.context import cantina as ctx_cantina
from app.modules.ai.context import coordenacao as ctx_coordenacao
from app.modules.ai.context import professor as ctx_professor
from app.modules.ai.context import responsavel as ctx_responsavel
from app.modules.ai.context import secretaria as ctx_secretaria
from app.modules.ai.context.base import ResultadoContexto
from app.modules.ai.guardrails import validar_resposta
from app.modules.ai.intent import INTENCOES, INTENCOES_POR_NOME, ResultadoIntencao
from app.shared.enums import (
    Perfil,
    StatusFrequencia,
    StatusMatricula,
    StatusOcorrencia,
    StatusPedido,
    StatusPulseira,
    StatusSolicitacaoDocumento,
    TipoMovimentacao,
    TipoProgramacao,
)
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_ano_letivo,
    create_avaliacao,
    create_aviso,
    create_chamada,
    create_configuracao_academica,
    create_disciplina,
    create_evento,
    create_evento_destinatario,
    create_frequencia,
    create_item_pedido,
    create_liberacao_boletim,
    create_matricula,
    create_movimentacao,
    create_nota,
    create_notificacao,
    create_ocorrencia,
    create_pedido,
    create_prazo_liberacao,
    create_produto,
    create_professor,
    create_programacao_cantina,
    create_programacao_item,
    create_pulseira,
    create_responsavel_aluno,
    create_solicitacao_documento,
    create_turma,
    create_usuario,
    create_wallet,
)

# `asyncio_mode = "auto"` no pyproject: pytest-asyncio já converte as funções
# `async def`, não é preciso `pytestmark` aqui.


# ===========================================================================
# COBERTURA E CONSISTÊNCIA
# ===========================================================================


def test_catalogo_e_registro_batem():
    """Toda intenção tem builder e todo builder tem intenção.

    `verificar_cobertura()` é chamada no boot do app; aqui garantimos que ela
    não está só passando por acidente.
    """
    verificar_cobertura()
    assert intencoes_sem_builder() == []


def test_cada_intencao_tem_descricao_legivel():
    """`descricao` alimenta `/ai/health` e é o contrato de revisão do catálogo."""
    for intencao in INTENCOES:
        assert intencao.descricao, intencao.nome
        assert len(intencao.descricao) > 15, intencao.nome


def test_todo_perfil_responde_algo():
    from app.modules.ai.context import intencoes_do_perfil

    for perfil in Perfil:
        assert intencoes_do_perfil(perfil), f"{perfil.value} sem nenhuma intenção"


# ===========================================================================
# HELPERS
# ===========================================================================


def _resultado(nome_intencao: str, **kwargs) -> ResultadoIntencao:
    """Monta um `ResultadoIntencao` como o classificador faria."""
    return ResultadoIntencao(
        intencao=INTENCOES_POR_NOME[nome_intencao],
        mensagem_original=kwargs.pop("mensagem", ""),
        mensagem_normalizada=kwargs.pop("normalizada", ""),
        **kwargs,
    )


async def _com_aluno(session, nome="Maria Souza", saldo=50.0):
    """Cria responsável + aluno + turma + matrícula + carteira."""
    resp = await create_usuario(session, nome="Ana Responsável", perfil=Perfil.RESPONSAVEL)
    aluno = await create_aluno(session, nome=nome)
    await create_responsavel_aluno(session, aluno.id, resp.id)
    turma = await create_turma(session, codigo="A1", nome="Turma A1")
    matricula = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    wallet = await create_wallet(session, aluno_id=aluno.id, saldo=saldo)
    return resp, aluno, turma, matricula, wallet


# ===========================================================================
# RESPONSÁVEL — COBERTURA AMPLIADA
# ===========================================================================


async def test_media_aluno_traz_media_geral_e_por_disciplina(session):
    resp, aluno, turma, matricula, _ = await _com_aluno(session)

    prof = await create_professor(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    avaliacao = await create_avaliacao(session, alocacao_id=aloc.id, peso=2)
    await create_nota(session, avaliacao_id=avaliacao.id, matricula_id=matricula.id, valor=8.0)

    ctx = await ctx_responsavel.media_aluno(session, resp.id, None)
    texto = "\n".join(ctx.fatos)

    assert ctx.vazio is False
    assert "8,00" in texto          # média geral ponderada
    assert "Matemática" in texto     # por disciplina
    assert "Média de aprovação configurada" in texto
    assert aluno.id in ctx.alunos_autorizados


async def test_media_aluno_filtra_por_disciplina_citada(session):
    """`nota de Matemática` vira filtro no SQL, não no texto do modelo."""
    resp, _aluno, turma, matricula, _ = await _com_aluno(session)

    prof = await create_professor(session)
    mat = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    avaliacao_mat = await create_avaliacao(session, alocacao_id=mat.id)
    await create_nota(session, avaliacao_mat.id, matricula.id, valor=9.0)
    hist = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    avaliacao_hist = await create_avaliacao(session, alocacao_id=hist.id)
    await create_nota(session, avaliacao_hist.id, matricula.id, valor=5.0)

    ctx = await ctx_responsavel.media_aluno(
        session, resp.id, None, disciplina="Matemática",
    )
    texto = "\n".join(ctx.fatos)
    assert "Matemática" in texto
    assert "História" not in texto
    assert "9,00" in texto


async def test_media_aluno_sem_nota_e_vazio_nao_excecao(session):
    resp, _aluno, _t, _m, _w = await _com_aluno(session)
    ctx = await ctx_responsavel.media_aluno(session, resp.id, None)
    assert ctx.vazio is True
    assert ctx.resumo


async def test_frequencia_aluno_conta_falta_justificada_como_presenca(session):
    """Regra do relatório: falta justificada conta como presença."""
    resp, _aluno, turma, matricula, _ = await _com_aluno(session)

    prof = await create_professor(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)

    for status in (
        StatusFrequencia.PRESENTE,
        StatusFrequencia.PRESENTE,
        StatusFrequencia.PRESENTE,
        StatusFrequencia.FALTA,
    ):
        chamada = await create_chamada(session, alocacao_id=aloc.id)
        await create_frequencia(session, chamada.id, matricula.id, status)

    justificativa = await create_chamada(session, alocacao_id=aloc.id)
    await create_frequencia(
        session, justificativa.id, matricula.id, StatusFrequencia.FALTA_JUSTIFICADA,
    )

    ctx = await ctx_responsavel.frequencia_aluno(session, resp.id, None)
    texto = "\n".join(ctx.fatos)
    assert ctx.vazio is False
    assert "80,00%" in texto          # 4 presenças em 5 registros
    assert "Justificadas: 1" in texto
    assert "Faltas: 1" in texto


async def test_frequencia_aluno_marca_abaixo_do_minimo(session):
    resp, _aluno, turma, matricula, _ = await _com_aluno(session)
    await create_configuracao_academica(session, turma.ano_letivo_id, frequencia_minima=90.0)

    prof = await create_professor(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    chamada = await create_chamada(session, alocacao_id=aloc.id)
    await create_frequencia(session, chamada.id, matricula.id, StatusFrequencia.FALTA)

    ctx = await ctx_responsavel.frequencia_aluno(session, resp.id, None)
    assert "abaixo do mínimo" in "\n".join(ctx.fatos)


async def test_extrato_carteira_lista_movimentacoes(session):
    resp, _aluno, _t, _m, wallet = await _com_aluno(session, saldo=100.0)
    await create_movimentacao(
        session, wallet.id, valor=20.0, tipo=TipoMovimentacao.CONSUMO, descricao="Salgado",
    )

    ctx = await ctx_responsavel.extrato_carteira(session, resp.id, None)
    texto = "\n".join(ctx.fatos)
    assert "80,00" in texto           # saldo após o consumo
    assert "Salgado" in texto
    assert ctx.vazio is False


async def test_extrato_carteira_nao_vaza_outro_aluno(session):
    """Dois responsáveis: cada um vê só o extrato do seu filho."""
    resp1, _a1, _t1, _m1, wallet1 = await _com_aluno(session, nome="Filho Um", saldo=10.0)
    resp2, _a2, _t2, _m2, wallet2 = await _com_aluno(session, nome="Filho Dois", saldo=99.0)
    await create_movimentacao(
        session, wallet2.id, valor=50.0, tipo=TipoMovimentacao.CONSUMO, descricao="SECRETO",
    )

    ctx = await ctx_responsavel.extrato_carteira(session, resp1.id, None)
    texto = "\n".join(ctx.fatos) + (ctx.resumo or "")
    assert "SECRETO" not in texto
    assert "99,00" not in texto


async def test_pedidos_cantina_mostra_status(session):
    resp, aluno, _t, _m, _w = await _com_aluno(session)
    produto = await create_produto(session, nome="Coxinha")
    pedido = await create_pedido(session, aluno.id, resp.id, status=StatusPedido.PRONTO)
    await create_item_pedido(session, pedido.id, produto.id, quantidade=2)

    ctx = await ctx_responsavel.pedidos_cantina(session, resp.id, None)
    texto = "\n".join(ctx.fatos)
    assert "Coxinha" in texto
    assert "2x" in texto
    assert "Pronto" in texto


async def test_programacao_cantina_lista_itens(session):
    resp, aluno, _t, _m, _w = await _com_aluno(session)
    produto = await create_produto(session, nome="Suco")
    prog = await create_programacao_cantina(
        session, aluno.id, resp.id, dia_semana="seg", tipo=TipoProgramacao.GERAL,
    )
    await create_programacao_item(session, prog.id, produto.id, quantidade=1)

    ctx = await ctx_responsavel.programacao_cantina(session, resp.id, None)
    assert "Suco" in "\n".join(ctx.fatos)


async def test_documentos_solicitacoes_responde_da_secretaria(session):
    resp, aluno, _t, _m, _w = await _com_aluno(session)
    await create_solicitacao_documento(
        session, resp.id, aluno.id,
        status=StatusSolicitacaoDocumento.CONCLUIDA,
        resposta="Documento liberado para retirada.",
    )

    ctx = await ctx_responsavel.documentos_solicitacoes(session, resp.id, None)
    texto = "\n".join(ctx.fatos)
    assert "Concluida" in texto
    assert "Documento liberado" in texto


async def test_documentos_solicitacoes_nao_mostra_pedido_de_outro_responsavel(session):
    """Anti-IDOR: o filtro exige responsavel_id E aluno_id no escopo."""
    resp1, _a1, _t1, _m1, _w1 = await _com_aluno(session, nome="Filho Um")
    resp2, a2, _t2, _m2, _w2 = await _com_aluno(session, nome="Filho Dois")
    await create_solicitacao_documento(
        session, resp2.id, a2.id, resposta="DOCUMENTO-PRIVADO",
    )

    ctx = await ctx_responsavel.documentos_solicitacoes(session, resp1.id, None)
    assert "DOCUMENTO-PRIVADO" not in "\n".join(ctx.fatos)


async def test_boletim_respeita_liberacao(session):
    """A IA não pode ser caminho para burlar a data de publicação do boletim."""
    resp, _aluno, turma, _matricula, _w = await _com_aluno(session)

    # Sem liberação nenhuma.
    ctx = await ctx_responsavel.boletim_aluno(session, resp.id, None)
    assert ctx.vazio is True
    assert "liberado" in (ctx.resumo or "").lower()

    # Com liberação.
    prof = await create_professor(session)
    disc = await create_disciplina(session, nome="Matemática")
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    await create_liberacao_boletim(
        session, prof.usuario_id, turma.id, disc.id, aloc.id, turma.ano_letivo_id, bimestre=1,
    )

    ctx = await ctx_responsavel.boletim_aluno(session, resp.id, None)
    assert ctx.vazio is False
    assert "liberados" in "\n".join(ctx.fatos)


async def test_pulseira_mostra_situacao(session):
    resp, aluno, _t, _m, _w = await _com_aluno(session)
    await create_pulseira(session, aluno.id, status=StatusPulseira.BLOQUEADA)

    ctx = await ctx_responsavel.pulseira_aluno(session, resp.id, None)
    assert "Bloqueada" in "\n".join(ctx.fatos)


async def test_matricula_aluno_informa_turma_e_serie(session):
    resp, _aluno, turma, _m, _w = await _com_aluno(session)
    ctx = await ctx_responsavel.matricula_aluno(session, resp.id, None)
    texto = "\n".join(ctx.fatos)
    assert "Turma:" in texto
    assert "Ativa" in texto


async def test_historico_escolar_lista_periodos(session):
    resp, aluno, _t, _m, _w = await _com_aluno(session)
    outra = await create_turma(session, codigo="B2", nome="Turma B2")
    await create_matricula(
        session, aluno_id=aluno.id, turma_id=outra.id, status=StatusMatricula.CONCLUIDA,
    )

    ctx = await ctx_responsavel.historico_escolar(session, resp.id, None)
    texto = "\n".join(ctx.fatos)
    assert "Concluida" in texto
    assert texto.count("Turma") >= 2


async def test_agenda_eventos_respeita_destinatario(session):
    resp, _aluno, _t, _m, _w = await _com_aluno(session)
    outro = await create_usuario(session, nome="Outro Responsável", perfil=Perfil.RESPONSAVEL)

    evento_meu = await create_evento(
        session, titulo="Reunião do meu filho",
        data_inicio=datetime.now(UTC) + timedelta(days=2),
    )
    await create_evento_destinatario(
        session, evento_meu.id, "RESPONSAVEL", resp.id,
    )

    evento_alheio = await create_evento(
        session, titulo="EVENTO-PRIVADO",
        data_inicio=datetime.now(UTC) + timedelta(days=2),
    )
    await create_evento_destinatario(
        session, evento_alheio.id, "RESPONSAVEL", outro.id,
    )

    ctx = await ctx_responsavel.agenda_eventos(session, resp.id, Perfil.RESPONSAVEL)
    texto = "\n".join(ctx.fatos)
    assert "Reunião do meu filho" in texto
    assert "EVENTO-PRIVADO" not in texto


async def test_notificacoes_nao_lidas_apenas_do_usuario(session):
    resp, _a, _t, _m, _w = await _com_aluno(session)
    outro = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    await create_notificacao(session, resp.id, titulo="NOTIF-MINHA")
    await create_notificacao(session, resp.id, titulo="NOTIF-LIDA", lida=True)
    await create_notificacao(session, outro.id, titulo="NOTIF-ALHEIA")

    ctx = await ctx_responsavel.notificacoes_nao_lidas(session, resp.id)
    texto = "\n".join(ctx.fatos)
    assert "NOTIF-MINHA" in texto
    assert "NOTIF-LIDA" not in texto
    assert "NOTIF-ALHEIA" not in texto


# ===========================================================================
# PROFESSOR
# ===========================================================================


async def test_minhas_turmas_lista_alocacoes(session):
    prof = await create_professor(session)
    turma = await create_turma(session, codigo="T9", nome="Nona")
    await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)

    ctx = await ctx_professor.minhas_turmas(session, prof.usuario_id)
    texto = "\n".join(ctx.fatos)
    assert "Nona" in texto
    assert "Total de turmas: 1" in texto


async def test_avaliacoes_sem_notas_conta_matriculas_sem_nota(session):
    prof = await create_professor(session)
    turma = await create_turma(session, codigo="T1")
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)

    a1 = await create_aluno(session, nome="Aluno Um")
    a2 = await create_aluno(session, nome="Aluno Dois")
    m1 = await create_matricula(session, aluno_id=a1.id, turma_id=turma.id)
    await create_matricula(session, aluno_id=a2.id, turma_id=turma.id)

    avaliacao = await create_avaliacao(session, alocacao_id=aloc.id, titulo="Prova 1")
    await create_nota(session, avaliacao.id, m1.id, valor=7.0)   # só um lançar

    ctx = await ctx_professor.avaliacoes_sem_notas(session, prof.usuario_id)
    texto = "\n".join(ctx.fatos)
    assert "Prova 1" in texto
    assert "1 de 2 aluno(s) sem nota" in texto


async def test_avaliacoes_sem_notas_vazio_quando_tudo_lancado(session):
    prof = await create_professor(session)
    turma = await create_turma(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    aluno = await create_aluno(session)
    matricula = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    avaliacao = await create_avaliacao(session, alocacao_id=aloc.id)
    await create_nota(session, avaliacao.id, matricula.id, valor=9.0)

    ctx = await ctx_professor.avaliacoes_sem_notas(session, prof.usuario_id)
    assert ctx.vazio is True


async def test_lista_alunos_turma_nao_vaza_outra_turma(session):
    prof = await create_professor(session)
    minha = await create_turma(session, codigo="M1", nome="Minha")
    outra = await create_turma(session, codigo="O1", nome="Outra")
    await create_alocacao(session, professor_id=prof.usuario_id, turma_id=minha.id)

    a_meu = await create_aluno(session, nome="Aluno Da Minha")
    a_outro = await create_aluno(session, nome="ALUNO-DE-OUTRA")
    await create_matricula(session, aluno_id=a_meu.id, turma_id=minha.id)
    await create_matricula(session, aluno_id=a_outro.id, turma_id=outra.id)

    ctx = await ctx_professor.lista_alunos_turma(session, prof.usuario_id)
    texto = "\n".join(ctx.fatos)
    assert "Aluno Da Minha" in texto
    assert "ALUNO-DE-OUTRA" not in texto
    assert outra.id not in ctx.turmas_autorizadas


async def test_lista_alunos_turma_filtra_por_turma_citada(session):
    prof = await create_professor(session)
    t1 = await create_turma(session, codigo="A1", nome="Primeira")
    t2 = await create_turma(session, codigo="B2", nome="Segunda")
    await create_alocacao(session, professor_id=prof.usuario_id, turma_id=t1.id)
    await create_alocacao(session, professor_id=prof.usuario_id, turma_id=t2.id)

    a1 = await create_aluno(session, nome="Aluno Da Primeira")
    a2 = await create_aluno(session, nome="Aluno Da Segunda")
    await create_matricula(session, aluno_id=a1.id, turma_id=t1.id)
    await create_matricula(session, aluno_id=a2.id, turma_id=t2.id)

    ctx = await ctx_professor.lista_alunos_turma(session, prof.usuario_id, nome_turma="Primeira")
    texto = "\n".join(ctx.fatos)
    assert "Aluno Da Primeira" in texto
    assert "Aluno Da Segunda" not in texto


async def test_turma_citada_que_nao_e_do_professor_nao_vaza(session):
    prof = await create_professor(session)
    minha = await create_turma(session, codigo="A1", nome="Minha")
    alheia = await create_turma(session, codigo="Z9", nome="Alheia")
    await create_alocacao(session, professor_id=prof.usuario_id, turma_id=minha.id)
    a = await create_aluno(session, nome="Segredo")
    await create_matricula(session, aluno_id=a.id, turma_id=alheia.id)

    ctx = await ctx_professor.lista_alunos_turma(session, prof.usuario_id, nome_turma="Alheia")
    texto = "\n".join(ctx.fatos) + (ctx.resumo or "")
    assert "Segredo" not in texto


async def test_media_disciplina_turma_agrupa_por_aluno(session):
    prof = await create_professor(session)
    turma = await create_turma(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    a = await create_aluno(session, nome="Aluno Média")
    m = await create_matricula(session, aluno_id=a.id, turma_id=turma.id)
    await create_nota(
        session, (await create_avaliacao(session, alocacao_id=aloc.id)).id, m.id, valor=7.5,
    )

    ctx = await ctx_professor.media_disciplina_turma(session, prof.usuario_id)
    assert "7,50" in "\n".join(ctx.fatos)


async def test_prazos_boletim_mostra_prazo_e_liberacao(session):
    prof = await create_professor(session)
    turma = await create_turma(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    disc = await create_disciplina(session)
    await create_prazo_liberacao(session, turma.ano_letivo_id, bimestre=1)
    await create_liberacao_boletim(
        session, prof.usuario_id, turma.id, disc.id, aloc.id, turma.ano_letivo_id, bimestre=1,
    )

    ctx = await ctx_professor.prazos_boletim(session, prof.usuario_id)
    texto = "\n".join(ctx.fatos)
    assert "Prazos de liberação" in texto
    assert "Liberações já feitas" in texto


async def test_avisos_turma_apenas_das_turmas_do_professor(session):
    prof = await create_professor(session)
    minha = await create_turma(session, codigo="M1")
    alheia = await create_turma(session, codigo="A1")
    await create_alocacao(session, professor_id=prof.usuario_id, turma_id=minha.id)

    await create_aviso(session, titulo="AVISO-MINHA", destinatario_turma_id=minha.id)
    await create_aviso(session, titulo="AVISO-ALHEIA", destinatario_turma_id=alheia.id)

    ctx = await ctx_professor.avisos_turma(session, prof.usuario_id)
    texto = "\n".join(ctx.fatos)
    assert "AVISO-MINHA" in texto
    assert "AVISO-ALHEIA" not in texto


async def test_chamadas_recentes_conta_registros(session):
    prof = await create_professor(session)
    turma = await create_turma(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    aluno = await create_aluno(session)
    m = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    chamada = await create_chamada(session, alocacao_id=aloc.id)
    await create_frequencia(session, chamada.id, m.id)

    ctx = await ctx_professor.chamadas_recentes(session, prof.usuario_id)
    assert "registro(s) de presença" in "\n".join(ctx.fatos)


async def test_professor_sem_alocacao_recebe_recusa_amigavel(session):
    prof = await create_professor(session)
    ctx = await ctx_professor.minhas_turmas(session, prof.usuario_id)
    assert ctx.vazio is True
    assert "alocações" in ctx.resumo


# ===========================================================================
# SECRETARIA / ADMIN
# ===========================================================================


async def test_alunos_sem_matricula_lista_apenas_desmatriculados(session):
    com = await create_aluno(session, nome="Com Matrícula")
    await create_aluno(session, nome="Sem Matrícula")
    await create_matricula(session, aluno_id=com.id)

    ctx = await ctx_secretaria.alunos_sem_matricula(session)
    texto = "\n".join(ctx.fatos)
    assert "Sem Matrícula" in texto
    assert "Com Matrícula" not in texto


async def test_turmas_ocupacao_marca_lotada(session):
    turma = await create_turma(session, codigo="L1", nome="Lotada", vagas_total=1)
    await create_matricula(session, turma_id=turma.id)

    ctx = await ctx_secretaria.turmas_ocupacao(session)
    texto = "\n".join(ctx.fatos)
    assert "Turmas lotadas: 1" in texto
    assert "Lotada" in texto


async def test_alunos_por_serie(session):
    await create_matricula(session)
    ctx = await ctx_secretaria.alunos_por_serie(session)
    assert "aluno(s)" in "\n".join(ctx.fatos)


async def test_documentos_pendentes_fila(session):
    resp = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    aluno = await create_aluno(session)
    await create_solicitacao_documento(session, resp.id, aluno.id)
    concluida = await create_solicitacao_documento(
        session, resp.id, aluno.id, status=StatusSolicitacaoDocumento.CONCLUIDA,
    )

    ctx = await ctx_secretaria.documentos_pendentes(session)
    texto = "\n".join(ctx.fatos)
    assert "aguardando atendimento: 1" in texto
    assert concluida.id is not None


async def test_ocorrencias_abertas_agrega_por_severidade(session):
    aluno = await create_aluno(session)
    await create_ocorrencia(session, aluno_id=aluno.id, status=StatusOcorrencia.ABERTA)
    await create_ocorrencia(session, aluno_id=aluno.id, status=StatusOcorrencia.EM_ANDAMENTO)
    resolvida = await create_ocorrencia(
        session, aluno_id=aluno.id, status=StatusOcorrencia.RESOLVIDA,
    )
    await session.flush()

    ctx = await ctx_secretaria.ocorrencias_abertas(session)
    texto = "\n".join(ctx.fatos)
    assert "em aberto: 2" in texto
    assert resolvida.id is not None


async def test_estoque_baixo_separa_esgotado_de_abaixo_do_minimo(session):
    await create_produto(session, nome="Esgotado", estoque_atual=0, estoque_minimo=2)
    await create_produto(session, nome="No Limite", estoque_atual=2, estoque_minimo=2)
    await create_produto(session, nome="Saudavel", estoque_atual=50, estoque_minimo=2)

    ctx = await ctx_secretaria.estoque_baixo(session)
    texto = "\n".join(ctx.fatos)
    assert "Esgotado" in texto
    assert "No Limite" in texto
    assert "Saudavel" not in texto
    assert "Produtos esgotados: 1" in texto


async def test_pedidos_cantina_pendentes_ignora_retirado(session):
    resp = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    a1 = await create_aluno(session, nome="Aluno Retirado")
    a2 = await create_aluno(session, nome="Aluno Pendente")
    await create_pedido(
        session, a1.id, resp.id, status=StatusPedido.RETIRADO, data_referencia=date.today(),
    )
    await create_pedido(
        session, a2.id, resp.id, status=StatusPedido.PENDENTE, data_referencia=date.today(),
    )

    ctx = await ctx_secretaria.pedidos_cantina_pendentes(session)
    texto = "\n".join(ctx.fatos)
    assert "Pedidos não finalizados: 1" in texto
    assert "Aluno Retirado" not in texto


async def test_professores_alocacoes_conta_sem_alocacao(session):
    await create_professor(session)          # sem alocação
    prof2 = await create_professor(session)
    await create_alocacao(session, professor_id=prof2.usuario_id)

    ctx = await ctx_secretaria.professores_alocacoes(session)
    assert "Sem alocação ativa: 1" in "\n".join(ctx.fatos)


async def test_matriculas_recentes(session):
    await create_matricula(session)
    ctx = await ctx_secretaria.matriculas_recentes(session)
    assert "Matrículas ativas encontradas" in "\n".join(ctx.fatos)


# ===========================================================================
# COORDENAÇÃO
# ===========================================================================


async def test_panorama_escolar_conta_agregados(session):
    await create_matricula(session)
    ctx = await ctx_coordenacao.panorama_escolar(session)
    texto = "\n".join(ctx.fatos)
    assert "Alunos cadastrados e ativos" in texto
    assert "Turmas ativas" in texto
    assert "Alocações de disciplina ativas" in texto


async def test_turmas_criticas_usa_media_de_corte_da_configuracao(session):
    ano = await create_ano_letivo(session, ano=2030, ativo=True)
    await create_configuracao_academica(session, ano.id, media_aprovacao=8.0)

    prof = await create_professor(session)
    turma = await create_turma(session, codigo="C1")
    turma.ano_letivo_id = ano.id
    await session.flush()

    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)
    baixo = await create_aluno(session, nome="Abaixo Da Corte")
    m_baixo = await create_matricula(session, aluno_id=baixo.id, turma_id=turma.id)
    await create_nota(
        session, (await create_avaliacao(session, alocacao_id=aloc.id)).id, m_baixo.id, valor=5.0,
    )

    ctx = await ctx_coordenacao.turmas_criticas(session)
    texto = "\n".join(ctx.fatos)
    assert "8,00" in texto           # média de corte da configuração
    assert "Abaixo Da Corte" in texto


async def test_alunos_atencao_exige_media_e_frequencia_baixas_ao_mesmo_tempo(session):
    """A interseção é o valor do relatório: um critério só não dispara."""
    ano = await create_ano_letivo(session, ano=2031, ativo=True)
    await create_configuracao_academica(
        session, ano.id, media_aprovacao=6.0, frequencia_minima=75.0,
    )

    prof = await create_professor(session)
    turma = await create_turma(session, codigo="R1")
    turma.ano_letivo_id = ano.id
    await session.flush()
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)

    # Nota baixa, presença alta → fora do relatório de atenção.
    a_ok = await create_aluno(session, nome="Nota Baixa Presenca Alta")
    m_ok = await create_matricula(session, aluno_id=a_ok.id, turma_id=turma.id)
    await create_nota(
        session, (await create_avaliacao(session, alocacao_id=aloc.id)).id, m_ok.id, valor=4.0,
    )
    for _ in range(3):
        c = await create_chamada(session, alocacao_id=aloc.id)
        await create_frequencia(session, c.id, m_ok.id, StatusFrequencia.PRESENTE)

    # Nota alta, presença baixa → também fora.
    a_freq = await create_aluno(session, nome="Nota Alta Presenca Baixa")
    m_freq = await create_matricula(session, aluno_id=a_freq.id, turma_id=turma.id)
    await create_nota(
        session, (await create_avaliacao(session, alocacao_id=aloc.id)).id, m_freq.id, valor=9.0,
    )
    for _ in range(3):
        c = await create_chamada(session, alocacao_id=aloc.id)
        await create_frequencia(session, c.id, m_freq.id, StatusFrequencia.FALTA)

    ctx = await ctx_coordenacao.alunos_atencao_coordenacao(session)
    texto = "\n".join(ctx.fatos)
    assert "Nota Baixa Presenca Alta" not in texto
    assert "Nota Alta Presenca Baixa" not in texto


async def test_alunos_atencao_inclui_quem_tem_os_dois_problemas(session):
    ano = await create_ano_letivo(session, ano=2032, ativo=True)
    await create_configuracao_academica(
        session, ano.id, media_aprovacao=6.0, frequencia_minima=75.0,
    )

    prof = await create_professor(session)
    turma = await create_turma(session, codigo="R2")
    turma.ano_letivo_id = ano.id
    await session.flush()
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)

    aluno = await create_aluno(session, nome="Dois Problemas")
    m = await create_matricula(session, aluno_id=aluno.id, turma_id=turma.id)
    await create_nota(
        session, (await create_avaliacao(session, alocacao_id=aloc.id)).id, m.id, valor=3.0,
    )
    for _ in range(4):
        c = await create_chamada(session, alocacao_id=aloc.id)
        await create_frequencia(session, c.id, m.id, StatusFrequencia.FALTA)

    ctx = await ctx_coordenacao.alunos_atencao_coordenacao(session)
    texto = "\n".join(ctx.fatos)
    assert "Dois Problemas" in texto
    # 4 faltas em 4 chamadas = 0% de frequência.
    assert "0,00%" in texto


# ===========================================================================
# CANTINA
# ===========================================================================


async def test_pedidos_cantina_hoje_apenas_data_de_hoje(session):
    resp = await create_usuario(session, perfil=Perfil.RESPONSAVEL)
    aluno = await create_aluno(session)
    await create_pedido(session, aluno.id, resp.id, data_referencia=date.today())
    await create_pedido(
        session, aluno.id, resp.id, data_referencia=date.today() - timedelta(days=5),
    )

    ctx = await ctx_cantina.pedidos_cantina_hoje(session)
    assert "fila: 1" in "\n".join(ctx.fatos)


async def test_cardapio_apenas_estoque_positivo(session):
    await create_produto(session, nome="Tem Estoque", estoque_atual=5)
    await create_produto(session, nome="SEM-ESTOQUE", estoque_atual=0)

    ctx = await ctx_cantina.cardapio_cantina(session)
    texto = "\n".join(ctx.fatos)
    assert "Tem Estoque" in texto
    assert "SEM-ESTOQUE" not in texto


async def test_estoque_cantina_marca_esgotado(session):
    await create_produto(session, nome="ESGOTADO", estoque_atual=0, estoque_minimo=3)

    ctx = await ctx_cantina.estoque_cantina(session)
    assert "ESGOTADO" in "\n".join(ctx.fatos)


async def test_saldo_aluno_cantina_encontra_por_nome(session):
    _resp, aluno, _t, _m, _w = await _com_aluno(session, nome="Joao Balcao", saldo=12.5)
    ctx = await ctx_cantina.saldo_aluno_cantina(session, "Joao Balcao", "")
    texto = "\n".join(ctx.fatos)
    assert "12,50" in texto
    assert "Ativa" in texto


async def test_saldo_aluno_cantina_nao_devolve_extrato(session):
    """Cantineiro tem `read_wallet`, não `read_wallet statement`: só o saldo."""
    _resp, _aluno, _t, _m, wallet = await _com_aluno(session, nome="Joao Extrato", saldo=30.0)
    await create_movimentacao(
        session, wallet.id, valor=5.0, tipo=TipoMovimentacao.CONSUMO, descricao="COMPRA-PRIVADA",
    )

    ctx = await ctx_cantina.saldo_aluno_cantina(session, "Joao Extrato", "")
    texto = "\n".join(ctx.fatos)
    assert "COMPRA-PRIVADA" not in texto
    assert "25,00" in texto


async def test_saldo_aluno_cantina_pediu_sem_nome(session):
    ctx = await ctx_cantina.saldo_aluno_cantina(session, None, "")
    assert ctx.vazio is True
    assert "nome do aluno" in ctx.resumo


async def test_saldo_aluno_cantina_nome_inexistente_nao_busca_global(session):
    await _com_aluno(session, nome="Aluno Conhecido", saldo=10.0)
    ctx = await ctx_cantina.saldo_aluno_cantina(session, "Fulano Que Nao Existe", "")
    assert ctx.vazio is True
    assert "Aluno Conhecido" not in "\n".join(ctx.fatos)


# ===========================================================================
# ANTI-ALUCINAÇÃO MECÂNICA
# ===========================================================================


@pytest.mark.parametrize(
    "nome_intencao",
    [
        "media_aluno", "frequencia_aluno", "extrato_carteira", "saldo_carteira",
        "turmas_ocupacao", "alunos_por_serie", "estoque_baixo", "panorama_escolar",
        "turmas_criticas", "estoque_cantina", "cardapio_cantina",
    ],
)
async def test_guardrail_aceita_todo_numero_do_contexto(session, nome_intencao):
    """O guardrail NÃO pode cortar um número que veio do próprio contexto.

    Este é o teste que impede a regressão maisCara do módulo: um builder novo
    que formata um número de um jeito que `_numeros_autorizados` não reconhece
    faria a IA responder "prefiro não afirmar" a uma resposta perfeitamente
    correta — falha silenciosa e muito difícil de diagnosticar em produção.
    """
    # Cenário único, mínimo, mas que produz fato COM NÚMERO para todos os
    # builders da lista: um aluno com nota fraca E alta (cobre "abaixo da média"
    # e "acima da média" ao mesmo tempo), frequência, movimentação de carteira,
    # ocorrência e dois produtos — um saudável e um no limite do mínimo.
    resp, _aluno, turma, matricula, wallet = await _com_aluno(session, saldo=45.5)
    prof = await create_professor(session)
    aloc = await create_alocacao(session, professor_id=prof.usuario_id, turma_id=turma.id)

    avaliacao_alta = await create_avaliacao(session, alocacao_id=aloc.id, titulo="Prova Alta")
    await create_nota(session, avaliacao_alta.id, matricula.id, valor=9.75)

    avaliacao_baixa = await create_avaliacao(session, alocacao_id=aloc.id, titulo="Prova Baixa")
    await create_nota(session, avaliacao_baixa.id, matricula.id, valor=4.25)

    await create_movimentacao(session, wallet.id, valor=4.5, tipo=TipoMovimentacao.CONSUMO)

    for _ in range(2):
        chamada = await create_chamada(session, alocacao_id=aloc.id)
        await create_frequencia(
            session, chamada.id, matricula.id, StatusFrequencia.PRESENTE,
        )

    await create_ocorrencia(session, aluno_id=_aluno.id)
    await create_produto(
        session, nome="Item Saudavel", preco=3.5, estoque_atual=40, estoque_minimo=1,
    )
    await create_produto(
        session, nome="Item No Limite", preco=2.75, estoque_atual=2, estoque_minimo=2,
    )

    perfil = (
        Perfil.RESPONSAVEL
        if nome_intencao in {
            "media_aluno", "frequencia_aluno", "extrato_carteira", "saldo_carteira",
        }
        else Perfil.ADMIN
    )
    resultado = _resultado(nome_intencao)
    ctx = await construir_contexto(
        session, resultado, usuario_id=resp.id, perfil=perfil,
    )

    # Nenhum builder da lista pode ficar sem dado nesse cenário: um skip aqui
    # significaria que o guardrail não foi verificado para aquela intenção.
    assert ctx.fatos, f"{nome_intencao}: sem dados no cenário mínimo"

    # O "resumo factual" é o que o prompt manda devolver literalmente.
    _, alertas = validar_resposta(ctx.resumo or ctx.fatos[0], ctx)
    assert not [a for a in alertas if a.startswith("numero_nao_autorizado")], (
        f"{nome_intencao}: o próprio contexto tem número que o guardrail rejeita -> {alertas}"
    )


async def test_guardrail_bloqueia_numero_que_nao_esta_no_contexto(session):
    """O outro lado da moeda: número inventado precisa ser barrado."""
    ctx = ResultadoContexto(intencao="saldo_carteira", fatos=["Saldo atual: R$ 50,00"])
    _, alertas = validar_resposta("O saldo é de R$ 999,00.", ctx)
    assert any(a.startswith("numero_nao_autorizado") for a in alertas)


# ===========================================================================
# DISPATCHER
# ===========================================================================


async def test_construir_contexto_recusa_intencao_sem_builder():
    """Defence in depth: intenção órfã vira recusa, nunca consulta genérica."""
    from dataclasses import replace

    from app.modules.ai.exceptions import IntencaoNaoPermitidaErro

    orfa = replace(
        INTENCOES_POR_NOME["saldo_carteira"], nome="intencao_que_nao_existe",
    )
    resultado = replace(
        _resultado("saldo_carteira"), intencao=orfa,
    )
    with pytest.raises(IntencaoNaoPermitidaErro):
        await construir_contexto(
            None, resultado, usuario_id=uuid.uuid4(), perfil=Perfil.RESPONSAVEL,
        )


async def test_registro_cobre_todas_as_intencoes_do_catalogo():
    assert set(REGISTRO) == {i.nome for i in INTENCOES}
