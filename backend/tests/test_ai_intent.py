"""Testes do roteador de intenções e da allowlist por perfil (Fase 2).

O roteador é a fronteira de segurança: é ele que impede um perfil de chegar
até um contexto que não lhe pertence. Estes testes travam esse contrato.
"""

from __future__ import annotations

import pytest

from app.modules.ai.context import intencoes_do_perfil
from app.modules.ai.exceptions import (
    IntencaoNaoPermitidaErro,
    IntencaoNaoReconhecidaErro,
)
from app.modules.ai.intent import INTENCOES, classificar, normalizar
from app.shared.enums import Perfil


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------
def test_normalizar_remove_acento_e_caixa():
    assert normalizar("  Última   NOTA do meu Filho? ") == "ultima nota do meu filho?"


# ---------------------------------------------------------------------------
# Classificação — as perguntas do enunciado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("perfil", "frase", "esperada"),
    [
        (Perfil.RESPONSAVEL, "Qual foi a última nota do meu filho?", "notas_aluno_ultima"),
        (Perfil.RESPONSAVEL, "Meu filho tem alguma ocorrência?", "ocorrencias_aluno"),
        (Perfil.RESPONSAVEL, "Quais avisos eu ainda não li?", "avisos_nao_lidos"),
        (Perfil.RESPONSAVEL, "Quanto há na carteira do meu filho?", "saldo_carteira"),
        (Perfil.PROFESSOR, "Quais alunos da minha turma estão com notas abaixo da média?",
         "alunos_abaixo_media"),
        (Perfil.PROFESSOR, "Tenho alguma ocorrência pendente?", "ocorrencias_pendentes"),
        (Perfil.SECRETARIA, "Quantos alunos estão matriculados?", "matriculas_contagem"),
        (Perfil.ADMIN, "Quantos alunos estão matriculados?", "matriculas_contagem"),
        (Perfil.ADMIN, "Quais responsáveis não visualizaram determinado aviso?",
         "avisos_nao_lidos_por_responsavel"),
    ],
)
def test_classifica_perguntas_do_enunciado(perfil, frase, esperada):
    assert classificar(frase, perfil).intencao.nome == esperada


def test_classificacao_ignora_causa_e_acento():
    r = classificar(
        "QuaIs AlUnOs Da MINHA TuRmA EstAo CoM NoTaS AbAiXo Da Media?",
        Perfil.PROFESSOR,
    )
    assert r.intencao.nome == "alunos_abaixo_media"


# ---------------------------------------------------------------------------
# Allowlist — a barreira de segurança
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("perfil", "frase"),
    [
        (Perfil.RESPONSAVEL, "Quantos alunos estão matriculados?"),
        (Perfil.RESPONSAVEL, "Quais responsáveis não visualizaram o aviso?"),
        (Perfil.RESPONSAVEL, "Quais alunos da minha turma estão abaixo da média?"),
        (Perfil.PROFESSOR, "Qual foi a última nota do meu filho?"),
        (Perfil.PROFESSOR, "Quais avisos eu ainda não li?"),
        (Perfil.PROFESSOR, "Quanto há na carteira do meu filho?"),
        (Perfil.SECRETARIA, "Qual foi a última nota do meu filho?"),
        (Perfil.SECRETARIA, "Quais alunos da minha turma estão abaixo da média?"),
        (Perfil.ADMIN, "Qual foi a última nota do meu filho?"),
        (Perfil.ADMIN, "Meu filho tem alguma ocorrência?"),
    ],
)
def test_intencao_de_outro_perfil_e_bloqueada(perfil, frase):
    with pytest.raises((IntencaoNaoPermitidaErro, IntencaoNaoReconhecidaErro)):
        classificar(frase, perfil)


def test_coordenador_tem_acesso_pedagogico():
    """Coordenação tem visão institucional de aluno/nota/frequência/ocorrência.

    Antes da cobertura completa, o perfil tinha allowlist VAZIA: qualquer pergunta
    caía em "não tenho acesso", mesmo o RBAC dando leitura de aluno, nota e
    frequência em escopo "all". O catálogo agora reflete o RBAC.
    """
    nomes = intencoes_do_perfil(Perfil.COORDENADOR)
    assert "turmas_criticas" in nomes
    assert "alunos_atencao_coordenacao" in nomes
    assert "panorama_escolar" in nomes


def test_cantineiro_tem_acesso_operacional():
    """Cantineiro responde de balcão: fila de hoje, cardápio, estoque, saldo."""
    nomes = intencoes_do_perfil(Perfil.CANTINEIRO)
    assert set(nomes) == {
        "pedidos_cantina_hoje", "cardapio_cantina",
        "estoque_cantina", "saldo_aluno_cantina", "agenda_eventos",
    }


def test_coordenador_obtem_agregado_institucional():
    """A coordenação é perfil institucional: o total da escola é função dela."""
    assert (
        classificar("Quantos alunos estão matriculados?", Perfil.COORDENADOR).intencao.nome
        == "matriculas_contagem"
    )


def test_cantineiro_nao_obtem_nada():
    with pytest.raises(IntencaoNaoReconhecidaErro):
        classificar("Qual foi a última nota do meu filho?", Perfil.CANTINEIRO)


def test_cantineiro_nao_obtem_dado_academico():
    """O cantineiro não tem escopo acadêmico no RBAC — nem média, nem faltas."""
    for frase in (
        "Qual a média do meu filho?",
        "Quantas faltas o meu filho tem?",
        "Quais notas o aluno tirou?",
    ):
        with pytest.raises((IntencaoNaoPermitidaErro, IntencaoNaoReconhecidaErro)):
            classificar(frase, Perfil.CANTINEIRO)


# ---------------------------------------------------------------------------
# Pedido de escopo amplo por perfil restrito
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("perfil", [Perfil.RESPONSAVEL, Perfil.PROFESSOR, Perfil.CANTINEIRO])
def test_pedido_de_dados_globais_e_negado(perfil):
    with pytest.raises(IntencaoNaoPermitidaErro):
        classificar("Quantos alunos de toda a escola estão matriculados?", perfil)


@pytest.mark.parametrize(
    "perfil", [Perfil.ADMIN, Perfil.SECRETARIA, Perfil.COORDENADOR],
)
def test_administracao_pode_consultar_o_total_da_escola(perfil):
    """Para secretaria/admin/coordenação o total institucional É a função deles.

    A regra "sem escopo amplo" vale para perfis restritos; para o perfil
    institucional, negar seria confundir segurança com chronicina.
    """
    resultado = classificar("Quantos alunos de toda a escola estão matriculados?", perfil)
    assert resultado.intencao.nome == "matriculas_contagem"


# ---------------------------------------------------------------------------
# Extração de nome de aluno (nunca vira busca global)
# ---------------------------------------------------------------------------
def test_extrai_nome_proprio_da_frase():
    r = classificar("Qual foi a última nota da Maria Souza?", Perfil.RESPONSAVEL)
    assert r.nome_aluno == "Maria Souza"


def test_nao_extrai_nome_quando_a_frase_nao_tem_nome():
    r = classificar("Qual foi a última nota do meu filho?", Perfil.RESPONSAVEL)
    assert r.nome_aluno is None


def test_palavra_comum_capitalizada_nao_vira_nome():
    r = classificar("Qual foi a Última Nota do Meu Filho?", Perfil.RESPONSAVEL)
    assert r.nome_aluno is None


# ---------------------------------------------------------------------------
# Contrato — cada intenção pertence a pelo menos um perfil
# ---------------------------------------------------------------------------
def test_toda_intencao_tem_perfis_e_requisitos():
    for intencao in INTENCOES:
        assert intencao.perfis, f"{intencao.nome} sem perfil"
        assert intencao.requisitos, f"{intencao.nome} sem sinônimos"
        assert intencao.descricao


def test_nome_das_intencoes_e_unico():
    nomes = [i.nome for i in INTENCOES]
    assert len(nomes) == len(set(nomes))


def test_matriz_de_permissao_fica_explicita():
    """Trava a allowlist para facilitar revisão de segurança futura.

    É a documentação executável de "quem pode perguntar o quê". Ao mudar o
    catálogo, este teste muda junto — de propósito: a matriz é revisada em
    code review, não descoberta em produção.
    """
    # Coordenação: visão pedagógica institucional (o RBAC dá aluno/nota/
    # frequência/ocorrência/aviso em escopo "all"), sem operação de cantina.
    pedagogica = {
        "matriculas_contagem", "avisos_nao_lidos_por_responsavel",
        "ocorrencias_abertas", "panorama_escolar", "turmas_criticas",
        "alunos_atencao_coordenacao", "agenda_eventos",
    }
    # Secretaria/admin: pedagógico + administrativo + operação de cantina.
    secretaria_admin = pedagogica | {
        "alunos_sem_matricula", "turmas_ocupacao", "alunos_por_serie",
        "documentos_pendentes", "pedidos_cantina_pendentes", "estoque_baixo",
        "matriculas_recentes", "professores_alocacoes",
        "saldo_aluno_cantina", "pedidos_cantina_hoje", "cardapio_cantina",
        "estoque_cantina",
    }

    esperado = {
        Perfil.RESPONSAVEL: {
            "notas_aluno_ultima", "media_aluno", "notas_aluno_historico",
            "boletim_aluno", "frequencia_aluno", "ocorrencias_aluno",
            "avisos_nao_lidos", "respostas_aviso", "notificacoes_nao_lidas",
            "saldo_carteira", "extrato_carteira", "pedidos_cantina",
            "programacao_cantina", "documentos_solicitacoes", "agenda_eventos",
            "pulseira_aluno", "matricula_aluno", "historico_escolar",
        },
        Perfil.PROFESSOR: {
            "alunos_abaixo_media", "ocorrencias_pendentes", "minhas_turmas",
            "avaliacoes_sem_notas", "media_disciplina_turma", "frequencia_turma",
            "lista_alunos_turma", "avisos_turma", "prazos_boletim",
            "chamadas_recentes", "agenda_eventos",
        },
        Perfil.ADMIN: secretaria_admin,
        Perfil.SECRETARIA: secretaria_admin,
        Perfil.COORDENADOR: pedagogica,
        Perfil.CANTINEIRO: {
            "pedidos_cantina_hoje", "cardapio_cantina",
            "estoque_cantina", "saldo_aluno_cantina", "agenda_eventos",
        },
    }
    for perfil, permissoes in esperado.items():
        assert set(intencoes_do_perfil(perfil)) == permissoes


def test_todo_perfil_tem_pelo_menos_uma_intencao():
    """Nenhum perfil pode ficar sem ability de consultar o assistente.

    Regressão que já aconteceu: coordenador e cantineiro ficaram com allowlist
    vazia e qualquer pergunta resultava em "não tenho acesso", embora o RBAC
    lhes desse escopo real.
    """
    for perfil in Perfil:
        assert intencoes_do_perfil(perfil), f"{perfil.value} sem nenhuma intenção"


def test_coordenacao_e_cantina_nao_veem_dado_de_aluno_do_responsavel():
    """Coordenação e cantina não têm escopo de 'meu filho' — é do responsável."""
    coordenadas = set(intencoes_do_perfil(Perfil.COORDENADOR))
    cantina = set(intencoes_do_perfil(Perfil.CANTINEIRO))
    proibidas_responsavel = {
        "notas_aluno_ultima", "boletim_aluno", "frequencia_aluno",
        "documentos_solicitacoes", "pulseira_aluno", "historico_escolar",
        "avisos_nao_lidos", "extrato_carteira", "notificacoes_nao_lidas",
    }
    assert not (coordenadas & proibidas_responsavel)
    assert not (cantina & proibidas_responsavel)
