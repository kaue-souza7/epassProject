"""Acesso ao histórico de conversas (Fase 5).

REGRA DE OURO DESTE ARQUIVO
---------------------------
`usuario_id` NUNCA vem do corpo da requisição: entra como argumento e é sempre
o do token. E todo método que recebe `conversa_id` inclui o dono no filtro:

    WHERE id = :conversa_id AND usuario_id = :usuario_id

Isso é o que impede IDOR. Passar o id de outra pessoa não retorna "403"
(código que confirma que o id existe) e sim `None`/404 indistinguível de "não
existe" — o atacante não consegue enumerar conversas alheias.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.history_models import Conversa, Mensagem
from app.shared.enums import PapelMensagemIA

# Quantas mensagens saem do banco por vez. Maior que o limite enviado ao modelo
# (ver `prompt.py`), de propósito: o teto do prompt é mais apertado porque conta
# também com o custo de contexto do qwen3:1.7b.
LIMITE_MENSAGENS = 100


class ConversaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self, usuario_id: uuid.UUID, titulo: str | None = None,
    ) -> Conversa:
        agora = datetime.now(UTC)
        conversa = Conversa(
            id=uuid.uuid4(),
            usuario_id=usuario_id,
            titulo=(titulo or None),
            criada_em=agora,
            atualizada_em=agora,
        )
        self._session.add(conversa)
        await self._session.flush()
        return conversa

    async def listar(
        self, usuario_id: uuid.UUID, limite: int = 50,
    ) -> list[Conversa]:
        result = await self._session.execute(
            select(Conversa)
            .where(Conversa.usuario_id == usuario_id)
            .order_by(Conversa.atualizada_em.desc())
            .limit(limite),
        )
        return list(result.scalars().all())

    async def obter(
        self, conversa_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> Conversa | None:
        """Busca JÁ filtrada pelo dono. `None` = não existe OU é de outro."""
        result = await self._session.execute(
            select(Conversa).where(
                Conversa.id == conversa_id,
                Conversa.usuario_id == usuario_id,
            ),
        )
        return result.scalar_one_or_none()

    async def contar_mensagens(
        self, conversa_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> int:
        result = await self._session.execute(
            select(func.count(Mensagem.id))
            .join(Conversa, Conversa.id == Mensagem.conversa_id)
            .where(
                Conversa.id == conversa_id,
                Conversa.usuario_id == usuario_id,
            ),
        )
        return int(result.scalar_one())

    async def tocar(self, conversa_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Conversa)
            .where(Conversa.id == conversa_id)
            .values(atualizada_em=datetime.now(UTC)),
        )
        await self._session.flush()

    async def definir_titulo(self, conversa_id: uuid.UUID, titulo: str) -> None:
        await self._session.execute(
            update(Conversa)
            .where(Conversa.id == conversa_id)
            .values(titulo=titulo[:200]),
        )
        await self._session.flush()

    async def excluir(
        self, conversa_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> bool:
        """Exclusão dura. As mensagens caem por CASCADE.

        Existe por decisão de privacidade: o usuário que pede para apagar uma
        conversa espera que o conteúdo seja realmente removido, não escondido.
        Devolve False quando o id não é dele (o chamador responde 404).
        """
        conversa = await self.obter(conversa_id, usuario_id)
        if conversa is None:
            return False
        await self._session.execute(delete(Conversa).where(Conversa.id == conversa_id))
        await self._session.flush()
        return True


class MensagemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def adicionar(
        self,
        conversa_id: uuid.UUID,
        papel: PapelMensagemIA,
        conteudo: str,
        *,
        intencao: str | None = None,
        codigo: str | None = None,
    ) -> Mensagem:
        mensagem = Mensagem(
            id=uuid.uuid4(),
            conversa_id=conversa_id,
            papel=papel,
            conteudo=conteudo[:8000],
            intencao=(intencao or None) if intencao else None,
            codigo=(codigo or None) if codigo else None,
            criado_em=datetime.now(UTC),
        )
        self._session.add(mensagem)
        await self._session.flush()
        return mensagem

    async def listar(
        self, conversa_id: uuid.UUID, limite: int = LIMITE_MENSAGENS,
    ) -> list[Mensagem]:
        """Lista as mensagens de uma conversa JÁ verificada como do usuário.

        Quem chama precisa ter passado por `ConversaRepository.obter`; o filtro
        de dono é verificado ali, na raiz, em vez de repetido aqui.
        """
        result = await self._session.execute(
            select(Mensagem)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.criado_em.asc(), Mensagem.id.asc())
            .limit(limite),
        )
        return list(result.scalars().all())

    async def ultimas(
        self, conversa_id: uuid.UUID, quantidade: int,
    ) -> list[Mensagem]:
        """As `quantidade` mensagens MAIS RECENTES, em ordem cronológica.

        Subquery com `ORDER BY ... DESC LIMIT`, e não `listar()` inteiro: assim
        uma conversa com 500 mensagens não carrega tudo para usar as últimas 6.
        """
        sub = (
            select(Mensagem.id)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.criado_em.desc(), Mensagem.id.desc())
            .limit(max(1, quantidade))
            .scalar_subquery()
        )
        result = await self._session.execute(
            select(Mensagem)
            .where(Mensagem.id.in_(sub))
            .order_by(Mensagem.criado_em.asc(), Mensagem.id.asc()),
        )
        return list(result.scalars().all())
