import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.students.schemas import (
    AlunoRequest,
    AlunoResponse,
    AlunoUpdateRequest,
    HistoricoEscolarResponse,
    MyChildrenResponse,
    ResponsavelAlunoCreate,
    ResponsavelAlunoResponse,
)
from app.modules.students.service import AlunoService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/students", tags=["students"])


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def list_alunos(
    nome: str | None = Query(None),
    only_active: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = AlunoService(session)
    items, total = await service.search_paginated(
        nome=nome, only_active=only_active, page=page, size=size,
    )
    return PaginatedResponse(
        items=[AlunoResponse.model_validate(a).model_dump() for a in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/my-children",
    response_model=list[MyChildrenResponse],
)
async def list_my_children(
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> list[MyChildrenResponse]:
    service = AlunoService(session)
    alunos = await service.list_alunos_do_responsavel(uuid.UUID(current_user["sub"]))
    return [MyChildrenResponse.model_validate(a) for a in alunos]


@router.get(
    "/{id}",
    response_model=AlunoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def get_aluno(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> AlunoResponse:
    service = AlunoService(session)
    aluno = await service.get_by_id(id)
    return AlunoResponse.model_validate(aluno)


@router.post(
    "",
    response_model=AlunoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def create_aluno(
    body: AlunoRequest, session: AsyncSession = Depends(get_session),
) -> AlunoResponse:
    service = AlunoService(session)
    aluno = await service.create(body)
    return AlunoResponse.model_validate(aluno)


@router.put(
    "/{id}",
    response_model=AlunoResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def update_aluno(
    id: uuid.UUID, body: AlunoUpdateRequest, session: AsyncSession = Depends(get_session),
) -> AlunoResponse:
    service = AlunoService(session)
    aluno = await service.update(id, body)
    return AlunoResponse.model_validate(aluno)


@router.post(
    "/{id}/responsaveis",
    response_model=ResponsavelAlunoResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def add_responsavel(
    id: uuid.UUID, body: ResponsavelAlunoCreate, session: AsyncSession = Depends(get_session),
) -> ResponsavelAlunoResponse:
    service = AlunoService(session)
    vinculo = await service.add_responsavel(id, body)
    return ResponsavelAlunoResponse.model_validate(vinculo)


@router.get(
    "/{id}/responsaveis",
    response_model=list[ResponsavelAlunoResponse],
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def list_responsaveis(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> list[ResponsavelAlunoResponse]:
    service = AlunoService(session)
    vinculos = await service.list_responsaveis(id)
    return [ResponsavelAlunoResponse.model_validate(v) for v in vinculos]


@router.get(
    "/{id}/history",
    response_model=HistoricoEscolarResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def get_student_history(
    id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> HistoricoEscolarResponse:
    service = AlunoService(session)
    return await service.get_history(id)


@router.delete(
    "/{aluno_id}/responsaveis/{responsavel_id}",
    status_code=204,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def remove_responsavel(
    aluno_id: uuid.UUID, responsavel_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    service = AlunoService(session)
    await service.remove_responsavel(aluno_id, responsavel_id)
