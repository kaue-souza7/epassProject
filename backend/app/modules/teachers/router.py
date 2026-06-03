import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.database import get_session
from app.modules.teachers.schemas import (
    ProfessorProfileCreate,
    ProfessorProfileResponse,
    ProfessorProfileUpdate,
)
from app.modules.teachers.service import ProfessorProfileService
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def list_professores(
    nome: str | None = Query(None),
    matricula_funcional: str | None = Query(None),
    only_active: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = ProfessorProfileService(session)
    items, total = await service.search(
        nome=nome,
        matricula_funcional=matricula_funcional,
        only_active=only_active,
        page=page,
        size=size,
    )
    return PaginatedResponse(
        items=[ProfessorProfileResponse(
            usuario_id=p.usuario_id,
            nome=p.usuario.nome,
            formacao_principal=p.formacao_principal,
            matricula_funcional=p.matricula_funcional,
            data_contratacao=p.data_contratacao,
            observacoes=p.observacoes,
            ativo=p.ativo,
        ).model_dump() for p in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get(
    "/{usuario_id}",
    response_model=ProfessorProfileResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def get_professor(
    usuario_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> ProfessorProfileResponse:
    service = ProfessorProfileService(session)
    profile = await service.get_by_usuario(usuario_id)
    return ProfessorProfileResponse(
        usuario_id=profile.usuario_id,
        nome=profile.usuario.nome,
        formacao_principal=profile.formacao_principal,
        matricula_funcional=profile.matricula_funcional,
        data_contratacao=profile.data_contratacao,
        observacoes=profile.observacoes,
        ativo=profile.ativo,
    )


@router.post(
    "",
    response_model=ProfessorProfileResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def create_professor(
    body: ProfessorProfileCreate, session: AsyncSession = Depends(get_session),
) -> ProfessorProfileResponse:
    service = ProfessorProfileService(session)
    profile = await service.create(body)
    return ProfessorProfileResponse(
        usuario_id=profile.usuario_id,
        nome=profile.usuario.nome,
        formacao_principal=profile.formacao_principal,
        matricula_funcional=profile.matricula_funcional,
        data_contratacao=profile.data_contratacao,
        observacoes=profile.observacoes,
        ativo=profile.ativo,
    )


@router.put(
    "/{usuario_id}",
    response_model=ProfessorProfileResponse,
    dependencies=[Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA))],
)
async def update_professor(
    usuario_id: uuid.UUID, body: ProfessorProfileUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProfessorProfileResponse:
    service = ProfessorProfileService(session)
    profile = await service.update(usuario_id, body)
    return ProfessorProfileResponse(
        usuario_id=profile.usuario_id,
        nome=profile.usuario.nome,
        formacao_principal=profile.formacao_principal,
        matricula_funcional=profile.matricula_funcional,
        data_contratacao=profile.data_contratacao,
        observacoes=profile.observacoes,
        ativo=profile.ativo,
    )
