import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.boletim.schemas import (
    LiberacaoBoletimRequest,
    LiberacaoBoletimResponse,
    LiberacaoStatusResponse,
    PrazoLiberacaoRequest,
    PrazoLiberacaoResponse,
    PrazoLiberacaoUpdate,
)
from app.modules.boletim.service import LiberacaoBoletimService, PrazoLiberacaoService
from app.shared.enums import Perfil

router = APIRouter(prefix="/boletim-liberacao", tags=["boletim-liberacao"])


@router.post(
    "",
    response_model=list[LiberacaoBoletimResponse],
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def liberar_boletim(
    body: LiberacaoBoletimRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[LiberacaoBoletimResponse]:
    service = LiberacaoBoletimService(session)
    return await service.liberar(
        professor_id=uuid.UUID(current_user["sub"]),
        body=body,
    )


@router.get(
    "/status",
    response_model=LiberacaoStatusResponse,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def obter_status_liberacao(
    turma_id: uuid.UUID = Query(...),
    bimestre: int = Query(..., ge=1, le=4),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LiberacaoStatusResponse:
    service = LiberacaoBoletimService(session)
    return await service.obter_status(
        professor_id=uuid.UUID(current_user["sub"]),
        turma_id=turma_id,
        bimestre=bimestre,
    )


@router.get(
    "/prazos",
    response_model=list[PrazoLiberacaoResponse],
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def listar_prazos(
    ano_letivo_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> list[PrazoLiberacaoResponse]:
    service = PrazoLiberacaoService(session)
    return await service.listar_por_ano(ano_letivo_id)


@router.post(
    "/prazos",
    response_model=PrazoLiberacaoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def criar_prazo(
    body: PrazoLiberacaoRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PrazoLiberacaoResponse:
    service = PrazoLiberacaoService(session)
    response = await service.criar(body)

    scheduler = getattr(request.app.state, "prazo_scheduler", None)
    if scheduler:
        prazo_repo = service._prazo_repo
        prazo = await prazo_repo.get_by_id(response.id)
        if prazo:
            scheduler.schedule_prazo(prazo)

    return response


@router.put(
    "/prazos/{prazo_id}",
    response_model=PrazoLiberacaoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def atualizar_prazo(
    prazo_id: uuid.UUID,
    body: PrazoLiberacaoUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PrazoLiberacaoResponse:
    service = PrazoLiberacaoService(session)
    response = await service.atualizar(prazo_id, body)

    scheduler = getattr(request.app.state, "prazo_scheduler", None)
    if scheduler:
        prazo_repo = service._prazo_repo
        prazo = await prazo_repo.get_by_id(prazo_id)
        if prazo:
            scheduler.schedule_prazo(prazo)

    return response
