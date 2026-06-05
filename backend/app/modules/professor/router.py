import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.professor.schemas import (
    FrequenciaSalvarRequest,
    FrequenciaSalvarResponse,
    NotaSalvarRequest,
    NotaSalvarResponse,
    ProfessorAvaliacao,
    ProfessorTurmaAluno,
    ProfessorTurmaDisciplina,
)
from app.modules.professor.service import ProfessorService
from app.shared.enums import Perfil

router = APIRouter(prefix="/professor", tags=["professor"])


@router.get(
    "/turmas",
    response_model=list[ProfessorTurmaDisciplina],
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def listar_turmas(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ProfessorService(session)
    return await service.get_turmas(uuid.UUID(current_user["sub"]))


@router.get(
    "/turmas/{turma_id}/alunos",
    response_model=list[ProfessorTurmaAluno],
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def listar_alunos(
    turma_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    service = ProfessorService(session)
    return await service.get_turma_alunos(turma_id)


@router.get(
    "/avaliacoes",
    response_model=list[ProfessorAvaliacao],
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def listar_avaliacoes(
    alocacao_id: uuid.UUID = Query(...),
    bimestre: int | None = Query(None, ge=1, le=4),
    session: AsyncSession = Depends(get_session),
):
    service = ProfessorService(session)
    return await service.get_avaliacoes(alocacao_id, bimestre)


@router.post(
    "/frequencia",
    response_model=FrequenciaSalvarResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def salvar_frequencia(
    body: FrequenciaSalvarRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ProfessorService(session)
    try:
        return await service.salvar_frequencia(
            professor_id=uuid.UUID(current_user["sub"]),
            turma_id=body.turma_id,
            data=body.data,
            presencas=[f.model_dump() for f in body.frequencias],
        )
    except ValueError as e:
        logger.exception("Erro ao salvar frequência")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erro inesperado ao salvar frequência")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar frequência")


@router.post(
    "/notas",
    response_model=NotaSalvarResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def salvar_notas(
    body: NotaSalvarRequest,
    session: AsyncSession = Depends(get_session),
):
    service = ProfessorService(session)
    try:
        await service.salvar_notas(
            avaliacao_id=body.avaliacao_id,
            notas=[n.model_dump() for n in body.notas],
        )
        return NotaSalvarResponse()
    except ValueError as e:
        logger.exception("Erro ao salvar notas")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erro inesperado ao salvar notas")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar notas")
