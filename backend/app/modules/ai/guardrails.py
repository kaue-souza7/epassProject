"""Guardrails de pós-processamento da resposta do modelo.

O prompt NÃO é garantia. Um modelo local pode inventar um número mesmo com
instrução clara — especialmente em notas, valores e datas, que é exatamente o
tipo de dado escolar que não pode ser fabrilado.

Aqui fazemos validação MECÂNICA (sem LLM) da resposta:

  1. Vazamento de prompt: se a resposta reproduz instruções internas, é
     substituída por uma mensagem neutra.
  2. Vazamento técnico: nomes de tabela/coluna, SQL, rotas de API.
  3. Alucinação numérica: todo número presente na resposta precisa existir no
     contexto autorizado. É o guardrail mais importante para dados escolares.
  4. Resposta vazia/inútil: cai para um texto padrão seguro.

O objetivo NÃO é reescrever a resposta com IA (seria outro modelo inventando),
é apenas rejeitar/reescrever o que é comprovadamente inseguro.
"""

from __future__ import annotations

import re

from app.modules.ai import mensagens as textos
from app.modules.ai.context.base import ResultadoContexto

# Termos que denunciam vazamento de instrução interna.
_MARCAS_PROMPT = (
    "dados_autORIZADOS".lower(),
    "regras inegociaveis",
    "system prompt",
    "você é a atena, assistente",
    "prompt de sistema",
    "resumo factual",
    "lista de dados encurtada",
)

# Termos técnicos que nunca devem aparecer na resposta ao usuário.
_PADROES_TECNICOS = (
    r"\bselect\s+.+\s+from\b",
    r"\bjoin\b.+\bon\b",
    r"\binsert\s+into\b",
    r"\bupdate\s+\w+\s+set\b",
    r"\bdelete\s+from\b",
    r"/api/v1",
    r"\bdb\.\w+",
    r"\bturmas?\b.*\bid\s*=",
    r"\baluno_id\b",
    r"\bresponsavel_id\b",
    r"\bmatricula_id\b",
    r"\busuario_id\b",
    r"\btoken\b",
    r"\bprompt\b",
    r"\bollama\b",
    r"\bqwen\b",
    r"\bllm\b",
    r"\bguardrails?\b",
    r"\bembedding\b",
    r"\bhttp[s]?\b",
    r"\bendpoint\b",
    r"banco\s+de\s+dados",
)

# A Atena é uma assistente, não uma tecnologia. Quando o modelo sai do papel e
# passa a comentar a si mesmo ("sou um modelo de linguagem"), a resposta vira
# uma explicação de infraestrutura — que é exatamente o que o usuário não
# deveria ler. Isso é tratado como vazamento, do mesmo jeito que o system
# prompt: é papel, não dado.
_PADROES_AUTOREFERENCIA = (
    r"\bsou\s+(um|uma)\s+(ia|modelo|assistente\s+autom)",
    r"\bcomo\s+(um|uma)\s+(ia|modelo)\b",
    r"\bmodelo\s+de\s+l\w+\b",
    r"\bmeu\s+treinamento\b",
    r"\btreinei\s+(com|em|para)\b",
    r"\bmeu\s+prompt\b",
    r"\bminhas?\s+instru\w+\b",
    r"\bfui\s+(programad|construíd|treinad)[ao]\b",
    r"\bmeu\s+c\w+digo\b",
)

# Números: moeda (R$), percentual e número "solto" (notas, médias, datas).
# O caso "solto" é o que mais importa aqui: uma nota inventada ("a nota foi
# 9,75") não tem R$ nem %, e é exatamente o dado que não pode ser fabrilado.
_RE_NUMERO = re.compile(
    r"(?<![\w])R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?)"
    r"|(?<![\w])(\d+(?:[.,]\d+)?)\s*%"
    r"|(?<![\w.,])(\d+(?:[.,]\d+)?)(?![\w]*[,.]\d)"
)

_TEXTO_SEGURO_SEM_NUMERO = (
    "Não consegui confirmar um dos números dessa resposta, então prefiro não "
    "afirmar: ainda não tenho essa informação. 😊 Posso te ajudar com outro "
    "assunto?"
)

_TEXTO_SEGURO_VAZAMENTO = (
    "Prefiro não detalhar isso aqui. 😊 Mas posso te dizer o que está "
    "registrado no ePass sobre isso — é só me perguntar de novo!"
)


def _numeros_autorizados(contexto: ResultadoContexto) -> set[float]:
    """Números presentes nos fatos autorizados, como valores.

    Ex.: uma nota 8,5 vira 8.5 — assim "8,50", "8.5" e "8,5" na resposta são
    todos reconhecidos como o mesmo número, independentemente da formatação.
    """
    texto = " ".join(contexto.fatos)
    if contexto.resumo:
        texto += " " + contexto.resumo

    autorizados: set[float] = set()
    for match in re.finditer(r"\d+(?:[.,]\d+)*", texto):
        valor = _para_float(match.group(0))
        if valor is not None:
            autorizados.add(valor)
    return autorizados


def _contem_vazamento(texto: str) -> bool:
    minusculo = texto.lower()
    if any(marca in minusculo for marca in _MARCAS_PROMPT):
        return True
    padroes = _PADROES_TECNICOS + _PADROES_AUTOREFERENCIA
    return any(re.search(padrao, minusculo) for padrao in padroes)


def _para_float(texto: str) -> float | None:
    """Converte um número escrito em pt-BR ou US para float.

    "8,5", "8.5", "8,50" -> 8.5 ; "1.234,56" -> 1234.56 ; "1,234.56" -> 1234.56
    """
    limpo = re.sub(r"[^\d.,]", "", texto)
    if not limpo or not re.search(r"\d", limpo):
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+,\d+", limpo):
        # pt-BR: ponto é separador de milhar, vírgula é decimal.
        limpo = limpo.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+\.\d+", limpo):
        # US: vírgula é separador de milhar, ponto é decimal.
        limpo = limpo.replace(",", "")
    else:
        limpo = limpo.replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _mesmo_numero(candidato: str, autorizados: set[float]) -> bool:
    """Compara por VALOR, não por texto.

    "8,5", "8.5" e "8,50" são o mesmo número; "10" e "10,00" também. Sem
    normalizar, o modelo seria cortado por formatar a nota de um jeito
    equivalente — e o guardrail perderia a credibilidade justamente no caso que
    ele existe para pegar.
    """
    valor = _para_float(candidato)
    if valor is None:
        return True
    return any(abs(valor - autorizado) < 1e-9 for autorizado in autorizados)


def _numero_nao_autorizado(texto: str, autorizados: set[float]) -> str | None:
    """Retorna o primeiro número presente na resposta que não está no contexto.

    Ignora marcadores de lista ("1.", "- 2)") e ordinais ("3º bimestre"): são
    forma, não dado. Um corte falso aqui custaria mais caro que o defeito que
    o guardrail corrige.
    """
    for match in _RE_NUMERO.finditer(texto):
        candidato = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if not candidato:
            continue
        if _mesmo_numero(candidato, autorizados):
            continue
        if _eh_marcador_de_lista(texto, match):
            continue
        return candidato
    return None


def _eh_marcador_de_lista(texto: str, match: re.Match) -> bool:
    antes = texto[: match.start()].rstrip()
    depois = texto[match.end() :].lstrip()
    if antes.endswith(("-", "•", "*")):
        return True
    if match.group(3) and not match.group(1) and not match.group(2):
        # Só é marcador se for um inteiro curto no início da linha ("1.").
        if "." in match.group(0):
            return True
        if match.group(0) + "º" == depois[:2] or match.group(0) + "o" == depois[:2]:
            return True
    return False


def validar_resposta(
    resposta: str,
    contexto: ResultadoContexto,
) -> tuple[str, list[str]]:
    """Filtra a resposta do modelo.

    Returns:
        (texto_final, alertas) — `alertas` registra o que foi bloqueado, para
        observabilidade/log (nunca é exposto ao usuário).
    """
    alertas: list[str] = []
    texto = (resposta or "").strip()

    if not texto:
        alertas.append("resposta_vazia")
        return textos.SEM_INFORMACOES, alertas

    if _contem_vazamento(texto):
        alertas.append("vazamento_prompt_ou_tecnico")
        return _TEXTO_SEGURO_VAZAMENTO, alertas

    nao_autorizado = _numero_nao_autorizado(texto, _numeros_autorizados(contexto))
    if nao_autorizado is not None:
        alertas.append(f"numero_nao_autorizado:{nao_autorizado}")
        return _TEXTO_SEGURO_SEM_NUMERO, alertas

    return texto, alertas
