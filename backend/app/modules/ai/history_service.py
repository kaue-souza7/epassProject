"""Regras de negócio do histórico da Atena (Fase 5).

Duas responsabilidades, e só elas:

1. Criar/persistir a conversa e suas mensagens;
2. Entregar ao prompt um recorte PEQUENO e delimitado do histórico.

O recorte é limitado por dois tetos independentes (turnos e caracteres) porque
o modelo é pequeno: um histórico longo degrada o qwen3:1.7b e ainda aumenta o
risco de o modelo "responder à conversa antiga" em vez de responder à pergunta
atual. A pergunta atual sempre vem por último e fora do bloco do histórico.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.ai.exceptions import AIException
from app.modules.ai.history_models import Conversa, Mensagem
from app.modules.ai.history_repository import ConversaRepository, MensagemRepository
from app.shared.enums import PapelMensagemIA

logger = logging.getLogger(__name__)

# Turnos (pares pergunta/resposta) enviados ao modelo. 3 é o suficiente para
# "e a nota de Matemática?" funcionar sem poluir o contexto do 1.7b.
TURNOS_POR_PADRAO = 3


class ConversaNaoEncontradaErro(AIException):
    """A conversa não existe OU é de outra pessoa.

    A mensagem é a mesma nos dois casos de propósito: responder "403" ou "esta
    conversa é de outro usuário" confirmaria que o id existe e transformaria o
    endpoint em enumerador de conversas alheias.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Conversa não encontrada.", status_code=404,
            code="conversa_nao_encontrada",
        )


@dataclass
class HistoricoConversa:
    """Histórico já recortado, pronto para virar bloco de prompt."""

    mensagens: list[dict[str, str]]

    @property
    def vazio(self) -> bool:
        return not self.mensagens


class HistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversas = ConversaRepository(session)
        self._mensagens = MensagemRepository(session)

    # ------------------------------------------------------------------
    # Conversa
    # ------------------------------------------------------------------
    async def commit(self) -> None:
        """Confirma a transação. O router usa em vez de tocar em `_session`."""
        await self._session.commit()

    async def obter_ou_criar(
        self,
        usuario_id: uuid.UUID,
        conversa_id: uuid.UUID | None,
        titulo: str | None = None,
    ) -> Conversa | None:
        """Devolve a conversa do usuário, ou `None` se o id é de outra pessoa.

        O `None` é intencional: quem chama transforma em 404, sem revelar se o
        id existe. Passar `conversa_id=None` cria uma conversa nova.
        """
        if conversa_id is None:
            return await self._conversas.criar(usuario_id, titulo)
        return await self._conversas.obter(conversa_id, usuario_id)

    async def exigir_conversa(
        self, conversa_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> Conversa:
        """Como `obter_ou_criar`, mas levanta 404 em vez de devolver `None`.

        Usado na gravação: o dono é conferido na MESMA operação que insere as
        mensagens, para não existir caminho que grave em conversa alheia.
        """
        conversa = await self._conversas.obter(conversa_id, usuario_id)
        if conversa is None:
            raise ConversaNaoEncontradaErro
        return conversa

    # ------------------------------------------------------------------
    # Mensagens
    # ------------------------------------------------------------------
    async def registrar_pergunta(
        self, conversa_id: uuid.UUID, texto: str,
    ) -> Mensagem:
        return await self._mensagens.adicionar(
            conversa_id, PapelMensagemIA.USUARIO, texto,
        )

    async def registrar_resposta(
        self,
        conversa_id: uuid.UUID,
        texto: str,
        *,
        intencao: str | None = None,
        codigo: str | None = None,
    ) -> Mensagem:
        return await self._mensagens.adicionar(
            conversa_id,
            PapelMensagemIA.ASSISTENTE,
            texto,
            intencao=intencao,
            codigo=codigo,
        )

    async def registrar_turno(
        self,
        conversa: Conversa,
        pergunta: str,
        resposta: str,
        *,
        intencao: str | None = None,
        codigo: str | None = None,
    ) -> tuple[Mensagem, Mensagem]:
        """Grava pergunta + resposta e dá um título à conversa na 1ª troca."""
        await self._conversas.tocar(conversa.id)
        m_user = await self.registrar_pergunta(conversa.id, pergunta)
        m_assistant = await self.registrar_resposta(
            conversa.id, resposta, intencao=intencao, codigo=codigo,
        )
        if not conversa.titulo:
            await self._conversas.definir_titulo(conversa.id, _titulo_de(pergunta))
        return m_user, m_assistant

    async def registrar_turno_do_usuario(
        self,
        conversa_id: uuid.UUID,
        usuario_id: uuid.UUID,
        pergunta: str,
        resposta: str,
        *,
        intencao: str | None = None,
        codigo: str | None = None,
    ) -> tuple[Mensagem, Mensagem]:
        """Grava o turno conferindo o dono na mesma operação (404 se alheia)."""
        conversa = await self.exigir_conversa(conversa_id, usuario_id)
        return await self.registrar_turno(
            conversa, pergunta, resposta, intencao=intencao, codigo=codigo,
        )

    async def listar_mensagens(
        self, conversa_id: uuid.UUID, limite: int | None = None,
    ) -> list[Mensagem]:
        if limite is None:
            return await self._mensagens.listar(conversa_id)
        return await self._mensagens.listar(conversa_id, limite)

    async def historico_para_prompt(
        self, conversa_id: uuid.UUID, turnos: int | None = None,
    ) -> HistoricoConversa:
        """Recorte do histórico para o prompt, já limitado em turnos e bytes.

        Descarta do começo o que ultrapassar o orçamento de caracteres: em uma
        conversa longa, o trecho final é o que importa para continuidade.
        """
        n_turnos = turnos if turnos is not None else settings.AI_HISTORY_TURNS
        if n_turnos <= 0:
            return HistoricoConversa([])

        mensagens = await self._mensagens.ultimas(conversa_id, n_turnos * 2)
        if not mensagens:
            return HistoricoConversa([])

        itens = [
            {"papel": "usuario" if m.papel is PapelMensagemIA.USUARIO else "assistente",
             "texto": m.conteudo}
            for m in mensagens
        ]

        # Orçamento de caracteres, cortando do começo (o mais recente fica).
        teto = settings.AI_HISTORY_MAX_CHARS
        total = sum(len(i["texto"]) for i in itens)
        while itens and total > teto:
            total -= len(itens.pop(0)["texto"])

        if not itens:
            return HistoricoConversa([])
        if len(itens) < len(mensagens):
            logger.info(
                "AI: histórico truncado para %d mensagens (teto de %d chars)",
                len(itens), teto,
            )
        return HistoricoConversa(itens)


def _titulo_de(pergunta: str) -> str:
    """Título da conversa a partir da primeira pergunta, sem chamar o modelo."""
    limpo = " ".join(pergunta.split()).strip()
    if len(limpo) <= 60:
        return limpo
    return f"{limpo[:57].rstrip()}..."
