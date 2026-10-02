from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, NotFound, ValidationError
from app.modules.document_requests.models import SolicitacaoDocumento
from app.modules.document_requests.repository import SolicitacaoDocumentoRepository
from app.modules.document_requests.schemas import (
    SolicitacaoDocumentoResponse,
)
from app.modules.students.models import Aluno, ResponsavelAluno
from app.shared.enums import StatusSolicitacaoDocumento, TipoDocumento

# Status que o responsável pode cancelar: um pedido já atendido ou recusado
# não faz sentido ser cancelado pelo solicitante.
CANCELAVEIS = {
    StatusSolicitacaoDocumento.PENDENTE,
    StatusSolicitacaoDocumento.EM_ANALISE,
}

# Status finais: a secretaria não deve alterá-los depois.
FINAIS = {
    StatusSolicitacaoDocumento.CONCLUIDA,
    StatusSolicitacaoDocumento.RECUSADA,
    StatusSolicitacaoDocumento.CANCELADA,
}


def _para_response(solicitacao: SolicitacaoDocumento) -> SolicitacaoDocumentoResponse:
    return SolicitacaoDocumentoResponse(
        id=solicitacao.id,
        aluno_id=solicitacao.aluno_id,
        aluno_nome=getattr(solicitacao.aluno, "nome", None),
        tipo=solicitacao.tipo,
        status=solicitacao.status,
        observacoes=solicitacao.observacoes,
        resposta=solicitacao.resposta,
        documento_url=solicitacao.documento_url,
        atendido_em=solicitacao.atendido_em,
        created_at=solicitacao.created_at,
        updated_at=solicitacao.updated_at,
    )


class SolicitacaoDocumentoService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SolicitacaoDocumentoRepository(session)
        self._session = session

    async def _aluno_do_responsavel(
        self, responsavel_id: uuid.UUID, aluno_id: uuid.UUID
    ) -> Aluno:
        """Bloqueia o IDOR: só quem é responsável pode pedir para o próprio filho.

        Devolve o `Aluno` em vez de só validar. O nome é Needed na resposta e,
        num objeto recém-criado, o relationship `aluno` não está populado ainda:
        tocá-lo dispararia lazy load, e IO síncrono fora de `await` estoura
        `MissingGreenlet`. Os testes não pegavam isso porque o `Aluno` do fixture
        já vivia no identity map da mesma sessão; em produção ele não carrega.
        """
        result = await self._session.execute(
            select(Aluno)
            .join(ResponsavelAluno, ResponsavelAluno.aluno_id == Aluno.id)
            .where(
                ResponsavelAluno.responsavel_id == responsavel_id,
                Aluno.id == aluno_id,
            )
            .limit(1)
        )
        aluno = result.scalar_one_or_none()
        if aluno is None:
            raise Forbidden("Você não é responsável por este aluno")
        return aluno

    async def criar(
        self,
        responsavel_id: uuid.UUID,
        aluno_id: uuid.UUID,
        tipo: TipoDocumento,
        observacoes: str | None,
    ) -> SolicitacaoDocumentoResponse:
        aluno = await self._aluno_do_responsavel(responsavel_id, aluno_id)

        texto = (observacoes or "").strip() or None
        if tipo == TipoDocumento.OUTRO and not texto:
            raise ValidationError("Descreva o documento que deseja solicitar")
        if texto and len(texto) > 1000:
            raise ValidationError("Observações devem ter no máximo 1000 caracteres")

        # Evita pedido duplicado de algo que ainda está em aberto.
        pendentes = await self._repo.listar_por_responsavel(responsavel_id)
        for existente in pendentes:
            if (
                existente.aluno_id == aluno_id
                and existente.tipo == tipo
                and existente.status in CANCELAVEIS
            ):
                raise ValidationError("Já existe uma solicitação deste documento em aberto")

        solicitacao = SolicitacaoDocumento(
            responsavel_id=responsavel_id,
            aluno_id=aluno_id,
            tipo=tipo,
            status=StatusSolicitacaoDocumento.PENDENTE,
            observacoes=texto,
        )
        solicitacao.aluno = aluno
        await self._repo.create(solicitacao)
        return _para_response(solicitacao)

    async def listar_minhas(
        self,
        responsavel_id: uuid.UUID,
        status: StatusSolicitacaoDocumento | None = None,
    ) -> list[SolicitacaoDocumentoResponse]:
        itens = await self._repo.listar_por_responsavel(responsavel_id, status)
        return [_para_response(item) for item in itens]

    async def listar_todas(
        self,
        status: StatusSolicitacaoDocumento | None = None,
    ) -> list[SolicitacaoDocumentoResponse]:
        itens = await self._repo.listar_todas(status)
        return [_para_response(item) for item in itens]

    async def cancelar(
        self,
        responsavel_id: uuid.UUID,
        solicitacao_id: uuid.UUID,
    ) -> SolicitacaoDocumentoResponse:
        solicitacao = await self._repo.get_by_id(solicitacao_id)
        if solicitacao is None:
            raise NotFound("Solicitação não encontrada")
        if solicitacao.responsavel_id != responsavel_id:
            raise Forbidden("Você não pode cancelar esta solicitação")
        if solicitacao.status not in CANCELAVEIS:
            raise ValidationError("Esta solicitação não pode mais ser cancelada")

        solicitacao.status = StatusSolicitacaoDocumento.CANCELADA
        solicitacao.atendido_em = datetime.now(UTC)
        return _para_response(await self._repo.update(solicitacao))

    async def responder(
        self,
        solicitacao_id: uuid.UUID,
        status: StatusSolicitacaoDocumento,
        resposta: str | None,
        documento_url: str | None,
        atendente_id: uuid.UUID,
    ) -> SolicitacaoDocumentoResponse:
        solicitacao = await self._repo.get_by_id(solicitacao_id)
        if solicitacao is None:
            raise NotFound("Solicitação não encontrada")
        if solicitacao.status in FINAIS:
            raise ValidationError("Esta solicitação já está encerrada")
        if status == StatusSolicitacaoDocumento.CANCELADA:
            raise ValidationError("Use o cancelamento para encerrar o pedido")

        solicitacao.status = status
        solicitacao.resposta = (resposta or "").strip() or None
        solicitacao.documento_url = (documento_url or "").strip() or None
        solicitacao.atendido_por = atendente_id
        solicitacao.atendido_em = datetime.now(UTC)
        return _para_response(await self._repo.update(solicitacao))
