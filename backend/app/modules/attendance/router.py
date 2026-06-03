import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.attendance.schemas import (
    ChamadaAbrir,
    ChamadaDetalheResponse,
    ChamadaResponse,
    FrequenciaComMatriculaResponse,
    FrequenciaRegistrar,
)
from app.modules.attendance.service import ChamadaService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse


class FrequenciasRegistrarBody(BaseModel):
    chamada_id: uuid.UUID
    frequencias: list[FrequenciaRegistrar]


router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get(
    "/calls",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR,
    ))],
)
async def listar_chamadas(
    alocacao_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = ChamadaService(session)
    items, total = await service.listar_por_alocacao(
        alocacao_id=alocacao_id, page=page, size=size,
    )
    return PaginatedResponse(
        items=[ChamadaResponse.model_validate(c).model_dump() for c in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/calls/{id}",
    response_model=ChamadaDetalheResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR,
    ))],
)
async def obter_chamada(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> ChamadaDetalheResponse:
    service = ChamadaService(session)
    chamada = await service.obter_chamada(id)
    return ChamadaDetalheResponse(
        id=chamada.id,
        alocacao_id=chamada.alocacao_id,
        data_hora_aula=chamada.data_hora_aula,
        frequencias=[
            FrequenciaComMatriculaResponse(
                id=f.id,
                chamada_id=f.chamada_id,
                matricula_id=f.matricula_id,
                matricula_codigo=f.matricula.turma.codigo if f.matricula and f.matricula.turma else None,
                aluno_nome=f.matricula.aluno.nome if f.matricula and f.matricula.aluno else None,
                status=f.status,
                observacoes=f.observacoes,
            )
            for f in chamada.frequencias
        ],
    )


@router.post(
    "/calls",
    response_model=ChamadaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def abrir_chamada(
    body: ChamadaAbrir, session: AsyncSession = Depends(get_session),
) -> ChamadaResponse:
    service = ChamadaService(session)
    chamada = await service.abrir_chamada(body)
    return ChamadaResponse.model_validate(chamada)


@router.post(
    "/frequencies",
    status_code=204,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def registrar_frequencias(
    body: FrequenciasRegistrarBody, session: AsyncSession = Depends(get_session),
) -> None:
    service = ChamadaService(session)
    await service.registrar_frequencias(body.chamada_id, body.frequencias)
