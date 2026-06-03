from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.agenda.schemas import (
    EventoCreate,
    EventoDetalheResponse,
    EventoDestinatarioResponse,
    EventoResponse,
    EventoUpdate,
)
from app.modules.agenda.service import EventoService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/agenda/events", tags=["agenda"])


@router.post(
    "",
    response_model=EventoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def create_evento(
    body: EventoCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> EventoResponse:
    service = EventoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    evento = await service.criar(body, usuario_id, perfil)
    return EventoResponse.model_validate(evento)


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL))],
)
async def list_eventos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    data_inicio: datetime | None = Query(None),
    data_fim: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse:
    service = EventoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    items, total = await service.listar(
        usuario_id=usuario_id, perfil=perfil,
        page=page, size=size,
        data_inicio=data_inicio, data_fim=data_fim,
    )
    return PaginatedResponse(
        items=[EventoResponse.model_validate(e).model_dump() for e in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{id}",
    response_model=EventoDetalheResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL))],
)
async def get_evento(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> EventoDetalheResponse:
    service = EventoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    evento = await service.obter(id, usuario_id, perfil)
    destinatarios = await service._repo.get_destinatarios_by_evento(evento.id)
    return EventoDetalheResponse(
        evento=EventoResponse.model_validate(evento),
        destinatarios=[EventoDestinatarioResponse.model_validate(d) for d in destinatarios],
    )


@router.put(
    "/{id}",
    response_model=EventoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def update_evento(
    id: uuid.UUID,
    body: EventoUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> EventoResponse:
    service = EventoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    evento = await service.atualizar(id, body, usuario_id, perfil)
    return EventoResponse.model_validate(evento)


@router.delete(
    "/{id}",
    status_code=204,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def delete_evento(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    service = EventoService(session)
    usuario_id = uuid.UUID(current_user["sub"])
    perfil = Perfil(current_user["perfil"])
    await service.excluir(id, usuario_id, perfil)
