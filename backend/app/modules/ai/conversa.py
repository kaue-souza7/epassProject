"""Conversa simples, resolvida sem tocar no banco e sem chamar o modelo.

POR QUE ISTO EXISTE
-------------------
"Olá", "obrigado" e "até mais" não são pergunta sobre a escola: são
acolhimento. Respondê-las com uma inferência de vários segundos gastaria a
latência mais valiosa do produto (e a RAM) para redigir "Olá!".

São também as mensagens em que o usuário menos espera uma máquina. É o ponto
em que a Atena precisa soar HUMANA, e um modelo local pequeno erra ali com
frequência: devolve raciocínio vazado, texto truncado ou uma frase seca sem a
saudação de volta. Determinismo resolve melhor que probabilidade aqui — a
resposta é sempre a mesma e sai em milissegundos.

ESCOPO (por desenho, não por conveniência)
------------------------------------------
Este módulo:

  - NÃO recebe sessão, NÃO consulta banco e NÃO conhece `usuario_id`;
  - NÃO recebe o contexto autorizado (nenhum dado entra no texto);
  - NÃO chama o Ollama;
  - NÃO depende do perfil, porque não revela nada que varie por perfil.

Ele decide APENAS se a mensagem é "cortesia". Se a mensagem perguntar algo —
por mais curto que seja ("e a nota?") — ela NÃO casa aqui e segue para
`intent.classificar`, que é quem consulta os dados. Duas guardas explícitas
protegem essa fronteira: uma lista de termos que indicam pergunta e o
Reconhecimento de referência a um turno anterior ("e ela?").

CRITÉRIO
--------
O padrão é "a mensagem INTEIRA é apenas cortesia", nunca "a mensagem contém
'olá'". Por isso "Olá, qual a nota do Miguel?" não é tratada como saudação:
ela não pertence a nenhum conjunto abaixo e o classificador assume.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

# Emoji e emoticons no lugar de palavras. Removidos ANTES da comparação para
# que "👋" e "olá" caiam no mesmo balde.
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]+"
)
_PONTUACAO = re.compile(r"[!,.?;:…\-—_*\"'`()\[\]{}]+")
_ESPACOS = re.compile(r"\s+")


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento, sem emoji, sem pontuação, espaços colapsados."""
    sem_acento = unicodedata.normalize("NFD", texto)
    limpo = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    limpo = _EMOJI.sub(" ", limpo)
    limpo = _PONTUACAO.sub(" ", limpo)
    return _ESPACOS.sub(" ", limpo.lower()).strip()


# ---------------------------------------------------------------------------
# Categorias de cortesia
# ---------------------------------------------------------------------------

SAUDACAO = "saudacao"
AGRADECIMENTO = "agradecimento"
DESPEDIDA = "despedida"

# Cada conjunto só aceita mensagens QUE INTEIRAM são aquela cortesia. É essa
# lista explícita — e não uma regex solta — que impede "olá, me diga a nota"
# de ser engolida.
_SAUDACOES: frozenset[str] = frozenset({
    "ola",
    "oi",
    "opa",
    "e ai",
    "eai",
    "hey",
    "fala",
    "salve",
    "tudo bem",
    "tudo bem com voce",
    "tudo certo",
    "tudo certo com voce",
    "oi tudo bem",
    "ola tudo bem",
    "como voce esta",
    "como voce esta hoje",
    "como vai",
    "como vai voce",
    "como foi seu dia",
    "bom dia",
    "bom dia tudo bem",
    "bom dia tudo bem com voce",
    "boa tarde",
    "boa tarde tudo bem",
    "boa tarde tudo bem com voce",
    "boa noite",
    "boa noite tudo bem",
    "boa noite tudo bem com voce",
    "fala atena",
    "ola atena",
    "oi atena",
    "eai atena",
    "opa atena",
    "bom dia atena",
    "boa tarde atena",
    "boa noite atena",
    "tudo bem atena",
})

_AGRADECIMENTOS: frozenset[str] = frozenset({
    "obrigado",
    "obrigada",
    "muito obrigado",
    "muito obrigada",
    "valeu",
    "vlw",
    "valeu atena",
    "obrigado atena",
    "agradeço",
    "agradeco",
    "agradeco muito",
    "muito grato",
    "muito grata",
    "era isso",
    "isso",
    "perfeito",
    "otimo",
    "otima",
    "show",
    "legal",
    "massa",
    "entendi",
    "entendi obrigado",
    "ok obrigado",
    "beleza",
    "beleza obrigado",
    "blz obrigado",
    "fechado",
    "fechado obrigado",
    "ok",
    "beleza valeu",
    "era isso obrigado",
    "valeu obrigado",
})

_DESPEDIDAS: frozenset[str] = frozenset({
    "ate mais",
    "ate logo",
    "ate breve",
    "te ate mais",
    "tchau",
    "tchauzinho",
    "tchau atena",
    "flw",
    "flw atena",
    "falou",
    "falou atena",
    "e ate mais",
    "e ate logo",
    "vou indo",
    "vou dormir",
    "tenho que ir",
    "preciso ir",
    "era isso tchau",
    "era isso ate mais",
    "obrigado tchau",
    "valeu tchau",
})

_CONJUNTOS: dict[str, frozenset[str]] = {
    SAUDACAO: _SAUDACOES,
    AGRADECIMENTO: _AGRADECIMENTOS,
    DESPEDIDA: _DESPEDIDAS,
}

# Despedida tem precedência sobre agradecimento e sobre saudação: "valeu, até
# mais" é despedida, e não "valeu" com sobra.
_ORDEM: tuple[str, ...] = (DESPEDIDA, AGRADECIMENTO, SAUDACAO)

# Frases que carregam uma PERGUNTA mesmo parecendo cortesia.
_PERGUNTA = re.compile(
    r"\b(qual|quais|quanto|quanta|quando|onde|quem|por que|porque|"
    r"tem alguma|tem algum|tem mais|me diz|me fala|fala sobre|mostra|"
    r"nota|notas|boletim|boletins|media|medias|frequencia|falta|falta falta|"
    r"avisos?|ocorrencia|ocorrencias|saldo|carteira|agenda|evento|eventos|"
    r"materia|materias|disciplina|disciplinas|turma|turmas|pai|mae|pais|maes|"
    r"filho|filha|filhos|filhas)\b"
)

# Referência a um turno anterior ("e ela?", "e a última?"). Continua sendo
# pergunta, mesmo sem verbo: precisa do classificador e do contexto.
_REFERENCIA = re.compile(r"^(e|ela|ele|a|o|os|as|sobre|entao|agora|qual)\s")

# ---------------------------------------------------------------------------
# Respostas
# ---------------------------------------------------------------------------

# A saudação responde com o MESMO período que o usuário usou. "Bom dia!" merece
# "Bom dia!", não "Olá!" — é o detalhe que faz soar humano em vez de template.
_SAUDACAO_POR_PERIODO: tuple[tuple[str, str], ...] = (
    ("bom dia", "Bom dia! 😊 Como posso ajudar você hoje?"),
    ("boa tarde", "Boa tarde! 😊 Como posso ajudar você hoje?"),
    ("boa noite", "Boa noite! 😊 Como posso ajudar você hoje?"),
)

_SAUDACOES_RESPOSTA: tuple[str, ...] = (
    "Olá! 😊 Como posso ajudar você hoje?",
    "Oi! 😊 Estou por aqui — como posso ajudar?",
)

_AGRADECIMENTOS_RESPOSTA: tuple[str, ...] = (
    "Por nada! 😊 Estou à disposição.",
    "Imagina! 😊 Se precisar de mais alguma coisa, é só chamar.",
    "De nada! 😊 Que bom poder ajudar.",
)

_DESPEDIDAS_RESPOSTA: tuple[str, ...] = (
    "Até mais! 😊 Se precisar, é só chamar.",
    "Até logo! 😊 Foi bom falar com você.",
    "Tchau! 😊 Qualquer coisa, estou por aqui.",
)

_RESPOSTAS: dict[str, tuple[str, ...]] = {
    SAUDACAO: _SAUDACOES_RESPOSTA,
    AGRADECIMENTO: _AGRADECIMENTOS_RESPOSTA,
    DESPEDIDA: _DESPEDIDAS_RESPOSTA,
}

# O que a Atena sugere depois de uma cortesia: o caminho de volta para o que
# ela sabe fazer de verdade.
_SUGESTOES: dict[str, tuple[str, ...]] = {
    SAUDACAO: (
        "Como estão as notas do meu filho?",
        "Quantas faltas ele tem?",
        "Tem algum aviso para mim?",
    ),
    AGRADECIMENTO: (
        "Quero ver o boletim",
        "Como está o saldo da carteira?",
    ),
    DESPEDIDA: (
        "Até mais!",
        "Preciso de ajuda com o boletim",
    ),
}


def _variar(opcoes: tuple[str, ...], mensagem_normalizada: str) -> str:
    """Varia a resposta sem parecer aleatória nem exigir estado entre requisições.

    A semente é a própria mensagem, então "obrigado" sempre recebe a mesma
    variação — a consistência é parte do contrato.
    """
    return opcoes[sum(ord(c) for c in mensagem_normalizada) % len(opcoes)]


def _saudacao_por_periodo(normalizada: str) -> str:
    """Responde com o MESMO período que o usuário usou.

    "Bom dia!" merece "Bom dia!", não "Olá!" — é o detalhe que faz a conversa
    soar humana em vez de template.
    """
    for periodo, texto in _SAUDACAO_POR_PERIODO:
        if periodo in normalizada:
            return texto
    return _variar(_SAUDACOES_RESPOSTA, normalizada)


def classificar_conversa(mensagem: str) -> tuple[str, str, tuple[str, ...]] | None:
    """Devolve `(categoria, resposta, sugestoes)` se a mensagem for só cortesia.

    Devolve `None` em qualquer outro caso — aí quem responde é o classificador
    de intenção, com o contexto autorizado do banco.
    """
    normalizada = _normalizar(mensagem)
    if not normalizada:
        # Só emoji ("👋", "👍"): o usuário cumprimentou, mesmo sem escrever.
        if _EMOJI.search(mensagem):
            return SAUDACAO, _SAUDACOES_RESPOSTA[0], _SUGESTOES[SAUDACAO]
        return None

    # A pertinência ao conjunto é autoritativa: a lista compara a mensagem
    # INTEIRA, então "e aí" é saudação mesmo começando com "e" e "valeu" é
    # agradecimento mesmo depois de uma pergunta anterior.
    #
    # Importante: a verificação vem ANTES das guardas de pergunta. Na ordem
    # inversa, "e aí" era barrado pela regra de referência a turno anterior e
    # o usuário recebia um "não entendi" no lugar de um "olá" — o defeito mais
    # visível possível numa conversa de Cumprimento.
    for categoria in _ORDEM:
        if normalizada in _CONJUNTOS[categoria]:
            if categoria == SAUDACAO:
                return categoria, _saudacao_por_periodo(normalizada), _SUGESTOES[categoria]
            opcoes = _RESPOSTAS[categoria]
            return categoria, _variar(opcoes, normalizada), _SUGESTOES[categoria]

    # Não pertence a nenhum conjunto: não é cortesia, por construção. A guarda
    # de pergunta é a segunda camada, para blindar o dia em que alguém acrescentar
    # uma frase a uma lista sem pensar numa eventual pergunta disfarçada.
    if _PERGUNTA.search(normalizada) or _REFERENCIA.match(normalizada):
        return None

    return None
