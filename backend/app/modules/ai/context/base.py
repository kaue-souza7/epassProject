"""Infraestrutura dos context builders.

REGRA INEGOCIÁVEL DESTE PACOTE
------------------------------
Nenhum builder pode:
  - consultar uma tabela "global" e filtrar depois (o filtro entra no WHERE);
  - aceitar um `aluno_id`/`turma_id` que não tenha sido resolvido dentro do
    escopo do usuário;
  - devolver dados de outra pessoa.

O fluxo é sempre: resolver escopo → consultar já restrito → formatar.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.modules.ai.exceptions import EscopoNaoResolvidoErro
from app.modules.ai.intent import normalizar


@dataclass
class AlunoNoEscopo:
    """Aluno JÁ verificado como pertencente ao escopo do usuário solicitante.

    Este dataclass é a "moeda" de autorização: os builders só recebem
    instâncias dele. Não existe caminho para montar um `AlunoNoEscopo` com um
    aluno que o usuário não pode ver.
    """

    id: uuid.UUID
    nome: str
    turma_nome: str | None = None
    serie_nome: str | None = None
    parentesco: str | None = None

    @property
    def rotulo(self) -> str:
        partes = [self.nome]
        if self.turma_nome:
            partes.append(f"({self.turma_nome})")
        return " ".join(partes)


@dataclass
class ResultadoContexto:
    """Contexto autorizado, pronto para virar prompt.

    `fatos` são linhas de fato que o modelo pode usar. `vazio=True` significa
    "consultei dentro do escopo e não há nada" — a resposta correta é dizer que
    não encontrou, nunca inventar.
    """

    intencao: str
    fatos: list[str] = field(default_factory=list)
    resumo: str = ""
    vazio: bool = False
    # Nomes de fontes consultadas (auditoria; nunca exposto ao LLM).
    fontes: list[str] = field(default_factory=list)
    # Ids de aluno/turma efetivamente consultados, já autorizados.
    alunos_autorizados: list[uuid.UUID] = field(default_factory=list)
    turmas_autorizadas: list[uuid.UUID] = field(default_factory=list)

    def adicionar(self, linha: str) -> None:
        self.fatos.append(linha)

    def __str__(self) -> str:  # pragma: no cover - formatação
        if self.vazio or not self.fatos:
            return "<SEM_DADOS>"
        return "\n".join(self.fatos)


# ---------------------------------------------------------------------------
# Formatadores (nenhum dado sensível: sem CPF, endereço, telefone, e-mail)
# ---------------------------------------------------------------------------

def formatar_data(valor: date | datetime | None) -> str:
    if valor is None:
        return "-"
    return f"{valor.day:02d}/{valor.month:02d}/{valor.year}"


def formatar_decimal(valor: Decimal | float | None, casas: int = 2) -> str:
    if valor is None:
        return "-"
    texto = f"{float(valor):.{casas}f}"
    return texto.replace(".", ",")


def formatar_enum(valor) -> str:
    """Enum do projeto -> texto legível ('resolvida' -> 'Resolvida')."""
    if valor is None:
        return "-"
    bruto = getattr(valor, "value", str(valor))
    return str(bruto).replace("_", " ").capitalize()


# ---------------------------------------------------------------------------
# Resolução de aluno dentro do escopo
# ---------------------------------------------------------------------------


def resolver_por_nome(
    alunos: list[AlunoNoEscopo],
    nome_candidato: str | None,
) -> AlunoNoEscopo | None:
    """Resolve o nome citado na pergunta ENTRE OS ALUNOS JÁ AUTORIZADOS.

    Não existe fallback para busca global: se o nome não estiver na lista do
    escopo, a resposta é recusa. É isso que impede o vazamento clássico
    "qual a nota do João?" contra a tabela global de alunos.

    Tolerâncias aceitas (nunca fora do escopo): nome completo, primeiro nome e
    sobrenome. Um nome ambíguo (dois filhos com o mesmo primeiro nome) NÃO é
    adivinhado: retorna None para que `escolher_aluno` peça a especificação.
    """
    if not alunos or not nome_candidato:
        return None

    alvo = normalizar(nome_candidato)
    if not alvo:
        return None

    # 1) Correspondência exata do nome completo.
    for aluno in alunos:
        if normalizar(aluno.nome) == alvo:
            return aluno

    # 2) Primeiro nome citado. Ambíguo -> None (pede desambiguação).
    primeiro = alvo.split()[0]
    if len(primeiro) >= 3:
        por_primeiro = [a for a in alunos if normalizar(a.nome).split()[0] == primeiro]
        if len(por_primeiro) == 1:
            return por_primeiro[0]
        if len(por_primeiro) > 1:
            return None

    # 3) Sobrenome citado (o próprio ou parte dele), com 4+ letras.
    if len(alvo) >= 4:
        for aluno in alunos:
            if alvo in normalizar(aluno.nome):
                return aluno

    return None


def resolver_por_primeiro_nome_no_escopo(
    alunos: list[AlunoNoEscopo],
    mensagem: str,
) -> AlunoNoEscopo | None:
    """Casa o primeiro nome de um aluno DO ESCOPO citado na pergunta.

    Por que isto existe: a extração genérica de nomes só considera duas ou mais
    palavras capitalizadas, então "a nota da Maria" não produzia candidata
    alguma e um responsável com dois filhos recebia sempre "sobre qual deles?".
    Aqui a comparação é feita **contra os nomes já autorizados**, o que elimina
    a heurística frágil de adivinhar o que é nome: só há match se a palavra
    citada for literalmente o primeiro nome de alguém do escopo.

    Devolve None quando não casa ou quando casa mais de um ("Maria Souza" e
    "Maria Costa" -> desambiguação, nunca palpite).
    """
    if not alunos or not mensagem:
        return None

    # `normalizar` tira acento e caixa, mas preserva a pontuação — e a
    # pontuação gruda na última palavra ("Maria?" != "maria"). Por isso as
    # palavras são remontadas aqui só com letras e dígitos, o que também
    # garante a fronteira de palavra: "marias" não casa com "maria".
    limpo = normalizar(mensagem)
    if not limpo:
        return None
    palavras = {p for p in re.split(r"[^0-9a-z]+", limpo) if p}

    achados = [
        aluno
        for aluno in alunos
        if normalizar(aluno.nome).split()[0] in palavras
    ]
    if len(achados) == 1:
        return achados[0]
    return None


def escolher_aluno(
    alunos: list[AlunoNoEscopo],
    nome_candidato: str | None,
    aluno_selecionado_id: uuid.UUID | None = None,
    *,
    mensagem: str = "",
) -> AlunoNoEscopo:
    """Aplica a precedência de desambiguação do requisito.

    1. nome citado na pergunta (completo), resolvido dentro do escopo;
    2. primeiro nome de um aluno do escopo citado na pergunta;
    3. aluno selecionado ativamente (web/mobile);
    4. único aluno do responsável;
    5. ambiguidade -> erro pedindo a especificação.

    Dois casos de recusa explícita, por segurança:

    - o nome citado NÃO pertence ao escopo: em vez de degradar para "o primeiro
      filho" (o que responderia sobre a pessoa errada), a resposta é recusa;
    - o `aluno_selecionado_id` NÃO pertence ao escopo: idem. Sem isso, um id
      adulterado no corpo da requisição faria a IA responder sobre outro aluno
      enquanto o usuário acreditava estar vendo o selecionado.
    """
    if not alunos:
        raise EscopoNaoResolvidoErro(
            "Não há alunos vinculados ao seu usuário no sistema."
        )

    if nome_candidato:
        resolvido = resolver_por_nome(alunos, nome_candidato)
        if resolvido is not None:
            return resolvido
        # Havia um nome na pergunta e ele NÃO pertence ao escopo. O nome citado
        # volta na resposta: é o que permite ao usuário perceber o erro de
        # digitação. A razão da recusa fica implícita, não anunciada.
        raise EscopoNaoResolvidoErro(
            f"Não encontrei nenhum aluno chamado '{nome_candidato}' entre os "
            f"seus filhos. 😊 Confira o nome ou o vínculo no ePass — enquanto "
            f"isso, posso olhar outro assunto."
        )

    # Primeiro nome citado ("a nota da Maria"): só casa com quem já está no
    # escopo, então não existe caminho para alcançar um aluno de fora.
    if mensagem:
        por_primeiro = resolver_por_primeiro_nome_no_escopo(alunos, mensagem)
        if por_primeiro is not None:
            return por_primeiro

    if aluno_selecionado_id:
        for aluno in alunos:
            if aluno.id == aluno_selecionado_id:
                return aluno
        raise EscopoNaoResolvidoErro(
            "O aluno selecionado não está entre os seus filhos. 😊 Posso "
            "ajudar com outro assunto enquanto isso."
        )

    if len(alunos) == 1:
        return alunos[0]

    nomes = ", ".join(a.nome for a in alunos[:5])
    raise EscopoNaoResolvidoErro(
        f"Você tem {len(alunos)} alunos vinculados ({nomes}). "
        "Sobre qual deles você quer a informação?"
    )
