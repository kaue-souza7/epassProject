import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.reports.schemas import BoletimAnual, BoletimBimestral
from app.modules.reports.service import BoletimService
from app.shared.enums import Perfil

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/report-card/{enrollment_id}",
    response_model=BoletimBimestral,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def boletim_bimestral(
    enrollment_id: uuid.UUID,
    bimestre: int = Query(..., ge=1, le=4),
    session: AsyncSession = Depends(get_session),
) -> BoletimBimestral:
    service = BoletimService(session)
    return await service.gerar_boletim_bimestral(enrollment_id, bimestre)


@router.get(
    "/report-card/{enrollment_id}/annual",
    response_model=BoletimAnual,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def boletim_anual(
    enrollment_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> BoletimAnual:
    service = BoletimService(session)
    return await service.gerar_boletim_anual(enrollment_id)
