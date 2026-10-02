"""Context builders — resolução de intenção → dados autorizados.

REGRA DE OURO DESTE PACOTE
--------------------------
A escolha do builder é feita pelo NOME DA INTENÇÃO, e cada builder faz a
autorização na raiz da sua consulta. Não existe caminho "genérico" que aceite
uma tabela ou um filtro vindo de fora: isso seria justamente a porta que o
LLM usaria para escapar do escopo.

POR QUE UM REGISTRO (E NÃO UMA CADEIA DE `if`)
-----------------------------------------------
São ~45 intenções. Numa cadeia de `if`, o dispatcher cresceria até passar do
tamanho dos builders que ele chama, e o dia que uma intenção fosse adicionada
no meio da cadeia esquecendo um ramo, ela cairia no `raise` final e viraria
"não tenho acesso" — falha silenciosa, do tipo que só aparece em produção.

O registro resolve os dois problemas de uma vez:

  1. `REGISTRO` é a lista completa e explícita do que existe, e
     `verificar_cobertura()` (rodada nos testes) acusa qualquer intenção sem
     builder ou builder sem intenção — antes do deploy, não em runtime.
  2. O dispatcher tem UM ramo só, que não pode esquecer nenhum caso.

ASSINATURA ÚNICA
----------------
Todo builder registrado recebe os MESMOS dois argumentos, mesmo os que não
usam ambos. A uniformidade aqui não é estética: é o que permite ao dispatcher
ser um `await REGISTRO[nome](session, ctx)`, sem uma única condição — e sem
`inspect.signature` em tempo de execução.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai import mensagens as textos
from app.modules.ai.context import cantina as _cantina
from app.modules.ai.context import coordenacao as _coordenacao
from app.modules.ai.context import professor as _professor
from app.modules.ai.context import responsavel as _responsavel
from app.modules.ai.context import secretaria as _secretaria
from app.modules.ai.context.base import AlunoNoEscopo, ResultadoContexto
from app.modules.ai.exceptions import IntencaoNaoPermitidaErro
from app.modules.ai.intent import ResultadoIntencao
from app.shared.enums import Perfil

__all__ = [
    "AlunoNoEscopo",
    "ResultadoContexto",
    "construir_contexto",
    "intencoes_do_perfil",
    "intencoes_sem_builder",
    "verificar_cobertura",
]


class Ctx:
    """Contexto da requisição, empacotado para os builders.

    Existe para eliminar a classe de bug mais perigosa deste módulo: builders
    com quatro parâmetros posicionais similarizados (`uuid.UUID`,
    `str | None`, `uuid.UUID | None`, `str`) trocados dois a dois. Isso compila,
    passa revisão visual e vaza escopo em produção. Com os campos nomeados, a
    troca não tem como acontecer.
    """

    __slots__ = ("resultado", "usuario_id", "perfil", "aluno_selecionado_id")

    def __init__(
        self,
        resultado: ResultadoIntencao,
        usuario_id: uuid.UUID,
        perfil: Perfil,
        aluno_selecionado_id: uuid.UUID | None,
    ) -> None:
        self.resultado = resultado
        self.usuario_id = usuario_id
        self.perfil = perfil
        self.aluno_selecionado_id = aluno_selecionado_id

    # Atalhos usados pela maioria dos builders.
    @property
    def nome_aluno(self) -> str | None:
        return self.resultado.nome_aluno

    @property
    def nome_turma(self) -> str | None:
        return self.resultado.nome_turma

    @property
    def mensagem(self) -> str:
        return self.resultado.mensagem_original

    @property
    def bimestre(self) -> int | None:
        return self.resultado.bimestre

    @property
    def disciplina(self) -> str | None:
        return self.resultado.nome_disciplina

    @property
    def nome_aviso(self) -> str | None:
        return self.resultado.nome_aviso


Builder = Callable[[AsyncSession, Ctx], Awaitable[ResultadoContexto]]


def _construir_registro() -> dict[str, Builder]:
    """Monta o mapa intenção → builder.

    Os lambdas são deliberadamente "burros": traduzem o `Ctx` para os
    parâmetros que o builder concreto espera. Toda a lógica de escopo continua
    dentro do builder, nunca aqui.
    """

    # --- responsável: escopo por aluno ---
    def _aluno_aluno(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(
                session, ctx.usuario_id, ctx.nome_aluno,
                ctx.aluno_selecionado_id, ctx.mensagem,
            )
        return _run

    def _aluno_bimestre(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(
                session, ctx.usuario_id, ctx.nome_aluno,
                ctx.aluno_selecionado_id, ctx.mensagem, bimestre=ctx.bimestre,
            )
        return _run

    def _aluno_disciplina(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(
                session, ctx.usuario_id, ctx.nome_aluno,
                ctx.aluno_selecionado_id, ctx.mensagem,
                bimestre=ctx.bimestre, disciplina=ctx.disciplina,
            )
        return _run

    def _so_responsavel(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(session, ctx.usuario_id)
        return _run

    # --- professor: escopo por usuário (as alocações são o filtro) ---
    def _prof(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(session, ctx.usuario_id)
        return _run

    def _prof_turma(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(session, ctx.usuario_id, ctx.nome_turma, ctx.mensagem)
        return _run

    def _prof_turma_bimestre(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(
                session, ctx.usuario_id, ctx.nome_turma, ctx.mensagem,
                bimestre=ctx.bimestre,
            )
        return _run

    # --- institucional ---
    def _inst(fn):
        async def _run(session: AsyncSession, _ctx: Ctx) -> ResultadoContexto:
            return await fn(session)
        return _run

    def _inst_com_aviso(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(session, ctx.nome_aviso)
        return _run

    def _institucional_agenda(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(session, ctx.usuario_id, ctx.perfil)
        return _run

    def _cantina_aluno(fn):
        async def _run(session: AsyncSession, ctx: Ctx) -> ResultadoContexto:
            return await fn(session, ctx.nome_aluno, ctx.mensagem)
        return _run

    return {
        # ---------------- Responsável ----------------
        "notas_aluno_ultima": _aluno_aluno(_responsavel.notas_aluno_ultima),
        "media_aluno": _aluno_disciplina(_responsavel.media_aluno),
        "notas_aluno_historico": _aluno_disciplina(_responsavel.notas_aluno_historico),
        "boletim_aluno": _aluno_bimestre(_responsavel.boletim_aluno),
        "frequencia_aluno": _aluno_bimestre(_responsavel.frequencia_aluno),
        "ocorrencias_aluno": _aluno_aluno(_responsavel.ocorrencias_aluno),
        "avisos_nao_lidos": _so_responsavel(_responsavel.avisos_nao_lidos),
        "notificacoes_nao_lidas": _so_responsavel(_responsavel.notificacoes_nao_lidas),
        "respostas_aviso": _inst_com_aviso(_responsavel.respostas_aviso),
        "saldo_carteira": _aluno_aluno(_responsavel.saldo_carteira),
        "extrato_carteira": _aluno_aluno(_responsavel.extrato_carteira),
        "pedidos_cantina": _aluno_aluno(_responsavel.pedidos_cantina),
        "programacao_cantina": _aluno_aluno(_responsavel.programacao_cantina),
        "documentos_solicitacoes": _aluno_aluno(_responsavel.documentos_solicitacoes),
        "pulseira_aluno": _aluno_aluno(_responsavel.pulseira_aluno),
        "matricula_aluno": _aluno_aluno(_responsavel.matricula_aluno),
        "historico_escolar": _aluno_aluno(_responsavel.historico_escolar),

        # ---------------- Agenda (qualquer perfil) ----------------
        "agenda_eventos": _institucional_agenda(_responsavel.agenda_eventos),

        # ---------------- Professor ----------------
        "alunos_abaixo_media": _prof(_professor.alunos_abaixo_media),
        "ocorrencias_pendentes": _prof(_professor.ocorrencias_pendentes),
        "minhas_turmas": _prof(_professor.minhas_turmas),
        "lista_alunos_turma": _prof_turma(_professor.lista_alunos_turma),
        "avaliacoes_sem_notas": _prof_turma(_professor.avaliacoes_sem_notas),
        "media_disciplina_turma": _prof_turma_bimestre(_professor.media_disciplina_turma),
        "frequencia_turma": _prof_turma_bimestre(_professor.frequencia_turma),
        "avisos_turma": _prof_turma(_professor.avisos_turma),
        "prazos_boletim": _prof(_professor.prazos_boletim),
        "chamadas_recentes": _prof(_professor.chamadas_recentes),

        # ---------------- Secretaria / Admin ----------------
        "matriculas_contagem": _inst(_secretaria.matriculas_contagem),
        "alunos_sem_matricula": _inst(_secretaria.alunos_sem_matricula),
        "turmas_ocupacao": _inst(_secretaria.turmas_ocupacao),
        "alunos_por_serie": _inst(_secretaria.alunos_por_serie),
        "documentos_pendentes": _inst(_secretaria.documentos_pendentes),
        "ocorrencias_abertas": _inst(_secretaria.ocorrencias_abertas),
        "matriculas_recentes": _inst(_secretaria.matriculas_recentes),
        "professores_alocacoes": _inst(_secretaria.professores_alocacoes),
        "pedidos_cantina_pendentes": _inst(_secretaria.pedidos_cantina_pendentes),
        "estoque_baixo": _inst(_secretaria.estoque_baixo),
        "avisos_nao_lidos_por_responsavel": _inst_com_aviso(
            _secretaria.avisos_nao_lidos_por_responsavel,
        ),

        # ---------------- Coordenação ----------------
        "panorama_escolar": _inst(_coordenacao.panorama_escolar),
        "turmas_criticas": _inst(_coordenacao.turmas_criticas),
        "alunos_atencao_coordenacao": _inst(_coordenacao.alunos_atencao_coordenacao),

        # ---------------- Cantina ----------------
        "pedidos_cantina_hoje": _inst(_cantina.pedidos_cantina_hoje),
        "cardapio_cantina": _inst(_cantina.cardapio_cantina),
        "estoque_cantina": _inst(_cantina.estoque_cantina),
        "saldo_aluno_cantina": _cantina_aluno(_cantina.saldo_aluno_cantina),
    }


REGISTRO: dict[str, Builder] = _construir_registro()


async def construir_contexto(
    session: AsyncSession,
    resultado: ResultadoIntencao,
    usuario_id: uuid.UUID,
    perfil: Perfil,
    aluno_selecionado_id: uuid.UUID | None = None,
) -> ResultadoContexto:
    """Executa o builder da intenção classificada, já validada pela allowlist.

    `aluno_selecionado_id` vem do cliente (web/mobile) e só é usado se pertence
    ao escopo — a validação é feita dentro de `escolher_aluno`.
    """
    nome = resultado.intencao.nome
    builder = REGISTRO.get(nome)

    if builder is None:
        # Defence in depth: mesmo que uma intenção nova entre no catálogo sem
        # builder, ela NÃO vira uma consulta genérica — vira uma recusa
        # amigável. `verificar_coverage()` falha o teste antes de chegar aqui.
        raise IntencaoNaoPermitidaErro(textos.INTENCAO_NAO_PERMITIDA)

    ctx = Ctx(resultado, usuario_id, perfil, aluno_selecionado_id)
    return await builder(session, ctx)


def intencoes_do_perfil(perfil: Perfil) -> list[str]:
    """Nomes das intenções permitidas ao perfil (usado em testes e no /ai/health)."""
    from app.modules.ai.intent import INTENCOES

    return [i.nome for i in INTENCOES if perfil in i.perfis]


def intencoes_sem_builder() -> list[str]:
    """Intenções do catálogo sem builder correspondente (deve ser vazio)."""
    from app.modules.ai.intent import INTENCOES

    return [i.nome for i in INTENCOES if i.nome not in REGISTRO]


def builders_sem_intencao() -> list[str]:
    """Builders registrados que não correspondem a nenhuma intenção (vazio)."""
    from app.modules.ai.intent import INTENCOES

    return [nome for nome in REGISTRO if nome not in {i.nome for i in INTENCOES}]


def verificar_cobertura() -> None:
    """Falha alto se o catálogo e o registro divergirem.

    Roda nos testes. É a rede de segurança que substitui a cadeia de `if`:
    esquecer de cadastrar um builder é erro de build, não erro de produção.
    """
    sem_builder = intencoes_sem_builder()
    orfaos = builders_sem_intencao()
    problemas: list[str] = []
    if sem_builder:
        problemas.append(f"intenções sem builder: {sem_builder}")
    if orfaos:
        problemas.append(f"builders sem intenção: {orfaos}")
    if problemas:
        raise AssertionError("Cobertura de context builders inconsistente: " + "; ".join(problemas))
