import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.assessment.schemas import (
    AvaliacaoCreate,
    AvaliacaoGradesResponse,
    AvaliacaoResponse,
    AvaliacaoUpdate,
    NotaComAlunoResponse,
    NotaLancar,
    NotaResponse,
)
from app.modules.assessment.service import AvaliacaoService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse


class NotasLancarBody(BaseModel):
    avaliacao_id: uuid.UUID
    notas: list[NotaLancar]


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def listar_avaliacoes(
    alocacao_id: uuid.UUID = Query(...),
    bimestre: int | None = Query(None, ge=1, le=4),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = AvaliacaoService(session)
    items, total = await service.listar_por_alocacao(
        alocacao_id=alocacao_id, bimestre=bimestre, page=page, size=size,
    )
    return PaginatedResponse(
        items=[AvaliacaoResponse.model_validate(a).model_dump() for a in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{id}",
    response_model=AvaliacaoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def get_avaliacao(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> AvaliacaoResponse:
    service = AvaliacaoService(session)
    avaliacao = await service.obter_avaliacao(id)
    return AvaliacaoResponse.model_validate(avaliacao)


@router.get(
    "/{id}/grades",
    response_model=AvaliacaoGradesResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR))],
)
async def obter_notas(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> AvaliacaoGradesResponse:
    service = AvaliacaoService(session)
    avaliacao, notas_com_alunos = await service.obter_notas_com_alunos(id)
    notas_response = []
    for nota, matricula in notas_com_alunos:
        nome = matricula.aluno.nome if matricula.aluno else None
        if nota is not None:
            notas_response.append(
                NotaComAlunoResponse(
                    id=nota.id,
                    avaliacao_id=nota.avaliacao_id,
                    matricula_id=nota.matricula_id,
                    aluno_nome=nome,
                    valor=nota.valor,
                    observacoes=nota.observacoes,
                ),
            )
        else:
            notas_response.append(
                NotaComAlunoResponse(
                    id=matricula.id,
                    avaliacao_id=id,
                    matricula_id=matricula.id,
                    aluno_nome=nome,
                    valor=0,
                    observacoes=None,
                ),
            )
    return AvaliacaoGradesResponse(
        avaliacao=AvaliacaoResponse.model_validate(avaliacao),
        notas=notas_response,
    )


@router.put(
    "/{id}",
    response_model=AvaliacaoResponse,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def update_avaliacao(
    id: uuid.UUID, body: AvaliacaoUpdate, session: AsyncSession = Depends(get_session),
) -> AvaliacaoResponse:
    service = AvaliacaoService(session)
    avaliacao = await service.atualizar(id, body)
    return AvaliacaoResponse.model_validate(avaliacao)


@router.post(
    "",
    response_model=AvaliacaoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def create_avaliacao(
    body: AvaliacaoCreate, session: AsyncSession = Depends(get_session),
) -> AvaliacaoResponse:
    service = AvaliacaoService(session)
    avaliacao = await service.criar(body)
    return AvaliacaoResponse.model_validate(avaliacao)


@router.post(
    "/grades",
    response_model=list[NotaResponse],
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.PROFESSOR))],
)
async def lancar_notas(
    body: NotasLancarBody, session: AsyncSession = Depends(get_session),
) -> list[NotaResponse]:
    service = AvaliacaoService(session)
    notas = await service.lancar_notas(body.avaliacao_id, body.notas)
    return [NotaResponse.model_validate(n) for n in notas]
