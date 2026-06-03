import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.academic_config.schemas import (
    ConfiguracaoAcademicaResponse,
    ConfiguracaoAcademicaUpdate,
)
from app.modules.academic_config.service import ConfiguracaoAcademicaService
from app.shared.enums import Perfil

router = APIRouter(prefix="/academic-config", tags=["academic-config"])


@router.get(
    "/{ano_letivo_id}",
    response_model=ConfiguracaoAcademicaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def obter_configuracao(
    ano_letivo_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> ConfiguracaoAcademicaResponse:
    service = ConfiguracaoAcademicaService(session)
    config = await service.obter(ano_letivo_id)
    return ConfiguracaoAcademicaResponse.model_validate(config)


@router.put(
    "/{ano_letivo_id}",
    response_model=ConfiguracaoAcademicaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN))],
)
async def atualizar_configuracao(
    ano_letivo_id: uuid.UUID,
    body: ConfiguracaoAcademicaUpdate,
    session: AsyncSession = Depends(get_session),
) -> ConfiguracaoAcademicaResponse:
    service = ConfiguracaoAcademicaService(session)
    config = await service.atualizar(ano_letivo_id, body)
    return ConfiguracaoAcademicaResponse.model_validate(config)
