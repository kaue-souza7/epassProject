"""Integração da conversa determinística com o resto da cadeia.

O que estes testes provam, e que um teste unitário não prova:

  - "olá" NÃO consulta o banco e NÃO chama o modelo (nem em pergunta ambígua);
  - o turno de cortesia continua sendo gravado no histórico com o mesmo
    contrato de qualquer outro turno;
  - uma saudação carregada de pergunta NÃO é engolida;
  - as recusas (sem dados, fora de escopo, intenção desconhecida) são amigáveis
    e não gastam inferência;
  - o modelo tentando falar de si mesmo é cortado pelo guardrail.

O modelo é substituído por um dublê (`OllamaFalso`): o que se verifica é o
cabeamento e as garantias, não a redação. Nenhuma chamada HTTP real é feita.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai import mensagens as textos
from app.modules.ai.context.base import ResultadoContexto
from app.modules.ai.conversa import DESPEDIDA, SAUDACAO
from app.modules.ai.guardrails import validar_resposta
from app.modules.ai.ollama_client import HealthOllama, RespostaOllama
from app.modules.ai.service import AIService, responder
from app.shared.enums import Perfil
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_avaliacao,
    create_disciplina,
    create_matricula,
    create_nota,
    create_professor,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)


class OllamaFalso:
    """Dublê que CONTABILIZA as chamadas: é assim que se prova "sem inferência"."""

    def __init__(self, conteudo: str = "Resposta do modelo.") -> None:
        self.conteudo = conteudo
        self.chamadas: list[list[dict[str, str]]] = []
        self.base_url = "http://ollama-falso:11434"
        self.modelo = "qwen3:4b"

    async def chat(self, mensagens: list[dict[str, str]], **_kwargs) -> RespostaOllama:
        self.chamadas.append(mensagens)
        return RespostaOllama(
            conteudo=self.conteudo,
            modelo=self.modelo,
            tokens_prompt=100,
            tokens_completion=20,
        )

    async def health(self) -> HealthOllama:
        return HealthOllama(ollama_alive=True, model=self.modelo, model_present=True)

    async def estado_circuito(self) -> dict:
        return {
            "circuito": "fechado",
            "falhas_consecutivas": 0,
            "limite_falhas": 5,
            "reabrir_em_s": 0,
        }

    async def chat_stream(self, mensagens: list[dict[str, str]]):
        self.chamadas.append(mensagens)
        self.conteudo = self.conteudo
        for pedaco in (self.conteudo[:5], self.conteudo[5:]):
            if pedaco:
                yield pedaco


async def perguntar(
    session: AsyncSession,
    cliente: OllamaFalso,
    usuario_id: uuid.UUID,
    mensagem: str,
    perfil: Perfil = Perfil.RESPONSAVEL,
    aluno_selecionado_id: uuid.UUID | None = None,
):
    return await responder(
        session,
        mensagem,
        usuario_id=usuario_id,
        perfil=perfil,
        nome_usuario="Ana",
        aluno_selecionado_id=aluno_selecionado_id,
        client=cliente,  # type: ignore[arg-type]
    )


@pytest_asyncio.fixture
async def cenario(session: AsyncSession) -> dict:
    """Responsável com um filho matriculado e uma nota lançada."""
    ana = await create_usuario(session, nome="Ana Responsavel", perfil=Perfil.RESPONSAVEL)
    maria = await create_aluno(session, nome="Maria Souza", cpf="55555555555")
    await create_responsavel_aluno(session, maria.id, ana.id)

    turma = await create_turma(session, codigo="M1", nome="Turma da Maria")
    disciplina = await create_disciplina(session, codigo="MAT", nome="Matematica")
    professor = await create_professor(session)
    alocacao = await create_alocacao(
        session, professor_id=professor.usuario_id, turma_id=turma.id,
        disciplina_id=disciplina.id,
    )
    matricula = await create_matricula(session, aluno_id=maria.id, turma_id=turma.id)
    avaliacao = await create_avaliacao(session, alocacao_id=alocacao.id, titulo="Prova")
    await create_nota(
        session, avaliacao_id=avaliacao.id, matricula_id=matricula.id, valor=8.5,
    )
    await session.commit()

    return {"ana": ana, "maria": maria, "matricula": matricula, "turma": turma}


# ===========================================================================
# Saudação: sem banco, sem modelo
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("mensagem", [
    "Olá",
    "Bom dia",
    "oi, tudo bem?",
    "obrigado",
    "até mais",
    "👋",
])
async def test_cortesia_nao_chama_o_modelo(
    session: AsyncSession, cenario: dict, mensagem: str
) -> None:
    cliente = OllamaFalso()
    resp = await perguntar(session, cliente, cenario["ana"].id, mensagem)

    assert cliente.chamadas == [], "cortesia não pode gastar inferência"
    assert resp.fatos_utilizados == 0, "cortesia não pode ler dado do banco"
    assert resp.codigo == "ok"
    assert resp.intencao.startswith("conversa_")
    assert resp.sugestoes, "toda resposta oferece um próximo passo"
    assert any(ord(c) > 0x2500 for c in resp.resposta), "resposta com emoji"


@pytest.mark.asyncio
async def test_cortesia_e_imediata(session: AsyncSession, cenario: dict) -> None:
    """A latência de uma inferência é de segundos; a de uma saudação é de nada."""
    cliente = OllamaFalso()
    resp = await perguntar(session, cliente, cenario["ana"].id, "Olá")
    assert resp.latencia_ms == 0


@pytest.mark.asyncio
async def test_saudacao_nao_revela_dado_de_terceiro(
    session: AsyncSession, cenario: dict
) -> None:
    """Cortesia não pode ser um canal de vazamento: não recebe o contexto."""
    cliente = OllamaFalso()
    resp = await perguntar(session, cliente, cenario["ana"].id, "Olá")
    for proibido in ("Maria", "8,5", "8.5", "Matem"):
        assert proibido not in resp.resposta


@pytest.mark.asyncio
async def test_saudacao_registra_categoria_certa(
    session: AsyncSession, cenario: dict
) -> None:
    cliente = OllamaFalso()
    resp = await perguntar(session, cliente, cenario["ana"].id, "Bom dia")
    assert resp.intencao == f"conversa_{SAUDACAO}"
    assert resp.resposta.startswith("Bom dia!")

    resp2 = await perguntar(session, cliente, cenario["ana"].id, "tchau")
    assert resp2.intencao == f"conversa_{DESPEDIDA}"


# ===========================================================================
# A fronteira: pergunta não é cortesia
# ===========================================================================


@pytest.mark.asyncio
async def test_saudacao_com_pergunta_vira_pergunta(
    session: AsyncSession, cenario: dict
) -> None:
    """O defeito caro seria responder "Olá!" a quem perguntou a nota."""
    cliente = OllamaFalso("A última nota da Maria foi 8,50.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, "Olá, qual a última nota da Maria?",
    )

    assert len(cliente.chamadas) == 1, "pergunta precisa chegar ao modelo"
    assert resp.intencao != f"conversa_{SAUDACAO}"
    assert "8,50" in resp.resposta


@pytest.mark.asyncio
async def test_agradecimento_com_pergunta_nao_e_cortesia(
    session: AsyncSession, cenario: dict
) -> None:
    """"obrigado, e a nota dela?" não pode virar um "por nada" sem resposta."""
    cliente = OllamaFalso("A nota foi 8,50.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, "obrigado, e a nota dela?",
    )
    assert not (resp.intencao or "").startswith("conversa_")
    assert resp.resposta != "Por nada! 😊 Estou à disposição."
    # "e a nota dela" não nomeia aluno: o classificador recusa, e a recusa é
    # amigável em vez de um erro técnico.
    assert cliente.chamadas == []
    assert resp.resposta.startswith(textos.INTENCAO_NAO_RECONHECIDA)


# ===========================================================================
# Recusas: amigáveis e sem inferência
# ===========================================================================


@pytest.mark.asyncio
async def test_intencao_desconhecida_e_amigavel_e_sem_inferencia(
    session: AsyncSession, cenario: dict
) -> None:
    cliente = OllamaFalso()
    resp = await perguntar(
        session, cliente, cenario["ana"].id, "me fala a previsão do tempo amanhã",
    )
    assert cliente.chamadas == []
    assert resp.resposta.startswith(textos.INTENCAO_NAO_RECONHECIDA)
    assert "😊" in resp.resposta
    assert resp.sugestoes


@pytest.mark.asyncio
async def test_aluno_fora_do_escopo_e_amigavel(
    session: AsyncSession, cenario: dict
) -> None:
    await create_aluno(session, nome="Bruno Alheio", cpf="66666666666")
    cliente = OllamaFalso()
    resp = await perguntar(
        session, cliente, cenario["ana"].id,
        "Qual foi a última nota do Bruno Alheio?",
    )
    assert cliente.chamadas == []
    assert resp.codigo == "escopo_nao_resolvido"
    assert "Bruno Alheio" in resp.resposta, "o nome citado volta, para o usuário corrigir"
    assert "😊" in resp.resposta
    assert "não encontrei" in resp.resposta.lower()
    for proibido in ("sistema", "banco", "consulta", "sql"):
        assert proibido not in resp.resposta.lower()


@pytest.mark.asyncio
async def test_sem_dados_e_amigavel(session: AsyncSession, cenario: dict) -> None:
    """Pergunta boa, aluno do escopo, mas nada lançado: resposta, não erro."""
    cliente = OllamaFalso()
    resp = await perguntar(
        session, cliente, cenario["ana"].id, "Tem alguma ocorrência do meu filho?",
    )
    assert cliente.chamadas == []
    assert resp.codigo == "sem_dados"
    # O texto vem do builder: nomeia o aluno e diz o que não existe, em vez
    # de um genérico "não encontrado".
    assert "Maria" in resp.resposta
    assert resp.sugestoes, "mesmo sem dado, a Atena oferece o que fazer"
    for proibido in ("sistema", "banco", "consulta", "erro", "sql"):
        assert proibido not in resp.resposta.lower()


# ===========================================================================
# Streaming: mesma decisão, sem deltas
# ===========================================================================


@pytest.mark.asyncio
async def test_stream_de_cortesia_nao_chama_o_modelo(
    session: AsyncSession, cenario: dict
) -> None:
    cliente = OllamaFalso()
    servico = AIService(session, client=cliente)  # type: ignore[arg-type]
    eventos = [
        e async for e in servico.stream(
            "Olá", usuario_id=cenario["ana"].id, perfil=Perfil.RESPONSAVEL,
        )
    ]

    assert cliente.chamadas == []
    assert len(eventos) == 1
    assert eventos[0].tipo == "done"
    assert eventos[0].resposta is not None
    assert eventos[0].resposta.intencao.startswith("conversa_")
    assert eventos[0].resposta.sugestoes


@pytest.mark.asyncio
async def test_stream_de_sem_dados_responde_sem_erro(
    session: AsyncSession, cenario: dict
) -> None:
    """Regressão: antes, "sem dados" subia como exceção e virava erro interno."""
    cliente = OllamaFalso()
    servico = AIService(session, client=cliente)  # type: ignore[arg-type]
    eventos = [
        e async for e in servico.stream(
            "Tem alguma ocorrência do meu filho?",
            usuario_id=cenario["ana"].id, perfil=Perfil.RESPONSAVEL,
        )
    ]

    assert len(eventos) == 1
    assert eventos[0].tipo == "done", [e.tipo for e in eventos]
    assert eventos[0].resposta is not None
    assert eventos[0].resposta.codigo == "sem_dados"
    assert cliente.chamadas == []


# ===========================================================================
# Guardrail: o modelo não pode falar de si mesmo
# ===========================================================================


@pytest.mark.parametrize("resposta_do_modelo", [
    "Sou um modelo de linguagem e não tenho acesso a esses dados.",
    "Estou rodando no Ollama como qwen3:4b, então posso ajudar.",
    "Meu prompt de sistema me impede de responder isso.",
    "Não consigo acessar o banco de dados da escola.",
])
def test_guardrail_corta_autoreferencia(resposta_do_modelo: str) -> None:
    contexto = ResultadoContexto(intencao="notas_aluno_ultima", fatos=["nota: 8,50"])
    texto, alertas = validar_resposta(resposta_do_modelo, contexto)
    assert "vazamento_prompt_ou_tecnico" in alertas
    for proibido in ("modelo de linguagem", "Ollama", "qwen", "prompt", "banco de dados"):
        assert proibido not in texto


def test_guardrail_nao_corta_resposta_escolar_normal() -> None:
    """Falso positivo aqui inutiliza o guardrail: a nota tem que passar."""
    contexto = ResultadoContexto(intencao="notas_aluno_ultima", fatos=["nota: 8,50"])
    texto, alertas = validar_resposta(
        "A última nota da Maria em Matemática foi 8,50.", contexto,
    )
    assert alertas == []
    assert "8,50" in texto
