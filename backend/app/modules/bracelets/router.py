import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.bracelets.schemas import (
    BraceletDetailResponse,
    BraceletRequest,
    BraceletResponse,
    BraceletUpdateRequest,
    StatusBraceletUpdateResponse,
    VincularAlunoRequest,
)
from app.modules.bracelets.service import BraceletService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/bracelets", tags=["bracelets"])


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def list_bracelets(
    status: str | None = Query(None),
    tem_aluno: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = BraceletService(session)
    items, total = await service.search_paginated(
        status=status, tem_aluno=tem_aluno, page=page, size=size,
    )
    return PaginatedResponse(
        items=[BraceletDetailResponse(
            id=b.id,
            uid=b.uid,
            codigo=b.codigo,
            aluno_id=b.aluno_id,
            status=b.status,
            created_at=b.created_at,
            updated_at=b.updated_at,
            aluno_nome=b.aluno.nome if b.aluno else None,
        ).model_dump() for b in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{id}",
    response_model=BraceletDetailResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def get_bracelet(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> BraceletDetailResponse:
    service = BraceletService(session)
    bracelet = await service.get_by_id(id)
    return BraceletDetailResponse(
        id=bracelet.id,
        uid=bracelet.uid,
        codigo=bracelet.codigo,
        aluno_id=bracelet.aluno_id,
        status=bracelet.status,
        created_at=bracelet.created_at,
        updated_at=bracelet.updated_at,
        aluno_nome=bracelet.aluno.nome if bracelet.aluno else None,
    )


@router.post(
    "",
    response_model=BraceletResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def create_bracelet(
    body: BraceletRequest, session: AsyncSession = Depends(get_session),
) -> BraceletResponse:
    service = BraceletService(session)
    bracelet = await service.create(body)
    return BraceletResponse.model_validate(bracelet)


@router.patch(
    "/{id}",
    response_model=BraceletResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def update_bracelet(
    id: uuid.UUID, body: BraceletUpdateRequest, session: AsyncSession = Depends(get_session),
) -> BraceletResponse:
    service = BraceletService(session)
    bracelet = await service.update(id, body)
    return BraceletResponse.model_validate(bracelet)


@router.patch(
    "/{id}/link",
    response_model=BraceletResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def vincular_aluno(
    id: uuid.UUID, body: VincularAlunoRequest, session: AsyncSession = Depends(get_session),
) -> BraceletResponse:
    service = BraceletService(session)
    bracelet = await service.vincular_aluno(id, body)
    return BraceletResponse.model_validate(bracelet)


@router.patch(
    "/{id}/unlink",
    response_model=BraceletResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def desvincular_aluno(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> BraceletResponse:
    service = BraceletService(session)
    bracelet = await service.desvincular_aluno(id)
    return BraceletResponse.model_validate(bracelet)


@router.patch(
    "/{id}/block",
    response_model=StatusBraceletUpdateResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def bloquear_bracelet(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> StatusBraceletUpdateResponse:
    service = BraceletService(session)
    bracelet = await service.bloquear(id)
    return StatusBraceletUpdateResponse(
        bracelet_id=bracelet.id,
        status=bracelet.status,
        mensagem="Pulseira bloqueada com sucesso",
    )


@router.patch(
    "/{id}/unblock",
    response_model=StatusBraceletUpdateResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def desbloquear_bracelet(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> StatusBraceletUpdateResponse:
    service = BraceletService(session)
    bracelet = await service.desbloquear(id)
    return StatusBraceletUpdateResponse(
        bracelet_id=bracelet.id,
        status=bracelet.status,
        mensagem="Pulseira desbloqueada com sucesso",
    )
