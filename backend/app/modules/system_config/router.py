from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.system_config.schemas import (
    AvisoConfigRequest,
    AvisoConfigResponse,
    SmtpConfigRequest,
    SmtpConfigResponse,
    SmtpTestRequest,
    SmtpTestResponse,
)
from app.modules.system_config.service import SystemConfigService
from app.shared.enums import Perfil

router = APIRouter(prefix="/system-config", tags=["system-config"])


@router.get(
    "/avisos",
    response_model=AvisoConfigResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def get_aviso_config(
    session: AsyncSession = Depends(get_session),
) -> AvisoConfigResponse:
    service = SystemConfigService(session)
    return await service.get_aviso_config()


@router.put(
    "/avisos",
    response_model=AvisoConfigResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def save_aviso_config(
    body: AvisoConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> AvisoConfigResponse:
    service = SystemConfigService(session)
    return await service.save_aviso_config(body)


@router.get(
    "/smtp",
    response_model=SmtpConfigResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def get_smtp_config(
    session: AsyncSession = Depends(get_session),
) -> SmtpConfigResponse:
    service = SystemConfigService(session)
    return await service.get_smtp_config()


@router.put(
    "/smtp",
    response_model=SmtpConfigResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def save_smtp_config(
    body: SmtpConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> SmtpConfigResponse:
    service = SystemConfigService(session)
    return await service.save_smtp_config(body)


@router.post(
    "/smtp/test",
    response_model=SmtpTestResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def test_smtp(
    body: SmtpTestRequest,
    session: AsyncSession = Depends(get_session),
) -> SmtpTestResponse:
    service = SystemConfigService(session)
    return await service.test_smtp(body)
