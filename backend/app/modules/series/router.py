import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.series.schemas import SerieRequest, SerieResponse, SerieUpdateRequest
from app.modules.series.service import SerieService
from app.shared.enums import Perfil

router = APIRouter(prefix="/series", tags=["series"])


@router.get(
    "",
    response_model=list[SerieResponse],
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def list_series(
    only_active: bool = False, session: AsyncSession = Depends(get_session),
) -> list[SerieResponse]:
    service = SerieService(session)
    series = await service.get_all(only_active=only_active)
    return [SerieResponse.model_validate(s) for s in series]


@router.get(
    "/{id}",
    response_model=SerieResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def get_serie(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> SerieResponse:
    service = SerieService(session)
    serie = await service.get_by_id(id)
    return SerieResponse.model_validate(serie)


@router.post(
    "",
    response_model=SerieResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def create_serie(
    body: SerieRequest, session: AsyncSession = Depends(get_session),
) -> SerieResponse:
    service = SerieService(session)
    serie = await service.create(body)
    return SerieResponse.model_validate(serie)


@router.put(
    "/{id}",
    response_model=SerieResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def update_serie(
    id: uuid.UUID, body: SerieUpdateRequest, session: AsyncSession = Depends(get_session),
) -> SerieResponse:
    service = SerieService(session)
    serie = await service.update(id, body)
    return SerieResponse.model_validate(serie)
