import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.allocations.schemas import AlocacaoCreate, AlocacaoEncerrar, AlocacaoResponse
from app.modules.allocations.service import AlocacaoService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/allocations", tags=["allocations"])


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def list_alocacoes(
    turma_id: uuid.UUID | None = Query(None),
    professor_id: uuid.UUID | None = Query(None),
    only_active: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse:
    service = AlocacaoService(session)

    if current_user["perfil"] == Perfil.PROFESSOR:
        professor_filter = current_user["sub"]
        turma_filter = None
    else:
        professor_filter = professor_id
        turma_filter = turma_id

    items, total = await service.search(
        professor_id=professor_filter,
        turma_id=turma_filter,
        only_active=only_active,
        page=page,
        size=size,
    )

    return PaginatedResponse(
        items=[AlocacaoResponse.model_validate(a).model_dump() for a in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{id}",
    response_model=AlocacaoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def get_alocacao(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AlocacaoResponse:
    service = AlocacaoService(session)
    alocacao = await service.get_by_id(id)
    if current_user["perfil"] == Perfil.PROFESSOR and str(alocacao.professor_id) != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return AlocacaoResponse.model_validate(alocacao)


@router.post(
    "",
    response_model=AlocacaoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def create_alocacao(
    body: AlocacaoCreate, session: AsyncSession = Depends(get_session),
) -> AlocacaoResponse:
    service = AlocacaoService(session)
    alocacao = await service.create(body)
    return AlocacaoResponse.model_validate(alocacao)


@router.put(
    "/{id}",
    response_model=AlocacaoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def encerrar_alocacao(
    id: uuid.UUID, body: AlocacaoEncerrar, session: AsyncSession = Depends(get_session),
) -> AlocacaoResponse:
    service = AlocacaoService(session)
    alocacao = await service.encerrar(id, body.data_fim)
    return AlocacaoResponse.model_validate(alocacao)
