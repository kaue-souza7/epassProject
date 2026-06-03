import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.academic_years.schemas import AnoLetivoRequest, AnoLetivoResponse
from app.modules.academic_years.service import AnoLetivoService
from app.shared.enums import Perfil

router = APIRouter(prefix="/academic-years", tags=["academic-years"])


@router.get(
    "",
    response_model=list[AnoLetivoResponse],
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def list_anos_letivos(session: AsyncSession = Depends(get_session)) -> list[AnoLetivoResponse]:
    service = AnoLetivoService(session)
    anos = await service.get_all()
    return [AnoLetivoResponse.model_validate(a) for a in anos]


@router.get(
    "/{id}",
    response_model=AnoLetivoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def get_ano_letivo(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> AnoLetivoResponse:
    service = AnoLetivoService(session)
    ano = await service.get_by_id(id)
    return AnoLetivoResponse.model_validate(ano)


@router.post(
    "",
    response_model=AnoLetivoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def create_ano_letivo(
    body: AnoLetivoRequest, session: AsyncSession = Depends(get_session),
) -> AnoLetivoResponse:
    service = AnoLetivoService(session)
    ano = await service.create(body)
    return AnoLetivoResponse.model_validate(ano)


@router.put(
    "/{id}",
    response_model=AnoLetivoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def update_ano_letivo(
    id: uuid.UUID, body: AnoLetivoRequest, session: AsyncSession = Depends(get_session),
) -> AnoLetivoResponse:
    service = AnoLetivoService(session)
    ano = await service.update(id, body)
    return AnoLetivoResponse.model_validate(ano)
