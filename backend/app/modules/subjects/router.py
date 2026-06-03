import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.subjects.schemas import DisciplinaRequest, DisciplinaResponse, DisciplinaUpdateRequest
from app.modules.subjects.service import DisciplinaService
from app.shared.enums import Perfil

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get(
    "",
    response_model=list[DisciplinaResponse],
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def list_disciplinas(
    only_active: bool = False, session: AsyncSession = Depends(get_session),
) -> list[DisciplinaResponse]:
    service = DisciplinaService(session)
    disciplinas = await service.get_all(only_active=only_active)
    return [DisciplinaResponse.model_validate(d) for d in disciplinas]


@router.get(
    "/{id}",
    response_model=DisciplinaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def get_disciplina(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> DisciplinaResponse:
    service = DisciplinaService(session)
    disciplina = await service.get_by_id(id)
    return DisciplinaResponse.model_validate(disciplina)


@router.post(
    "",
    response_model=DisciplinaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def create_disciplina(
    body: DisciplinaRequest, session: AsyncSession = Depends(get_session),
) -> DisciplinaResponse:
    service = DisciplinaService(session)
    disciplina = await service.create(body)
    return DisciplinaResponse.model_validate(disciplina)


@router.put(
    "/{id}",
    response_model=DisciplinaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def update_disciplina(
    id: uuid.UUID, body: DisciplinaUpdateRequest, session: AsyncSession = Depends(get_session),
) -> DisciplinaResponse:
    service = DisciplinaService(session)
    disciplina = await service.update(id, body)
    return DisciplinaResponse.model_validate(disciplina)
