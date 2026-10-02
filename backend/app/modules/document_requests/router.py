from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.document_requests.schemas import (
    AtualizarSolicitacaoDocumentoRequest,
    CriarSolicitacaoDocumentoRequest,
    SolicitacaoDocumentoResponse,
)
from app.modules.document_requests.service import SolicitacaoDocumentoService
from app.shared.enums import Perfil, StatusSolicitacaoDocumento

router = APIRouter(prefix="/documentos/solicitacoes", tags=["documentos"])


@router.post("", response_model=SolicitacaoDocumentoResponse, status_code=201)
async def criar_solicitacao(
    body: CriarSolicitacaoDocumentoRequest,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> SolicitacaoDocumentoResponse:
    service = SolicitacaoDocumentoService(session)
    return await service.criar(
        responsavel_id=uuid.UUID(current_user["sub"]),
        aluno_id=body.aluno_id,
        tipo=body.tipo,
        observacoes=body.observacoes,
    )


@router.get("", response_model=list[SolicitacaoDocumentoResponse])
async def listar_minhas_solicitacoes(
    status: StatusSolicitacaoDocumento | None = Query(None),
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> list[SolicitacaoDocumentoResponse]:
    service = SolicitacaoDocumentoService(session)
    return await service.listar_minhas(uuid.UUID(current_user["sub"]), status)


@router.post("/{solicitacao_id}/cancelar", response_model=SolicitacaoDocumentoResponse)
async def cancelar_solicitacao(
    solicitacao_id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> SolicitacaoDocumentoResponse:
    service = SolicitacaoDocumentoService(session)
    return await service.cancelar(uuid.UUID(current_user["sub"]), solicitacao_id)


@router.get("/admin/todas", response_model=list[SolicitacaoDocumentoResponse])
async def listar_todas_solicitacoes(
    status: StatusSolicitacaoDocumento | None = Query(None),
    _current_user: dict = Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA)),
    session: AsyncSession = Depends(get_session),
) -> list[SolicitacaoDocumentoResponse]:
    service = SolicitacaoDocumentoService(session)
    return await service.listar_todas(status)


@router.patch("/admin/{solicitacao_id}", response_model=SolicitacaoDocumentoResponse)
async def responder_solicitacao(
    solicitacao_id: uuid.UUID,
    body: AtualizarSolicitacaoDocumentoRequest,
    current_user: dict = Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA)),
    session: AsyncSession = Depends(get_session),
) -> SolicitacaoDocumentoResponse:
    service = SolicitacaoDocumentoService(session)
    return await service.responder(
        solicitacao_id=solicitacao_id,
        status=body.status,
        resposta=body.resposta,
        documento_url=body.documento_url,
        atendente_id=uuid.UUID(current_user["sub"]),
    )
