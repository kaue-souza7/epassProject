"""Roteador determinístico de intenções — o CATÁLOGO COMPLETO do ePass.

POR QUE NÃO USAR O LLM PARA ISSO
--------------------------------
Se o modelo decidisse a intenção, ele também poderia induzir a escolha de uma
consulta fora do escopo do usuário. A classificação é feita aqui, em código,
a partir de um dicionário de termos. O LLM recebe apenas fatos já autorizados.

ESCOPO DESTE ARQUIVO
--------------------
A Atena é "100% especializada no ePass": o catálogo abaixo cobre TODAS as áreas
do sistema que um usuário pode consultar, para CADA perfil. Não existe uma
pergunta "do sistema" que caia em "não entendi" por falta de um termo — quando
a pergunta é sobre algo que existe no ePass, existe uma intenção.

O que NÃO é possível declarar aqui: intenções que escrevem dados (lançar nota,
fazer chamada, aprovar pedido). O assistente é somente leitura por definição —
regra 9 do prompt. Pergunta de escrita cai na recusa genérica, que aponta o
caminho certo ("isso deve ser feito no ePass").

ORDEM DE DECISÃO (fixa e auditável)
-----------------------------------
  1. Normalizar o texto (minúsculas, sem acento, espaços colapsados).
  2. Filtrar as intenções pela ALLOWLIST DO PERFIL — o perfil decide o que
     existe, antes de qualquer classificação.
  3. Casa a pergunta contra os sinônimos da candidata. Cada match exige TODOS
     os grupos de sinônimos (`requisitos`), o que evita falsos positivos.
  4. Desambiguar por prioridade e sinais negativos.
  5. Sem match → IntencaoNaoReconhecidaErro, com sugestões do perfil.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.modules.ai import mensagens as textos
from app.modules.ai.exceptions import (
    IntencaoNaoPermitidaErro,
    IntencaoNaoReconhecidaErro,
)
from app.shared.enums import Perfil

# Palavras que aparecem capitalizadas no início de frases e não são nomes.
_PALAVRAS_COMUNS = frozenset({
    "eu", "meu", "minha", "meus", "minhas", "o", "a", "os", "as", "um", "uma",
    "qual", "quais", "quantos", "quantas", "quem", "quando", "onde", "tem",
    "tenho", "ha", "esta", "estao", "e", "em", "do", "da", "de", "para", "com",
    "boletim", "prova", "tarefa", "trabalho", "nota", "notas", "ocorrencia",
    "ocorrencias", "aviso", "avisos", "comunicado", "turma", "turmas", "aluno",
    "alunos", "filho", "filhos", "filha", "carteira", "saldo", "media",
    "ontem", "hoje", "agora", "ultima", "ultimo", "serie", "series", "faltas",
    "falta", "frequencia", "cardapio", "lanche", "pedido", "pedidos", "estoque",
    "matricula", "matriculas", "pulseira", "documento", "documentos", "evento",
    "eventos", "agenda", "media", "sistema", "atena", "obrigado", "ola",
})


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, espaços colapsados. Base de todas as comparações."""
    sem_acento = unicodedata.normalize("NFD", texto)
    limpo = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return " ".join(limpo.lower().split())


@dataclass(frozen=True)
class Intencao:
    """Uma pergunta suportada, seus sinônimos e a quem ela é permitida."""

    nome: str
    perfis: frozenset[Perfil]
    # Grupos de sinônimos. TODOS precisam aparecer no texto normalizado.
    requisitos: tuple[tuple[str, ...], ...]
    descricao: str
    # Sinônimos que, sozinhos, indicam OUTRA intenção (desambiguação).
    sinais_negativos: tuple[str, ...] = ()
    prioridade: int = 0
    exige_aluno: bool = False
    exige_turma: bool = False


TODOS = frozenset(Perfil)
RESPONSAVEL = frozenset({Perfil.RESPONSAVEL})
PROFESSOR = frozenset({Perfil.PROFESSOR})
ADMIN_E_SECRETARIA = frozenset({Perfil.ADMIN, Perfil.SECRETARIA})
COORDENACAO = frozenset({Perfil.ADMIN, Perfil.SECRETARIA, Perfil.COORDENADOR})
CANTINA_E_ADMIM = frozenset({Perfil.ADMIN, Perfil.SECRETARIA, Perfil.CANTINEIRO})

# Perfis com visão institucional da escola inteira. É uma propriedade do
# PERFIL (o RBAC lhes dá leitura em escopo "all"), e não do catálogo: um sinal
# derivado das intenções permitiria que `agenda_eventos`, aberta a todos,
# desse a um responsável uma falsa visão institucional.
PERFIS_INSTITUCIONAIS = frozenset({Perfil.ADMIN, Perfil.SECRETARIA, Perfil.COORDENADOR})

# Sinônimos de "escola toda" — o pedido de escopo amplo explícito.
_SINAIS_GLOBAL = (
    "escola inteira", "toda a escola", "todos os alunos", "todas as turmas",
    "global", "no geral", "em toda a escola",
)

# Marcas de escopo PESSOAL. A presença de uma delas na pergunta significa
# "meu escopo", mesmo que a frase também contenha um termo institucional
# ("quantas ocorrências tem MEU filho"). Sem esta checagem, "Quantas
# ocorrências tem meu filho?" seria lido como pergunta de escola inteira.
_SINAIS_ESCOPO_PESSOAL = (
    "meu filho", "minha filha", "meus filhos", "minhas filhas",
    "meu aluno", "minha aluna", "meus alunos", "minhas alunos",
    "minha turma", "minhas turmas", "meu professor", "minha professora",
    "meu", "minha", "dele", "dela", "deles", "delas",
)

# Agregados institucionais INAMBÍGUOS. Só entram aqui as formas que só fazem
# sentido para a escola inteira — "quantos alunos" não é pergunta sobre um
# filho. Formas ambíguas ("matriculados", "quantas ocorrências") NÃO entram:
# elas aparecem legitimamente em pergunta de escopo pessoal.
_SINAIS_ADMIN = (
    "quantos alunos", "quantas turmas", "total de alunos",
    "quantos responsaveis", "quantos avisos", "quantas matriculas",
    "quantos series", "quantas series", "quantos series",
)

# ---------------------------------------------------------------------------
# CATÁLOGO
# ---------------------------------------------------------------------------

INTENCOES: tuple[Intencao, ...] = (
    # ===================== RESPONSÁVEL =====================
    Intencao(
        nome="notas_aluno_ultima",
        perfis=RESPONSAVEL,
        requisitos=(
            ("nota", "notas", "boletim", "desempenho", "desempenho academico",
             "resultado", "rendimento", "prova"),
            ("ultima", "ultimo", "mais recente", "atual", "agora", "proxima",
             "disponivel", "saiu"),
        ),
        descricao="Última nota registrada de um aluno do responsável",
        prioridade=10,
        exige_aluno=True,
    ),
    Intencao(
        nome="media_aluno",
        perfis=RESPONSAVEL,
        requisitos=(
            ("media", "desempenho", "desempenho academico",
             "rendimento", "como esta", "como vai", "situacao", "andamento"),
        ),
        descricao="Média geral e situação estimada de um aluno do responsável",
        # Veto ao plural de turma/aluno: "quais alunos da minha turma" é
        # vocabulário de professor e coordenação. Sem o veto, a palavra "média"
        # faria o responsável receber a média do filho em vez da lista que
        # pediu.
        sinais_negativos=(
            "quais alunos", "meus alunos", "minha turma", "minhas turmas",
            "alunos da minha", "da minha turma",
        ),
        prioridade=20,
        exige_aluno=True,
    ),
    Intencao(
        nome="notas_aluno_historico",
        perfis=RESPONSAVEL,
        requisitos=(
            ("nota", "notas", "boletim", "avaliacoes", "provas", "trabalhos"),
            ("todas", "historico", "lista", "quais", "completo", "completa",
             "ano", "bimestre", "disciplina"),
        ),
        descricao="Histórico de notas por disciplina de um aluno do responsável",
        prioridade=15,
        exige_aluno=True,
    ),
    Intencao(
        nome="boletim_aluno",
        perfis=RESPONSAVEL,
        requisitos=(("boletim",),),
        descricao="Situação do boletim bimestral liberado de um aluno",
        prioridade=25,
        exige_aluno=True,
    ),
    Intencao(
        nome="frequencia_aluno",
        perfis=RESPONSAVEL,
        requisitos=(
            ("frequencia", "faltas", "falta", "assiduidade", "presencas", "presenca"),
        ),
        descricao="Frequência e faltas de um aluno do responsável",
        prioridade=20,
        exige_aluno=True,
    ),
    Intencao(
        nome="ocorrencias_aluno",
        perfis=RESPONSAVEL,
        requisitos=(("ocorrencia", "ocorrencias", "problema", "problemas"),),
        descricao="Ocorrências registradas de um aluno do responsável",
        prioridade=5,
        exige_aluno=True,
    ),
    Intencao(
        nome="avisos_nao_lidos",
        perfis=RESPONSAVEL,
        requisitos=(
            ("aviso", "avisos", "comunicado", "comunicados", "recados"),
            (
                "nao li", "nao lidos", "faltando", "pendente", "ainda nao",
                "recebi", "recebidos", "lidas", "novos", "recente",
            ),
        ),
        descricao="Avisos ainda não lidos pelo responsável",
        prioridade=10,
    ),
    Intencao(
        nome="respostas_aviso",
        perfis=RESPONSAVEL,
        requisitos=(
            ("aviso", "avisos", "comunicado", "comunicados", "resposta", "respostas"),
            ("respondeu", "responde", "respostas", "minha resposta", "retorno",
             "replicou", "mandaram resposta"),
        ),
        descricao="Respostas da secretaria a um aviso do responsável",
        prioridade=15,
    ),
    Intencao(
        nome="notificacoes_nao_lidas",
        perfis=RESPONSAVEL,
        requisitos=(
            ("notificacao", "notificacoes", "notificacao"),
            ("nao lidas", "nao li", "novas", "pendentes", "alertas", "quantas"),
        ),
        descricao="Notificações não lidas do responsável",
        prioridade=10,
    ),
    Intencao(
        nome="saldo_carteira",
        perfis=RESPONSAVEL,
        requisitos=(
            ("carteira", "saldo", "recarrega", "recarregar", "consumo", "gasto"),
        ),
        descricao="Saldo da carteira do aluno do responsável",
        prioridade=10,
        exige_aluno=True,
    ),
    Intencao(
        nome="extrato_carteira",
        perfis=RESPONSAVEL,
        requisitos=(
            ("extrato", "movimentacoes", "gastos", "consumos", "recarregas",
             "depositos", "saidas", "entradas"),
            ("carteira", "conta", "gasto", "consumo", "recarrega", "extrato"),
        ),
        descricao="Extrato de movimentações da carteira do aluno",
        prioridade=20,
        exige_aluno=True,
    ),
    Intencao(
        nome="pedidos_cantina",
        perfis=RESPONSAVEL,
        requisitos=(
            ("pedido", "pedidos", "lanche", "lanches", "refeicao", "refeicoes",
             "compras", "compra", "retirada"),
            ("pedido", "pedidos", "lanche", "lanches", "refeicao", "retirada",
             "status", "situacao", "hoje", "feito", "reservado"),
        ),
        descricao="Pedidos de lanche do aluno na cantina",
        prioridade=20,
        exige_aluno=True,
    ),
    Intencao(
        nome="programacao_cantina",
        perfis=RESPONSAVEL,
        requisitos=(
            ("programacao", "programada", "agendado", "agendada", "semanal",
             "semana", "cardapio", "menu"),
        ),
        descricao="Programação semanal de lanches do aluno",
        prioridade=20,
        exige_aluno=True,
    ),
    Intencao(
        nome="documentos_solicitacoes",
        perfis=RESPONSAVEL,
        requisitos=(
            ("documento", "documentos", "solicitacao", "solicitacoes",
             "declaracao", "comprovante", "atestado"),
            ("status", "situacao", "andamento", "pedido", "pedi", "solicitei",
             "situacao", "resposta", "pendente", "concluido"),
        ),
        descricao="Situação das solicitações de documento do responsável",
        prioridade=20,
        exige_aluno=True,
    ),
    Intencao(
        nome="agenda_eventos",
        perfis=TODOS,
        requisitos=(
            ("agenda", "evento", "eventos", "compromisso", "compromissos",
             "reuniao", "reunioes", "encontro"),
            (
                "proximo", "proximos", "proxima", "hoje", "amanha", "semana",
                "quando", "calendario", "o que tem", "tenho", "quais",
                "marcados", "marcado", "tem", "esta", "sao",
            ),
        ),
        descricao="Próximos eventos da agenda do usuário",
        prioridade=10,
    ),
    Intencao(
        nome="pulseira_aluno",
        perfis=RESPONSAVEL,
        requisitos=(
            ("pulseira", "pulseiras", "bracelet", "bracelete", "rfid", "entrada", "saida"),
        ),
        descricao="Situação da pulseira de identificação do aluno",
        prioridade=15,
        exige_aluno=True,
    ),
    Intencao(
        nome="matricula_aluno",
        perfis=RESPONSAVEL,
        requisitos=(
            ("matricula", "matriculado", "matriculada", "turma", "serie", "ano letivo"),
            ("matricula", "matriculado", "qual turma", "em que turma",
             "em qual serie", "situacao", "status"),
        ),
        descricao="Situação da matrícula e turma de um aluno do responsável",
        prioridade=15,
        exige_aluno=True,
    ),
    Intencao(
        nome="historico_escolar",
        perfis=RESPONSAVEL,
        requisitos=(
            ("historico", "historico escolar", "transferencia", "antecedentes"),
        ),
        descricao="Histórico escolar do aluno do responsável",
        prioridade=20,
        exige_aluno=True,
    ),

    # ===================== PROFESSOR =====================
    Intencao(
        nome="alunos_abaixo_media",
        perfis=PROFESSOR,
        requisitos=(
            ("aluno", "alunos", "turma", "turmas", "minha turma", "minhas turmas",
             "disciplina"),
            (
                "abaixo", "abaixo da media", "abaixo da media de corte", "reprovando",
                "reprovacao", "insuficiente", "deficit", "abaixo do esperado",
                "dificuldade", "dificeis", "risco",
            ),
        ),
        descricao="Alunos das turmas do professor com nota abaixo da média",
        # Acima de `media_disciplina_turma` de propósito: "quais alunos estão
        # abaixo da média" contém "média" e casa com as duas. A pergunta por
        # RISCO ("abaixo", "reprovando") tem de ganhar da pergunta por
        # DESCRIÇÃO ("qual a média"), senão o professor recebe a tabela de
        # médias quando pediu a lista de quem está reprovando.
        prioridade=30,
    ),
    Intencao(
        nome="ocorrencias_pendentes",
        perfis=PROFESSOR,
        requisitos=(
            ("ocorrencia", "ocorrencias"),
            (
                "pendente", "pendentes", "em aberto", "aberto", "nao resolvida",
                "nao resolvido", "concluida", "concluido", "ainda tem",
                "alguma ocorrencia", "quantas",
            ),
        ),
        descricao="Ocorrências em aberto das turmas do professor",
        prioridade=10,
    ),
    Intencao(
        nome="minhas_turmas",
        perfis=PROFESSOR,
        requisitos=(
            ("minhas turmas", "minha turma", "turmas", "turma", "minhas disciplinas",
             "minha disciplina", "disciplinas", "alocacoes", "aulas", "horarios"),
            ("minhas", "minha", "quais", "quais turmas", "lista", "tenho",
             "leciono", "quais disciplinas"),
        ),
        descricao="Turmas e disciplinas sob responsabilidade do professor",
        prioridade=10,
    ),
    Intencao(
        nome="avaliacoes_sem_notas",
        perfis=PROFESSOR,
        requisitos=(
            ("avaliacao", "avaliacoes", "nota", "notas", "prova", "provas",
             "trabalho", "trabalhos", "atividade"),
            ("sem nota", "nao lancei", "nao lancé", "faltam", "pendente",
             "pendentes", "nao launched", "ainda nao", "a lancar", "lancar"),
        ),
        descricao="Avaliações do professor com notas ainda não lançadas",
        prioridade=20,
    ),
    Intencao(
        nome="media_disciplina_turma",
        perfis=PROFESSOR,
        requisitos=(
            ("media", "m medias", "desempenho", "rendimento"),
            ("turma", "turmas", "minha disciplina", "disciplina", "minhas turmas",
             "alunos", "aluno", "classe", "ano", "bimestre"),
        ),
        descricao="Média da turma por disciplina sob responsabilidade do professor",
        prioridade=15,
    ),
    Intencao(
        nome="frequencia_turma",
        perfis=PROFESSOR,
        requisitos=(
            ("frequencia", "faltas", "falta", "assiduidade", "presencas"),
            ("turma", "turmas", "minha turma", "minhas turmas", "alunos", "aluno",
             "aula", "aulas", "chamada", "chamadas"),
        ),
        descricao="Frequência dos alunos das turmas do professor",
        prioridade=15,
    ),
    Intencao(
        nome="lista_alunos_turma",
        perfis=PROFESSOR,
        requisitos=(
            ("aluno", "alunos", "estudantes", "lista", "roster", "quem"),
            ("turma", "minha turma", "minhas turmas", "classe", "matriculados",
             "presentes", "participam"),
        ),
        descricao="Lista de alunos matriculados nas turmas do professor",
        prioridade=15,
    ),
    Intencao(
        nome="avisos_turma",
        perfis=PROFESSOR,
        requisitos=(
            ("aviso", "avisos", "comunicado", "comunicados", "recados"),
            ("minha turma", "minhas turmas", "turma", "turmas", "alunos"),
        ),
        descricao="Avisos publicados para as turmas do professor",
        prioridade=15,
    ),
    Intencao(
        nome="prazos_boletim",
        perfis=PROFESSOR,
        requisitos=(
            ("boletim", "prazos", "prazo", "liberacao", "liberar"),
            ("prazo", "prazos", "limite", "quando", "data", "liberar",
             "liberacao", "pendencia"),
        ),
        descricao="Prazos e liberações de boletim do professor",
        prioridade=15,
    ),
    Intencao(
        nome="chamadas_recentes",
        perfis=PROFESSOR,
        requisitos=(
            ("chamada", "chamadas", "presenca", "presencas", "aula", "aulas"),
            ("ultima", "ultimo", "recentes", "recente", "quantas", "quais",
             "fiz", "realizadas", "hoje"),
        ),
        descricao="Chamadas de presença realizadas pelo professor",
        prioridade=15,
    ),

    # ===================== SECRETARIA / ADMIN =====================
    Intencao(
        nome="matriculas_contagem",
        perfis=COORDENACAO,
        requisitos=(
            (
                "quantos alunos", "quantas matriculas", "numero de alunos",
                "numero de matriculas", "quantos estao matriculados",
                "quantos matriculados", "total de alunos",
                "quantos alunos estao matriculados",
            ),
        ),
        descricao="Quantidade de alunos matriculados (visão administrativa)",
        prioridade=10,
    ),
    Intencao(
        nome="alunos_sem_matricula",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("aluno", "alunos"),
            ("sem matricula", "sem matricula ativa", "desmatriculado",
             "nao matriculado", "sem matricula ativa", "sem matriculas"),
        ),
        descricao="Alunos ativos sem matrícula ativa",
        prioridade=20,
    ),
    Intencao(
        nome="turmas_ocupacao",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("turma", "turmas", "vagas", "lotacao", "ocupacao"),
            ("vaga", "vagas", "lotadas", "lotacao", "ocupacao", "cheia",
             "cheias", "cabem", "cabendo", "matriculas", "quantos alunos"),
        ),
        descricao="Ocupação e vagas das turmas",
        prioridade=15,
    ),
    Intencao(
        nome="alunos_por_serie",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("serie", "series"),
            ("quantos", "quantas", "alunos", "turmas", "total", "numero",
             "distribuicao", "por serie"),
        ),
        descricao="Distribuição de alunos e turmas por série",
        prioridade=15,
    ),
    Intencao(
        nome="documentos_pendentes",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("documento", "documentos", "solicitacao", "solicitacoes",
             "declaracao", "comprovante", "atestado"),
            ("pendente", "pendentes", "fila", "aguardando", "quantas",
             "quantos", "nao atendidas", "para atender"),
        ),
        descricao="Solicitações de documentos pendentes de atendimento",
        prioridade=20,
    ),
    Intencao(
        nome="ocorrencias_abertas",
        perfis=COORDENACAO,
        requisitos=(
            ("ocorrencia", "ocorrencias"),
            ("quantas", "quantos", "abertas", "em aberto", "pendentes",
             "geral", "escola", "situacao", "resumo"),
        ),
        descricao="Ocorrências abertas na instituição",
        prioridade=15,
    ),
    Intencao(
        nome="avisos_nao_lidos_por_responsavel",
        perfis=COORDENACAO,
        requisitos=(
            ("aviso", "avisos", "comunicado", "comunicados"),
            ("responsavel", "responsaveis", "pais", "parent", "todos"),
            (
                "nao visualizaram", "nao viram", "nao leram", "nao visualizado",
                "sem ler", "nao abriram", "nao visualizaram ainda",
            ),
        ),
        descricao="Responsáveis que ainda não visualizaram um aviso",
        prioridade=10,
    ),
    Intencao(
        nome="pedidos_cantina_pendentes",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("pedido", "pedidos", "lanche", "lanches", "refeicao"),
            ("pendente", "pendentes", "fila", "aguardando", "quantos",
             "quantas", "para produzir", "producao", "aprovados", "de hoje"),
        ),
        descricao="Pedidos de lanche pendentes na cantina",
        # Acima de `pedidos_cantina_hoje`: para secretaria/admin a pergunta é
        # sobre a fila inteira (qualquer data). O cantineiro não tem esta
        # intenção na allowlist e continua recebendo a fila de hoje, que é a
        # visão dele de balcão.
        prioridade=25,
    ),
    Intencao(
        nome="estoque_baixo",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("estoque", "produto", "produtos", "item", "itens", "insumo"),
            ("baixo", "acabando", "acabou", "esgotado", "esgotados", "zerado",
             "zerados", "falta", "faltando", "repor", "reposicao", "critico"),
        ),
        descricao="Produtos da cantina com estoque baixo ou zerado",
        # Acima de `estoque_cantina` (visão completa do balcão): para
        # secretaria/admin, "estoque baixo" é pedido de ALERTA de reposição.
        # O cantineiro não tem esta intenção na allowlist, então continua
        # recebendo a listagem completa — que é o que ele precisa no balcão.
        prioridade=25,
    ),
    Intencao(
        nome="matriculas_recentes",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("matricula", "matriculas", "aluno", "alunos", "novo", "novos"),
            ("recentes", "recente", "ultimas", "ultimos", "novos", "novas",
             "entradas", "entraram", "acabei de matricular", "hoje"),
        ),
        descricao="Matrículas mais recentes",
        prioridade=15,
    ),
    Intencao(
        nome="professores_alocacoes",
        perfis=ADMIN_E_SECRETARIA,
        requisitos=(
            ("professor", "professores", "disciplina", "disciplinas", "alocacao",
             "alocacoes", "docente", "docentes"),
            ("quantos", "quantas", "quais", "lista", "turmas", "sem disciplina",
             "sem alocacao", "cobertura", "coberto"),
        ),
        descricao="Corpo docente e alocações de disciplina",
        prioridade=15,
    ),

    # ===================== COORDENAÇÃO =====================
    Intencao(
        nome="panorama_escolar",
        perfis=COORDENACAO,
        requisitos=(
            ("panorama", "resumo", "visao geral", "como esta a escola",
             "como estao as coisas", "situacao geral", "numero de alunos",
             "quantas turmas", "quantas series"),
        ),
        descricao="Panorama geral da escola (contagens agregadas)",
        prioridade=15,
    ),
    Intencao(
        nome="turmas_criticas",
        perfis=COORDENACAO,
        requisitos=(
            ("turma", "turmas", "serie", "series"),
            ("critica", "criticas", "dificuldade", "risco", "abaixo da media",
             "abaixo da media de corte", "alunos abaixo", "em risco", "preocupante"),
        ),
        descricao="Turmas com mais alunos abaixo da média de corte",
        # "minha turma" é vocabulário de professor. Secretaria e coordenação
        # têm visão de todas as turmas, então responder a uma pergunta de
        # escopo pessoal com o recorte da escola inteira daria um número que
        # não corresponde ao que foi perguntado.
        sinais_negativos=("minha turma", "minhas turmas", "meus alunos"),
        prioridade=20,
    ),
    Intencao(
        nome="alunos_atencao_coordenacao",
        perfis=COORDENACAO,
        requisitos=(
            ("aluno", "alunos", "estudante", "estudantes"),
            ("atencao", "atencao especial", "precisam de atencao", "intervencao",
             "caso", "casos", "alerta", "alertas", "preocupantes", "reprovando"),
        ),
        descricao="Alunos que combinam nota e frequência abaixo do mínimo",
        prioridade=20,
    ),

    # ===================== CANTINEIRO =====================
    Intencao(
        nome="pedidos_cantina_hoje",
        perfis=CANTINA_E_ADMIM,
        requisitos=(
            ("pedido", "pedidos", "lanche", "lanches", "encomenda", "encomendas",
             "retirada", "retirar"),
            ("hoje", "de hoje", "pendentes", "fila", "aguardando", "produzir",
             "producao", "prontos", "para hoje", "quantos", "quantas"),
        ),
        descricao="Pedidos de lanche de hoje (produção da cantina)",
        prioridade=20,
    ),
    Intencao(
        nome="cardapio_cantina",
        perfis=CANTINA_E_ADMIM,
        requisitos=(
            ("cardapio", "menu", "produtos", "disponiveis", "oferetas",
             "vendem", "venda", "itens"),
            ("cardapio", "menu", "disponivel", "disponiveis", "tem", "quais",
             "o que", "vendem", "hoje"),
        ),
        descricao="Cardápio e produtos disponíveis na cantina",
        prioridade=15,
    ),
    Intencao(
        nome="estoque_cantina",
        perfis=CANTINA_E_ADMIM,
        requisitos=(
            ("estoque", "produto", "produtos", "item", "itens", "insumo",
             "quantidade", "quanto tem"),
            ("estoque", "quanto tem", "quantos", "quantas", "saldo", "disponivel",
             "acabou", "baixo"),
        ),
        descricao="Estoque de produtos da cantina",
        prioridade=20,
    ),
    Intencao(
        nome="saldo_aluno_cantina",
        perfis=CANTINA_E_ADMIM,
        requisitos=(
            ("saldo", "carteira", "quanto tem", "quanto ha", "tem saldo",
             "tem na carteira"),
        ),
        descricao="Saldo na carteira de um aluno (para compra no balcão)",
        prioridade=20,
    ),
)

INTENCOES_POR_NOME: dict[str, Intencao] = {i.nome: i for i in INTENCOES}

# Intenções cujo contexto NÃO é por aluno. Sem esta lista, o extrator de nome
# injetaria um nome de aluno em perguntas institucionais ("quantos alunos estão
# matriculados?") e o builder receberia um escopo que não existe.
_INTENCOES_SEM_ALUNO = frozenset({
    "avisos_nao_lidos",
    "notificacoes_nao_lidas",
    "agenda_eventos",
    "matriculas_contagem",
    "alunos_sem_matricula",
    "turmas_ocupacao",
    "alunos_por_serie",
    "documentos_pendentes",
    "ocorrencias_abertas",
    "avisos_nao_lidos_por_responsavel",
    "pedidos_cantina_pendentes",
    "estoque_baixo",
    "matriculas_recentes",
    "professores_alocacoes",
    "panorama_escolar",
    "turmas_criticas",
    "pedidos_cantina_hoje",
    "cardapio_cantina",
    "estoque_cantina",
})

# Intenções em que o trecho citado por aspas/"da/sobre" é um AVISO, não um
# aluno. Nomes de alunos continuam sendo resolvidos contra o escopo.
_INTENCOES_COM_AVISO = frozenset({
    "avisos_nao_lidos_por_responsavel",
    "respostas_aviso",
})


# ---------------------------------------------------------------------------
# RESULTADO E EXTRAÇÕES
# ---------------------------------------------------------------------------


@dataclass
class ResultadoIntencao:
    """Intenção classificada + o trecho da pergunta que o usuário digitar."""

    intencao: Intencao
    mensagem_original: str
    mensagem_normalizada: str
    # Entidades detectadas na linguagem natural (nunca IDs do banco).
    nome_aluno: str | None = None
    nome_turma: str | None = None
    # Trecho que identifica UM aviso citado ("o aviso da reunião de pais").
    nome_aviso: str | None = None
    # Disciplina citada por nome ("nota de matemática").
    nome_disciplina: str | None = None
    # Bimestre citado em numeral ou por extenso ("2º bimestre").
    bimestre: int | None = None
    # Fragmento da pergunta que descreve a "parte" (ex.: 'última nota de Matemática').
    consulta: str = field(default="", repr=False)


def _extrair_nome_candidato(mensagem: str) -> str | None:
    """Extrai um possível nome de aluno da pergunta em linguagem natural.

    Heurística CONSERVADORA: duas ou mais palavras capitalizadas consecutivas
    viram candidata a nome. Devolve `None` quando nada parece um nome — nesse
    caso os builders usam o aluno selecionado (mobile/web) ou o único filho do
    responsável.

    Importante: este texto é apenas uma *string*. Nenhum identificador de banco
    é derivado aqui. A candidata é resolvida contra a lista de filhos
    AUTORIZADOS dentro do escopo; se não resolver, a resposta é recusa — nunca
    uma busca global por nome.
    """
    limpo = re.sub(r"[^0-9A-Za-zÀ-ÿ\s]", " ", mensagem)
    palavras = [p for p in limpo.split() if p]

    candidatos: list[str] = []
    atual: list[str] = []
    for palavra in palavras:
        if palavra[0].isupper() and palavra.lower() not in _PALAVRAS_COMUNS and len(palavra) > 1:
            atual.append(palavra)
        else:
            if len(atual) >= 2:
                candidatos.append(" ".join(atual))
            atual = []
    if len(atual) >= 2:
        candidatos.append(" ".join(atual))

    return max(candidatos, key=len) if candidatos else None


# Marcadores que iniciam a referência a um aviso específico.
_MARCADORES_AVISO = (
    "aviso", "avisos", "comunicado", "comunicados", "memorando", "circular",
)


def _extrair_referencia_aviso(mensagem: str) -> str | None:
    """Extrai o trecho que nomeia UM aviso ("o aviso da reunião de pais").

    Aceita as formas usuais de referência:
      - "aviso da reunião de pais" / "aviso sobre a reunião"
      - "aviso: Reunião de Pais"
      - aspas: o aviso "Reunião de Pais"

    Devolve `None` quando nenhum aviso é citado — nesse caso o builder usa o
    escopo institucional completo (todos os avisos publicados).
    """
    texto = mensagem.strip()

    # Forma com aspas: o trecho literal é a referência mais precisa.
    for aspas in ('"', "'", "“", "«"):
        if aspas in texto:
            inicio = texto.index(aspas) + 1
            fim = texto.find(aspas, inicio)
            if fim > inicio:
                return texto[inicio:fim].strip() or None

    # Forma "aviso da/about/sobre <resto>".
    for marcador in _MARCADORES_AVISO:
        padrao = re.compile(
            rf"\b{marcador}\s+(?:d[aoes]|sobre|do|da|referente\s+a|chamad[oa])\s+(.+)",
            re.IGNORECASE,
        )
        achado = padrao.search(texto)
        if achado:
            trecho = achado.group(1).strip(" ?.!,;:")
            # Ignora a cauda da pergunta ("... visualizarem o aviso?").
            trecho = re.split(r"[?!.]", trecho)[0].strip()
            if trecho:
                return trecho

    # Forma "aviso: <resto>".
    achado = re.match(r"^\s*(?:o\s+|qual\s+)?aviso\s*:\s*(.+)", texto, re.IGNORECASE)
    if achado:
        trecho = re.split(r"[?!.]", achado.group(1))[0].strip()
        if trecho:
            return trecho

    return None


# Disciplinas cujo nome aparece capitalizado na pergunta ("de Matemática").
_MARCADORES_DISCIPLINA = ("disciplina", "materia", "prova de", "nota de", "notas de")


def _extrair_disciplina(mensagem: str) -> str | None:
    """Nome de disciplina citado na linguagem natural.

    Só devolve algo quando o trecho está explicitamente marcado como disciplina
    ("a nota de Matemática"), nunca por posição genérica — senão qualquer nome
    capitalizado vira disciplina e o filtro errado abaixa o contexto.
    """
    for marcador in _MARCADORES_DISCIPLINA:
        achado = re.search(rf"\b{marcador}\s+([A-ZÀ-Ý][\wÀ-ÿ]*)", mensagem)
        if achado:
            return achado.group(1)
    return None


_BIMESTRE_EXTENSO = {
    "primeiro": 1, "1o": 1, "segundo": 2, "2o": 2,
    "terceiro": 3, "3o": 3, "quarto": 4, "4o": 4,
}


def _extrair_bimestre(mensagem_normalizada: str) -> int | None:
    """Bimestre citado ('2º bimestre', 'segundo bimestre', 'bimestre 3')."""
    achado = re.search(r"(\d)\s*(?:o|º|°)?\s*bimestre", mensagem_normalizada)
    if achado:
        valor = int(achado.group(1))
        if 1 <= valor <= 4:
            return valor
    achado = re.search(r"bimestre\s*(\d)", mensagem_normalizada)
    if achado:
        valor = int(achado.group(1))
        if 1 <= valor <= 4:
            return valor
    achado = re.search(r"\b(primeiro|segundo|terceiro|quarto)\s+bimestre", mensagem_normalizada)
    if achado:
        return _BIMESTRE_EXTENSO[achado.group(1)]
    return None


def _casar(texto: str, intencao: Intencao) -> bool:
    """Todos os grupos de sinônimos precisam aparecer E nenhum veto pode bater.

    Os `sinais_negativos` são o espelho dos `requisitos`: servem para BLINDAR
    uma intenção contra a própria família de sinônimos. Sem eles, "quais alunos
    da MINHA TURMA estão abaixo da média" casaria com `media_aluno` (porque
    contém "média") e um responsável receberia a média do filho dele ao invés da
    lista que pediu — sem qualquer erro visível.
    """
    if any(negativo in texto for negativo in intencao.sinais_negativos):
        return False
    for grupo in intencao.requisitos:
        if not any(sin in texto for sin in grupo):
            return False
    return True


def classificar(mensagem: str, perfil: Perfil) -> ResultadoIntencao:
    """Classifica a pergunta do usuário dentro do que o perfil pode perguntar.

    Levanta:
      - IntencaoNaoReconhecidaErro: nada casou (200, com sugestões).
      - IntencaoNaoPermitidaErro:     a pergunta é claramente de uma área que o
                                      perfil não pode consultar (403).
    """
    texto = normalizar(mensagem)
    if not texto:
        raise IntencaoNaoReconhecidaErro(textos.intencao_nao_reconhecida_para(perfil))

    escopo_pessoal = any(m in texto for m in _SINAIS_ESCOPO_PESSOAL)
    sinal_global = any(m in texto for m in _SINAIS_GLOBAL)
    sinal_admin = any(m in texto for m in _SINAIS_ADMIN)

    # Allowlist do perfil: só existe o que este perfil pode perguntar.
    permitidas = [i for i in INTENCOES if perfil in i.perfis]

    # "Este perfil enxerga a escola inteira?" — definido pelo PERFIL, e não
    # derivado do catálogo: `agenda_eventos` é aberta a todos os perfis, e
    # usá-la como sinal daria a um responsável uma falsa visão institucional.
    tem_visao_institucional = perfil in PERFIS_INSTITUCIONAIS

    # PEDIDO DE ESCOPO AMPLO POR PERFIL RESTRITO — verificado ANTES do
    # casamento, não depois.
    #
    # Precisa vir antes porque uma pergunta de escola inteira quase sempre casa
    # com alguma intenção de escopo pessoal: "quantos alunos estão
    # matriculados?" contém "matriculado", que é requisito de `matricula_aluno`
    # — e o builder resolveria o filho do responsável, respondendo a uma
    # pergunta que ele não fez. A checagem depois do casamento nunca dispararia.
    if not tem_visao_institucional and not escopo_pessoal and (sinal_global or sinal_admin):
        raise IntencaoNaoPermitidaErro(textos.intencao_nao_permitida_para(perfil))

    candidatas = [i for i in permitidas if _casar(texto, i)]
    candidatas.sort(key=lambda i: (-i.prioridade, len(i.requisitos)))

    if candidatas:
        escolhida = candidatas[0]
        return ResultadoIntencao(
            intencao=escolhida,
            mensagem_original=mensagem,
            mensagem_normalizada=texto,
            nome_aluno=(
                None
                if escolhida.nome in _INTENCOES_SEM_ALUNO
                else _extrair_nome_candidato(mensagem)
            ),
            nome_turma=_extrair_nome_candidato(mensagem) if escolhida.exige_turma else None,
            nome_aviso=(
                _extrair_referencia_aviso(mensagem)
                if escolhida.nome in _INTENCOES_COM_AVISO
                else None
            ),
            nome_disciplina=_extrair_disciplina(mensagem),
            bimestre=_extrair_bimestre(texto),
            consulta=mensagem,
        )

    # Recusa final: base + escopo do perfil + UM exemplo concreto. Os três
    # juntos são o que faz "não entendi" virar uma próxima pergunta em vez de
    # beco sem saída — e o exemplo é sempre do perfil, nunca genérico.
    raise IntencaoNaoReconhecidaErro(
        textos.INTENCAO_NAO_RECONHECIDA
        + " "
        + textos.escopo_do_perfil(perfil)
        + " Por exemplo: "
        + _sugestoes(perfil)[0]
    )


def _sugestoes(perfil: Perfil) -> list[str]:
    """Sugestões de pergunta permitidas ao perfil (usadas nas respostas de fallback).

    Ordem aqui é a ordem de utilidade: a primeira é a que resolve a maior parte
    das dúvidas reais de cada perfil.
    """
    exemplos = {
        Perfil.RESPONSAVEL: [
            "Qual foi a última nota do meu filho?",
            "Meu filho tem alguma ocorrência?",
            "Quais avisos eu ainda não li?",
            "Quanto há na carteira do meu filho?",
            "Como está a média do meu filho?",
            "Quantas faltas o meu filho tem?",
            "Quais eventos tenho na agenda?",
            "Qual o status do pedido de lanche do meu filho?",
        ],
        Perfil.PROFESSOR: [
            "Quais alunos da minha turma estão abaixo da média?",
            "Tenho alguma ocorrência pendente?",
            "Quais são as minhas turmas?",
            "Quais avaliações ainda estão sem nota lançada?",
            "Como está a média da minha turma?",
            "Quais alunos estão matriculados nas minhas turmas?",
            "Quais avisos foram enviados para as minhas turmas?",
            "Quando são os prazos de liberação de boletim?",
        ],
        Perfil.ADMIN: [
            "Quantos alunos estão matriculados?",
            "Quais responsáveis não visualizaram o aviso?",
            "Quais alunos estão sem matrícula ativa?",
            "Quais documentos estão pendentes?",
            "Quais turmas estão lotadas?",
            "Quais produtos da cantina estão com estoque baixo?",
            "Quais professores ainda não têm alocação?",
            "Quais séries têm mais alunos?",
        ],
        Perfil.SECRETARIA: [
            "Quantos alunos estão matriculados?",
            "Quais responsáveis não visualizaram o aviso?",
            "Quais alunos estão sem matrícula ativa?",
            "Quais documentos estão pendentes?",
            "Quais turmas estão lotadas?",
            "Quais produtos da cantina estão com estoque baixo?",
            "Quais série têm mais alunos?",
            "Quais matrículas são mais recentes?",
        ],
        Perfil.COORDENADOR: [
            "Quais alunos estão reprovando?",
            "Quais séries estão críticas?",
            "Quais alunos precisam de atenção?",
            "Quantos alunos estão matriculados?",
            "Quais responsáveis não visualizaram o aviso?",
            "Quais ocorrências estão abertas?",
        ],
        Perfil.CANTINEIRO: [
            "Quais pedidos de hoje estão pendentes?",
            "O que há disponível no cardápio?",
            "Qual é o estoque dos produtos?",
            "Quanto há na carteira deste aluno?",
        ],
    }
    return exemplos.get(perfil, ["Consulte a secretaria."])


def sugestoes_para(perfil: Perfil) -> list[str]:
    """API pública para o frontend montar chips de sugestão."""
    return _sugestoes(perfil)
