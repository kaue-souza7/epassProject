"""Testes de integração do assistente — ESCOPO e ISOLAMENTO (Fase 2).

O modelo é substituído por um dublê (`OllamaFalso`): o que está sendo verificado
não é a qualidade da redação, e sim **o que o backend entrega ao modelo** e o
que ele faz com a resposta. Nenhuma chamada HTTP real é feita.

Cenário montado:
  - Ana (responsável) -> Maria, nota 8,50, ocorrência, saldo 25,50
  - Bruno (responsável) -> Pedro (nota 3,00) e Carlos (nota 2,00)
  - Prof A com alocação na turma da Maria
  - Prof B com alocação em outra turma (Pedro e Carlos)

Asserções centrais:
  - responsável só enxerga o próprio filho (nunca o do outro);
  - nome citado fora do escopo é RECUSA, sem tocar a tabela global;
  - `aluno_selecionado_id` fora do escopo é RECUSA (não degrada para outro aluno);
  - professor só enxerga as turmas das próprias alocações;
  - intenção de outro perfil é bloqueada;
  - recusas e "sem dados" NÃO gastam inferência;
  - contexto nunca contém CPF/contato/schema/SQL;
  - guardrail corta número que o modelo inventou.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.ollama_client import HealthOllama, RespostaOllama
from app.modules.ai.service import responder
from app.modules.communication.models import Aviso, AvisoDestinatario, Ocorrencia
from app.modules.financial.models import Wallet
from app.shared.enums import (
    Perfil,
    SeveridadeOcorrencia,
    StatusAviso,
    StatusCarteira,
    StatusOcorrencia,
    TipoOcorrencia,
)
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


# ---------------------------------------------------------------------------
# Dublê do Ollama
# ---------------------------------------------------------------------------
class OllamaFalso:
    """Cliente de IA de mentira que registra o que o backend lhe entregou."""

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

    @property
    def contexto(self) -> str:
        """Tudo que o backend mandou para o modelo."""
        if not self.chamadas:
            return ""
        return "\n".join(m["content"] for m in self.chamadas[-1])


async def perguntar(
    session: AsyncSession,
    cliente: OllamaFalso,
    usuario_id: uuid.UUID,
    perfil: Perfil,
    mensagem: str,
    aluno_selecionado_id: uuid.UUID | None = None,
    nome: str = "Usuário Teste",
):
    return await responder(
        session,
        mensagem,
        usuario_id=usuario_id,
        perfil=perfil,
        nome_usuario=nome,
        aluno_selecionado_id=aluno_selecionado_id,
        client=cliente,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Cenário
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def cenario(session: AsyncSession) -> dict:
    agora = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)

    # --- Responsáveis e filhos ---
    ana = await create_usuario(session, nome="Ana Responsavel", perfil=Perfil.RESPONSAVEL)
    bruno = await create_usuario(session, nome="Bruno Responsavel", perfil=Perfil.RESPONSAVEL)
    sem_filho = await create_usuario(
        session, nome="Solteiro", perfil=Perfil.RESPONSAVEL,
    )

    maria = await create_aluno(session, nome="Maria Souza", cpf="11111111111")
    pedro = await create_aluno(session, nome="Pedro Alves", cpf="22222222222")
    carlos = await create_aluno(session, nome="Carlos Souza", cpf="33333333333")
    # Gêmeo de primeiro nome: serve para testar a ambiguidade.
    maria2 = await create_aluno(session, nome="Maria Costa", cpf="44444444444")

    await create_responsavel_aluno(session, maria.id, ana.id)
    await create_responsavel_aluno(session, maria2.id, ana.id)
    await create_responsavel_aluno(session, pedro.id, bruno.id)
    await create_responsavel_aluno(session, carlos.id, bruno.id)

    # --- Turmas e professores ---
    disciplina = await create_disciplina(session, codigo="MAT", nome="Matematica")
    turma_maria = await create_turma(session, codigo="M1", nome="Turma da Maria")
    turma_outra = await create_turma(session, codigo="P1", nome="Turma de Outro")

    prof_a = await create_professor(session)
    prof_b = await create_professor(session)

    await create_alocacao(
        session, professor_id=prof_a.usuario_id, turma_id=turma_maria.id,
        disciplina_id=disciplina.id,
    )
    await create_alocacao(
        session, professor_id=prof_b.usuario_id, turma_id=turma_outra.id,
        disciplina_id=disciplina.id,
    )

    mat_maria = await create_matricula(session, aluno_id=maria.id, turma_id=turma_maria.id)
    mat_pedro = await create_matricula(session, aluno_id=pedro.id, turma_id=turma_outra.id)
    mat_carlos = await create_matricula(session, aluno_id=carlos.id, turma_id=turma_outra.id)

    # --- Notas. Maria fica ABAIXO da média de corte (6,00 < 7,00) para que o
    #     professor A a enxergue em "alunos abaixo da média".
    from app.modules.academic_config.models import ConfiguracaoAcademica
    from app.modules.allocations.repository import AlocacaoRepository

    alocacoes_a, _ = await AlocacaoRepository(session).search(
        professor_id=prof_a.usuario_id, only_active=True,
    )
    alocacoes_b, _ = await AlocacaoRepository(session).search(
        professor_id=prof_b.usuario_id, only_active=True,
    )
    assert len(alocacoes_a) == 1 and len(alocacoes_b) == 1

    # Média de corte explícita: o builder usa a configuração acadêmica como
    # fonte da verdade, e o teste não deve depender do fallback 7,0.
    ano_letivo_id = turma_maria.ano_letivo_id
    session.add(ConfiguracaoAcademica(
        ano_letivo_id=ano_letivo_id,
        media_aprovacao=7.0,
        frequencia_minima=75.0,
        possui_recuperacao=False,
        media_minima_recuperacao=None,
        quantidade_periodos=2,
        ativo=True,
    ))
    await session.flush()

    aval_maria = await create_avaliacao(
        session, alocacao_id=alocacoes_a[0].id, titulo="Prova de Matematica",
    )
    await create_nota(
        session, avaliacao_id=aval_maria.id, matricula_id=mat_maria.id, valor=6.0,
    )

    aval_pedro = await create_avaliacao(
        session, alocacao_id=alocacoes_b[0].id, titulo="Prova de Portugues",
    )
    await create_nota(
        session, avaliacao_id=aval_pedro.id, matricula_id=mat_pedro.id, valor=3.0,
    )
    await create_nota(
        session, avaliacao_id=aval_pedro.id, matricula_id=mat_carlos.id, valor=2.0,
    )

    # --- Ocorrências ---
    session.add(Ocorrencia(
        aluno_id=maria.id, turma_id=turma_maria.id,
        titulo="Chegada atrasada", descricao="Chegou 20 minutos atrasado",
        tipo=TipoOcorrencia.COMPORTAMENTO, severidade=SeveridadeOcorrencia.BAIXA,
        status=StatusOcorrencia.ABERTA, criado_por=prof_a.usuario_id,
        created_at=agora,
    ))
    session.add(Ocorrencia(
        aluno_id=pedro.id, turma_id=turma_outra.id,
        titulo="Conflito com colega", descricao="Conflito",
        tipo=TipoOcorrencia.COMPORTAMENTO, severidade=SeveridadeOcorrencia.MEDIA,
        status=StatusOcorrencia.ABERTA, criado_por=prof_b.usuario_id,
        created_at=agora,
    ))

    # --- Carteiras ---
    session.add(Wallet(
        aluno_id=maria.id, saldo=Decimal("25.50"), status=StatusCarteira.ATIVA,
    ))
    session.add(Wallet(
        aluno_id=pedro.id, saldo=Decimal("5.00"), status=StatusCarteira.ATIVA,
    ))

    # --- Avisos ---
    aviso_lido = Aviso(
        titulo="Reuniao de pais", mensagem="Reuniao na segunda", tipo="geral",
        prioridade="media", status=StatusAviso.PUBLICADO,
        criado_por=prof_a.usuario_id, publicado_em=agora,
    )
    aviso_feriado = Aviso(
        titulo="Feriado municipal", mensagem="Escola fechada na sexta", tipo="geral",
        prioridade="alta", status=StatusAviso.PUBLICADO,
        criado_por=prof_a.usuario_id, publicado_em=agora,
    )
    aviso_arquivado = Aviso(
        titulo="Comunicado antigo", mensagem="Nao vigente", tipo="geral",
        prioridade="baixa", status=StatusAviso.ARQUIVADO,
        criado_por=prof_a.usuario_id, publicado_em=agora,
    )
    session.add_all([aviso_lido, aviso_feriado, aviso_arquivado])
    await session.flush()

    session.add_all([
        AvisoDestinatario(aviso_id=aviso_lido.id, usuario_id=ana.id, lido_em=agora),
        AvisoDestinatario(aviso_id=aviso_feriado.id, usuario_id=ana.id, lido_em=None),
        AvisoDestinatario(aviso_id=aviso_feriado.id, usuario_id=bruno.id, lido_em=None),
        AvisoDestinatario(aviso_id=aviso_feriado.id, usuario_id=sem_filho.id, lido_em=None),
        AvisoDestinatario(aviso_id=aviso_arquivado.id, usuario_id=ana.id, lido_em=None),
    ])

    await session.commit()
    return {
        "ana": ana, "bruno": bruno, "sem_filho": sem_filho,
        "maria": maria, "maria2": maria2, "pedro": pedro, "carlos": carlos,
        "prof_a": prof_a, "prof_b": prof_b,
        "turma_maria": turma_maria, "turma_outra": turma_outra,
        "aviso_feriado": aviso_feriado, "aviso_lido": aviso_lido,
    }


# ===========================================================================
# RESPONSÁVEL — escopo
# ===========================================================================
@pytest.mark.asyncio
async def test_responsavel_consulta_o_proprio_filho(session, cenario):
    cliente = OllamaFalso("A última nota da Maria foi 6,00 em Matemática.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )

    assert resp.codigo == "ok"
    assert resp.intencao == "notas_aluno_ultima"
    contexto = cliente.contexto
    assert "6,00" in contexto
    # Nada do outro responsável e nada do outro filho da Ana.
    assert "3,00" not in contexto
    assert "2,00" not in contexto
    assert "Pedro" not in contexto
    assert "Carlos" not in contexto
    assert "Maria Costa" not in contexto
    assert resp.alunos_autorizados == [cenario["maria"].id]


@pytest.mark.asyncio
async def test_responsavel_nao_acessa_aluno_de_outro_responsavel(session, cenario):
    """O caso clássico de vazamento: deve RECUSAR, sem consultar o global."""
    cliente = OllamaFalso("O Pedro tem 3,00.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota do Pedro Alves?", nome="Ana",
    )

    assert resp.codigo == "escopo_nao_resolvido"
    assert "3,00" not in resp.resposta
    # Recusa ANTES de chamar o modelo: não se gasta inferência para dizer "não".
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_responsavel_nao_acessa_homonimo_de_outro_filho(session, cenario):
    """'Maria Souza' é da Ana; 'Carlos Souza' é do Bruno. Ambos são 'Souza'."""
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota do Carlos Souza?", nome="Ana",
    )
    assert resp.codigo == "escopo_nao_resolvido"
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_ambiguidade_de_primeiro_nome_nao_e_adivinhada(session, cenario):
    """Ana tem Maria Souza e Maria Costa: 'Maria' sozinho precisa desambiguar."""
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria?", nome="Ana",
    )
    assert resp.codigo == "escopo_nao_resolvido"
    assert "Maria Souza" in resp.resposta and "Maria Costa" in resp.resposta
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_responsavel_consulta_filho_pelo_primeiro_nome(session, cenario):
    """Bruno tem Pedro e Carlos: 'do Pedro' precisa resolver, sem desambiguar.

    Antes o extrator só aceitava duas ou mais palavras capitalizadas, então
    um responsável com filhos de nomes diferentes era obrigado a digitar o
    sobrenome. A comparação é feita contra os nomes já autorizados, o que
    mantém a garantia de escopo.
    """
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["bruno"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota do Pedro?", nome="Bruno",
    )
    assert resp.codigo == "ok"
    contexto = cliente.contexto
    assert "Pedro Alves" in contexto
    assert "Carlos Souza" not in contexto
    assert "3,00" in contexto


@pytest.mark.asyncio
async def test_aluno_selecionado_fora_do_escopo_e_recusado(session, cenario):
    """Id adulterado no corpo da requisição não pode trocar o aluno consultado."""
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota do meu filho?",
        aluno_selecionado_id=cenario["pedro"].id,  # Pedro é do Bruno
    )
    assert resp.codigo == "escopo_nao_resolvido"
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_aluno_selecionado_dentro_do_escopo_e_aceito(session, cenario):
    cliente = OllamaFalso("A nota foi 6,00.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota do meu filho?",
        aluno_selecionado_id=cenario["maria"].id, nome="Ana",
    )
    assert resp.codigo == "ok"
    assert resp.alunos_autorizados == [cenario["maria"].id]


@pytest.mark.asyncio
async def test_responsavel_sem_filhos_recebe_recusa_sem_inferencia(session, cenario):
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["sem_filho"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota do meu filho?", nome="Solteiro",
    )
    assert resp.codigo == "escopo_nao_resolvido"
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_responsavel_ocorrencias_apenas_do_proprio_filho(session, cenario):
    cliente = OllamaFalso("Sim, há uma ocorrência.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "O meu filho tem alguma ocorrência?",
        aluno_selecionado_id=cenario["maria"].id, nome="Ana",
    )
    assert resp.codigo == "ok"
    contexto = cliente.contexto
    assert "Chegada atrasada" in contexto
    assert "Conflito" not in contexto  # ocorrência do Pedro, em outra turma


@pytest.mark.asyncio
async def test_responsavel_saldo_apenas_do_proprio_filho(session, cenario):
    cliente = OllamaFalso("O saldo é R$ 25,50.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Quanto há na carteira do meu filho?",
        aluno_selecionado_id=cenario["maria"].id, nome="Ana",
    )
    assert resp.codigo == "ok"
    assert "25,50" in cliente.contexto
    assert "5,00" not in cliente.contexto  # saldo do Pedro


@pytest.mark.asyncio
async def test_responsavel_avisos_nao_lidos_apenas_nao_lidos(session, cenario):
    cliente = OllamaFalso("Você tem 1 aviso não lido.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Quais avisos eu ainda não li?", nome="Ana",
    )
    assert resp.codigo == "ok"
    contexto = cliente.contexto
    assert "Feriado municipal" in contexto
    assert "Reuniao de pais" not in contexto  # já lido
    assert "Comunicado antigo" not in contexto  # arquivado


@pytest.mark.asyncio
async def test_responsavel_sem_avisos_pendentes_responde_sem_dados(session, cenario):
    cliente = OllamaFalso("ok")
    novo = await create_usuario(
        session, nome="Novo Resp", perfil=Perfil.RESPONSAVEL,
    )
    await session.commit()
    resp = await perguntar(
        session, cliente, novo.id, Perfil.RESPONSAVEL,
        "Quais avisos eu ainda não li?", nome="Novo",
    )
    assert resp.codigo == "sem_dados"
    assert cliente.chamadas == []


# ===========================================================================
# PROFESSOR — escopo por alocação
# ===========================================================================
@pytest.mark.asyncio
async def test_professor_ve_apenas_alunos_das_suas_turmas(session, cenario):
    cliente = OllamaFalso("Maria está abaixo da média.")
    resp = await perguntar(
        session, cliente, cenario["prof_a"].usuario_id, Perfil.PROFESSOR,
        "Quais alunos da minha turma estão abaixo da média?", nome="Prof A",
    )
    assert resp.codigo == "ok"
    contexto = cliente.contexto
    assert "Maria Souza" in contexto
    assert "Pedro" not in contexto
    assert "Carlos" not in contexto


@pytest.mark.asyncio
async def test_professor_nao_ve_turma_de_outro_professor(session, cenario):
    cliente = OllamaFalso("ok")
    await perguntar(
        session, cliente, cenario["prof_b"].usuario_id, Perfil.PROFESSOR,
        "Quais alunos da minha turma estão abaixo da média?", nome="Prof B",
    )
    contexto = cliente.contexto
    assert "Maria Souza" not in contexto
    assert "Pedro Alves" in contexto
    assert "Carlos Souza" in contexto


@pytest.mark.asyncio
async def test_professor_sem_alocacao_nao_consulta_nada(session, cenario):
    cliente = OllamaFalso("ok")
    prof_sem_turma = await create_professor(session)
    await session.commit()
    resp = await perguntar(
        session, cliente, prof_sem_turma.usuario_id, Perfil.PROFESSOR,
        "Quais alunos da minha turma estão abaixo da média?", nome="Prof C",
    )
    assert resp.codigo == "sem_dados"
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_professor_ocorrencias_pendentes_da_sua_turma(session, cenario):
    cliente = OllamaFalso("Há 1 ocorrência em aberto.")
    resp = await perguntar(
        session, cliente, cenario["prof_a"].usuario_id, Perfil.PROFESSOR,
        "Tenho alguma ocorrência pendente?", nome="Prof A",
    )
    assert resp.codigo == "ok"
    contexto = cliente.contexto
    assert "Chegada atrasada" in contexto
    assert "Conflito" not in contexto


# ===========================================================================
# SECRETARIA / ADMIN
# ===========================================================================
@pytest.mark.asyncio
async def test_secretaria_conta_matriculas(session, cenario):
    cliente = OllamaFalso("Há 3 alunos matriculados.")
    secretaria = await create_usuario(session, nome="Sec", perfil=Perfil.SECRETARIA)
    await session.commit()
    resp = await perguntar(
        session, cliente, secretaria.id, Perfil.SECRETARIA,
        "Quantos alunos estão matriculados?", nome="Secretaria",
    )
    assert resp.codigo == "ok"
    # Agregado: nenhum nome de aluno no contexto.
    assert "Maria Souza" not in cliente.contexto
    assert "3" in cliente.contexto


@pytest.mark.asyncio
async def test_admin_avisos_pendentes_filtram_por_aviso_citado(session, cenario):
    cliente = OllamaFalso("2 responsáveis não visualizaram.")
    admin = await create_usuario(session, nome="Admin", perfil=Perfil.ADMIN)
    await session.commit()
    resp = await perguntar(
        session, cliente, admin.id, Perfil.ADMIN,
        "Quais responsáveis não visualizaram o aviso do Feriado municipal?",
        nome="Admin",
    )
    assert resp.codigo == "ok"
    contexto = cliente.contexto
    assert "Feriado municipal" in contexto
    assert "Reuniao de pais" not in contexto  # outro aviso, fora do filtro
    assert "Comunicado antigo" not in contexto  # arquivado


# ===========================================================================
# Allowlist e intenções não reconhecidas
# ===========================================================================
@pytest.mark.asyncio
async def test_responsavel_nao_pede_dado_administrativo(session, cenario):
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Quantos alunos estão matriculados?", nome="Ana",
    )
    assert resp.codigo == "intencao_nao_permitida"
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_professor_nao_pede_dado_de_filho(session, cenario):
    """Pergunta de outro perfil é recusada SEM chamar o modelo.

    O código é `intencao_nao_reconhecida` (e não `intencao_nao_permitida`) de
    propósito: revelar "essa pergunta existe, mas é de outro perfil" já seria
    dar uma pista sobre a capacidade dos demais. O usuário recebe "não entendi"
    mais as sugestões do SEU perfil — que é a informação útil.
    """
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["prof_a"].usuario_id, Perfil.PROFESSOR,
        "Qual foi a última nota do meu filho?", nome="Prof A",
    )
    assert resp.codigo == "intencao_nao_reconhecida"
    assert cliente.chamadas == []
    # As sugestões oferecidas são só as do perfil dele.
    assert "última nota do meu filho" not in " ".join(resp.sugestoes)
    assert resp.sugestoes


@pytest.mark.asyncio
async def test_cantineiro_nao_acessa_nada(session, cenario):
    cliente = OllamaFalso("ok")
    cantineiro = await create_usuario(
        session, nome="Cantina", perfil=Perfil.CANTINEIRO,
    )
    await session.commit()
    resp = await perguntar(
        session, cliente, cantineiro.id, Perfil.CANTINEIRO,
        "Qual foi a última nota do meu filho?", nome="Cantineiro",
    )
    assert resp.codigo == "intencao_nao_reconhecida"
    assert cliente.chamadas == []


@pytest.mark.asyncio
async def test_pergunta_fora_do_assistente_responde_sugestoes(session, cenario):
    cliente = OllamaFalso("ok")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual a melhor pizza de São Paulo?", nome="Ana",
    )
    assert resp.codigo == "intencao_nao_reconhecida"
    assert resp.sugestoes  # o usuário recebe caminhos permitidos
    assert cliente.chamadas == []


# ===========================================================================
# Privacidade do contexto
# ===========================================================================
@pytest.mark.asyncio
async def test_contexto_nao_contem_dados_sensiveis(session, cenario):
    cliente = OllamaFalso("A nota foi 6,00.")
    await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )
    contexto = cliente.contexto
    # CPF de nenhum aluno.
    assert "11111111111" not in contexto
    assert "22222222222" not in contexto
    # Schema / SQL / nomes de coluna.
    for termo in ("select ", " from ", "aluno_id", "usuario_id", "cpf", "/api/v1"):
        assert termo not in contexto.lower()


@pytest.mark.asyncio
async def test_contexto_nao_revela_credenciais_nem_dsn(session, cenario):
    cliente = OllamaFalso("ok")
    await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )
    contexto = cliente.contexto.lower()
    for termo in ("postgresql", "password", "senha", "jwt", "secret", "epass123"):
        assert termo not in contexto


# ===========================================================================
# Guardrails
# ===========================================================================
@pytest.mark.asyncio
async def test_guardrail_corta_numero_inventado_pelo_modelo(session, cenario):
    """Contexto tem 8,50; o modelo 'lembra' de 9,75 -> resposta é substituída."""
    cliente = OllamaFalso("A nota foi 9,75 em Matemática.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )
    assert "9,75" not in resp.resposta
    # A troca avisa o usuário sem dizer por quê: "não encontrei" e "não
    # consegui confirmar" são o mesmo produto — a Atena prefere admitir que não
    # tem a informação a dizer que o modelo errou.
    assert "não consegui confirmar" in resp.resposta.lower()
    assert resp.alertas_guardrails  # o bloqueio fica registrado para auditoria


@pytest.mark.asyncio
async def test_guardrail_aceita_reformatacao_equivalente(session, cenario):
    """6,00 no contexto, '6.0' na resposta: é o mesmo número, não é alucinação."""
    cliente = OllamaFalso("A nota da Maria foi 6.0.")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )
    assert resp.alertas_guardrails == []
    assert "6.0" in resp.resposta


@pytest.mark.asyncio
async def test_guardrail_corta_vazamento_de_schema(session, cenario):
    cliente = OllamaFalso("Consigo fazer SELECT * FROM notas WHERE aluno_id = ...")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )
    assert "select" not in resp.resposta.lower()
    assert resp.alertas_guardrails


@pytest.mark.asyncio
async def test_guardrail_corta_tentativa_de_revelar_prompt(session, cenario):
    cliente = OllamaFalso("Meus dados autorizada são: regras inegociaveis...")
    resp = await perguntar(
        session, cliente, cenario["ana"].id, Perfil.RESPONSAVEL,
        "Qual foi a última nota da Maria Souza?", nome="Ana",
    )
    assert "regras inegociaveis" not in resp.resposta.lower()
    assert resp.alertas_guardrails


# ===========================================================================
# Resiliência: falha da IA não derruba o SGE
# ===========================================================================
@pytest.mark.asyncio
async def test_ia_indisponivel_vira_excecao_de_dominio(session, cenario):
    """A falha do Ollama sai como erro do módulo de IA, não como 500 do SGE."""
    from app.modules.ai.exceptions import IADisponivelErro

    class ClienteQuebrado(OllamaFalso):
        async def chat(self, mensagens, **_kwargs):
            raise IADisponivelErro()

    with pytest.raises(IADisponivelErro) as excinfo:
        await perguntar(
            session, ClienteQuebrado(), cenario["ana"].id, Perfil.RESPONSAVEL,
            "Qual foi a última nota da Maria Souza?", nome="Ana",
        )
    assert excinfo.value.status_code == 503
    assert excinfo.value.code == "ia_indisponivel"


@pytest.mark.asyncio
async def test_sge_continua_funcionando_com_a_ia_quebrada(client, session, cenario):
    """Independência real: o health do SGE não sabe que a IA existe."""
    assert (await client.get("/health")).status_code == 200
