import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.classes.schemas import TurmaRequest, TurmaResponse, TurmaUpdateRequest
from app.modules.classes.service import TurmaService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def list_turmas(
    only_active: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = TurmaService(session)
    items, total = await service.search_paginated(
        only_active=only_active, page=page, size=size,
    )
    return PaginatedResponse(
        items=[TurmaResponse.model_validate(t).model_dump() for t in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{id}",
    response_model=TurmaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def get_turma(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> TurmaResponse:
    service = TurmaService(session)
    turma = await service.get_by_id(id)
    return TurmaResponse.model_validate(turma)


@router.post(
    "",
    response_model=TurmaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def create_turma(
    body: TurmaRequest, session: AsyncSession = Depends(get_session),
) -> TurmaResponse:
    service = TurmaService(session)
    turma = await service.create(body)
    return TurmaResponse.model_validate(turma)


@router.put(
    "/{id}",
    response_model=TurmaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def update_turma(
    id: uuid.UUID, body: TurmaUpdateRequest, session: AsyncSession = Depends(get_session),
) -> TurmaResponse:
    service = TurmaService(session)
    turma = await service.update(id, body)
    return TurmaResponse.model_validate(turma)
