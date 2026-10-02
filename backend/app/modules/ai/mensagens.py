"""Textos que o USUÁRIO vê, e a barreira que impede vazamento técnico.

POR QUE UM MÓDULO SÓ PARA ISSO
------------------------------
"Atena nunca fala de Ollama, modelo, tokens, timeout ou prompt" não se
sustenta com cuidado em cada `raise`: basta um caminho novo (uma exceção nova,
um `except` esquecido) para a regra quebrar em silêncio, e o usuário ler
"o modelo qwen3:4b ainda não está disponível" na tela do app da escola.

Então a regra passa a ter DUAS camadas:

  1. As mensagens canônicas moram aqui. Nenhum outro módulo escreve texto de
     erro para o usuário; os pontos de `raise` referenciam estas constantes.
  2. `sem_tecnologia()` roda no ÚLTIMO ponto antes da resposta sair do
     backend (router, chat e SSE). Se algum texto técnico escapar por um
     caminho não previsto, ele é substituído aqui em vez de chegar ao cliente.

A camada 2 é deliberadamente redundante. Redundância em fronteira pública é
barata; um vazamento de stack para um responsável não é.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Catálogo de mensagens
# ---------------------------------------------------------------------------

# Recusa por escopo/intenção não é falha: é uma resposta. Por isso são
# simpáticas, explicam o que a Atena SABE fazer e oferecem o próximo passo.
# A regra de ouro do texto: dizer o que ela não pode + oferecer o que pode,
# nunca enumerar a razão interna.

SEM_INFORMACOES = (
    "Ainda não tenho informações suficientes sobre isso. 😊 "
    "Me pergunta de outro jeito que eu te ajudo com o que está registrado no "
    "ePass."
)

SEM_DADOS = (
    "Não encontrei essa informação no ePass. 😕 "
    "Ela pode ainda não ter sido registrada — vale conferir se o nome está "
    "correto. Posso olhar outro assunto."
)

ESCOPO_NAO_RESOLVIDO = (
    "Não encontrei esse aluno entre os seus filhos. 😊 "
    "Se o nome estiver certo, o vínculo pode ainda não ter sido atualizado. "
    "Posso ajudar com outro assunto enquanto isso."
)

INTENCAO_NAO_PERMITIDA = (
    "Essa informação não está disponível para o seu perfil. 😊 "
    "Mas tem muita coisa do ePass que eu consigo te contar."
)

INTENCAO_NAO_RECONHECIDA = (
    "Não entendi bem essa pergunta. 😊 "
    "Tenta me perguntar de outro jeito — eu conheço bem o ePass."
)

# ---------------------------------------------------------------------------
# Escopo por perfil
# ---------------------------------------------------------------------------
# POR QUE ISTO EXISTE
# ------------------
# A recusa por escopo não pode ser um texto só: dizer a um professor "consigo
# te ajudar com o que é dos seus filhos" seria absurdo, e dizer a um responsável
# "consigo te ajudar com turmas e notas" seria um convite a tentar de novo.
#
# A regra é simples e está aqui: cada perfil recebe, no texto da recusa, uma
# lista do QUE PODE perguntar. Isso transforma a recusa de murosseco em
# convite, e o efeito colateral é que o usuário descobre o que a Atena sabe fazer
# só lendo a negativa.
_ESCOPO_POR_PERFIL: dict[str, str] = {
    "responsavel": (
        "Consigo te ajudar com o que é dos seus filhos: notas, média, boletim, "
        "faltas, ocorrências, avisos, Carteira, lanches, documentos e Agenda."
    ),
    "professor": (
        "Consigo te ajudar com as suas turmas e disciplinas: listas de alunos, "
        "médias, frequência, avaliações sem nota, ocorrências e prazos de boletim."
    ),
    "admin": (
        "Consigo te ajudar com a visão da escola: matrículas, turmas, séries, "
        "documentos, avisos, ocorrências, cantina e corpo docente."
    ),
    "secretaria": (
        "Consigo te ajudar com a visão da escola: matrículas, turmas, séries, "
        "documentos, avisos, ocorrências, cantina e corpo docente."
    ),
    "coordenador": (
        "Consigo te ajudar com o panorama pedagógico: turmas em risco, alunos "
        "que precisam de atenção, ocorrências abertas e números da escola."
    ),
    "cantineiro": (
        "Consigo te ajudar com o balcão: pedidos de hoje, cardápio, estoque e "
        "saldo na carteira do aluno."
    ),
}

_ESCOPO_PADRAO = (
    "Consigo te ajudar com o que está registrado no ePass."
)


def escopo_do_perfil(perfil) -> str:
    """Frase de "o que eu sei fazer" para o perfil — vai na recusa.

    É a única função deste módulo que recebe o perfil. Todo o resto do texto
    é genérico de propósito: um texto que muda por perfil em cinco lugares
    diferentes volta a divergir do catálogo em duas semanas.
    """
    chave = getattr(perfil, "value", perfil)
    return _ESCOPO_POR_PERFIL.get(str(chave), _ESCOPO_PADRAO)


def intencao_nao_permitida_para(perfil) -> str:
    """Recusa de escopo já com a oferta do que o perfil PODE perguntar."""
    return f"{INTENCAO_NAO_PERMITIDA} {escopo_do_perfil(perfil)}"


def intencao_nao_reconhecida_para(perfil) -> str:
    """Pergunta não entendida, com a oferta do escopo do perfil."""
    return f"{INTENCAO_NAO_RECONHECIDA} {escopo_do_perfil(perfil)}"

IA_INDISPONIVEL = (
    "Estou com uma dificuldade técnica agora e não consegui responder. 😕 "
    "Tenta de novo em alguns instantes — seus dados continuam seguros."
)

IA_DESABILITADA = (
    "O assistente está desativado neste momento. 😊 "
    "Se não era isso que você esperava, vale avisar a secretaria."
)

MODELO_NAO_DISPONIVEL = (
    "Meu assistente ainda está se preparando para te atender. 😊 "
    "Tenta novamente em alguns instantes."
)

IA_SOBRECARREGADA = (
    "Já estou respondendo a outra pergunta. 😊 "
    "Tenta de novo em alguns instantes."
)

RESPOSTA_VAZIA = (
    "Não consegui montar uma resposta agora. 😕 "
    "Tenta perguntar de novo?"
)

FALHA_INTERNA = (
    "Algo não saiu certo aqui do meu lado. 😕 "
    "Tenta novamente em alguns instantes."
)

# ---------------------------------------------------------------------------
# Barreira anti-vazamento
# ---------------------------------------------------------------------------

# Termos que jamais podem aparecer num texto entregue ao usuário. A lista é
# de VOCABULÁRIO TÉCNICO, não de frases: pega também o texto novo que alguém
# escrever no futuro ("HTTP 504", "qwen3:4b", "context window").
_TECNICOS = re.compile(
    r"\b("
    r"ollama|"
    r"qwen|llama|deepseek|mistral|phi|gemma|\d+\s*b\b|"
    r"llm|modelo|model|token|tokens|tokens_prompt|tokens_completion|"
    r"prompt|prompts|system\s?prompt|"
    r"contexto|context|contextual|"
    r"timeout|time-out|"
    r"inferencia|api|endpoint|backend|frontend|"
    r"http|https|sse|stream|streaming|"
    r"guardrail|guardrails|"
    r"sistema|interno|interna|infrastructure|"
    r"cpu|gpu|vram|ram|memoria do modelo|"
    r"docker|container|"
    r"exception|stack\s?trace|traceback|erro\s?\d{3}"
    r")\b",
    re.IGNORECASE,
)


def sem_tecnologia(texto: str, *, alternativa: str = IA_INDISPONIVEL) -> str:
    """Devolve `texto` limpo, ou `alternativa` se houver jargão técnico.

    Applied em mensagens de ERRO e recusa, nunca na resposta de conteúdo: uma
    resposta de conteúdo que cita "o sistema" ou "nota" é normal, e trocar
    ali destruiria a funcionalidade. A proteção do texto gerado pelo modelo é
    do `guardrails.py` (que conhece o contexto e sabe o que é dado legítimo).
    """
    if not texto or _TECNICOS.search(texto):
        return alternativa
    return texto
