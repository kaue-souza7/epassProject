import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.enrollments.schemas import (
    MatriculaCreate,
    MatriculaListResponse,
    MatriculaResponse,
)
from app.modules.enrollments.service import MatriculaService
from app.modules.students.repository import ResponsavelAlunoRepository
from app.shared.enums import Perfil, StatusMatricula
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get(
    "",
    response_model=PaginatedResponse,
)
async def list_matriculas(
    aluno_id: uuid.UUID | None = Query(None),
    turma_id: uuid.UUID | None = Query(None),
    status: StatusMatricula | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.RESPONSAVEL, Perfil.PROFESSOR)),
) -> PaginatedResponse:
    service = MatriculaService(session)

    if current_user["perfil"] == "responsavel":
        repo_resp = ResponsavelAlunoRepository(session)
        vinculos = await repo_resp.get_by_responsavel(uuid.UUID(current_user["sub"]))
        aluno_ids = [v.aluno_id for v in vinculos]

        if aluno_id is not None:
            if aluno_id in aluno_ids:
                filtered_ids = [aluno_id]
            else:
                filtered_ids = []
        else:
            filtered_ids = aluno_ids

        repo = MatriculaRepository(session)
        items, total = await repo.search(
            aluno_ids=filtered_ids if filtered_ids else None,
            turma_id=turma_id,
            status=status,
            page=page,
            size=size,
        )
    else:
        items, total = await service.search(
            aluno_id=aluno_id,
            turma_id=turma_id,
            status=status,
            page=page,
            size=size,
        )

    return PaginatedResponse(
        items=[
            MatriculaListResponse(
                id=m.id,
                aluno_id=m.aluno_id,
                aluno_nome=nome,
                turma_id=m.turma_id,
                turma_codigo=codigo,
                matricula_origem_id=m.matricula_origem_id,
                data_matricula=m.data_matricula,
                status=m.status,
                data_saida=m.data_saida,
                motivo_saida=m.motivo_saida,
                observacoes=m.observacoes,
            ).model_dump()
            for m, nome, codigo in items
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{id}",
    response_model=MatriculaResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA, Perfil.RESPONSAVEL, Perfil.PROFESSOR))],
)
async def get_matricula(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> MatriculaResponse:
    service = MatriculaService(session)
    matricula = await service.get_by_id(id)
    if current_user["perfil"] == Perfil.RESPONSAVEL:
        repo_resp = ResponsavelAlunoRepository(session)
        if not await repo_resp.exists(matricula.aluno_id, uuid.UUID(current_user["sub"])):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return MatriculaResponse.model_validate(matricula)


@router.post(
    "",
    response_model=MatriculaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def create_matricula(
    body: MatriculaCreate, session: AsyncSession = Depends(get_session),
) -> MatriculaResponse:
    service = MatriculaService(session)
    matricula = await service.create(body)
    return MatriculaResponse.model_validate(matricula)
