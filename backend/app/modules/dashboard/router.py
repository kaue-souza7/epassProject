import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.dashboard.schemas import (
    AdminDashboardResponse,
    ProfessorDashboardResponse,
    ResponsavelDashboardResponse,
    SecretariaDashboardResponse,
)
from app.modules.dashboard.service import DashboardService
from app.shared.enums import Perfil

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/admin",
    response_model=AdminDashboardResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def admin_dashboard(
    session: AsyncSession = Depends(get_session),
) -> AdminDashboardResponse:
    service = DashboardService(session)
    return await service.admin_dashboard()


@router.get(
    "/secretaria",
    response_model=SecretariaDashboardResponse,
    dependencies=[Depends(require_roles(Perfil.SECRETARIA))],
)
async def secretaria_dashboard(
    session: AsyncSession = Depends(get_session),
) -> SecretariaDashboardResponse:
    service = DashboardService(session)
    return await service.secretaria_dashboard()


@router.get(
    "/professor",
    response_model=ProfessorDashboardResponse,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def professor_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> ProfessorDashboardResponse:
    service = DashboardService(session)
    return await service.professor_dashboard(uuid.UUID(current_user["sub"]))


@router.get(
    "/responsavel",
    response_model=ResponsavelDashboardResponse,
    dependencies=[Depends(require_roles(Perfil.RESPONSAVEL))],
)
async def responsavel_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> ResponsavelDashboardResponse:
    service = DashboardService(session)
    return await service.responsavel_dashboard(uuid.UUID(current_user["sub"]))
