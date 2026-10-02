import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.cantina.programacao_schemas import (
    ProgramacaoCreate,
    ProgramacaoResponse,
    ProgramacaoSemanaResponse,
    ProgramacaoUpdate,
)
from app.modules.cantina.programacao_service import ProgramacaoService
from app.shared.enums import Perfil

router = APIRouter(prefix="/cantina/programacao", tags=["cantina-programacao"])


@router.get("/{aluno_id}", response_model=ProgramacaoSemanaResponse)
async def listar_programacao(
    aluno_id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> ProgramacaoSemanaResponse:
    service = ProgramacaoService(session)
    return await service.listar_semana(
        aluno_id=aluno_id,
        responsavel_id=uuid.UUID(current_user["sub"]),
    )


@router.post("", response_model=ProgramacaoResponse, status_code=201)
async def criar_ou_atualizar_programacao(
    body: ProgramacaoCreate,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> ProgramacaoResponse:
    service = ProgramacaoService(session)
    return await service.criar_ou_atualizar(
        data=body,
        responsavel_id=uuid.UUID(current_user["sub"]),
    )


@router.delete("/{programacao_id}", status_code=204)
async def remover_programacao(
    programacao_id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> None:
    service = ProgramacaoService(session)
    await service.remover(
        programacao_id=programacao_id,
        responsavel_id=uuid.UUID(current_user["sub"]),
    )
