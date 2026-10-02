from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.schedule.schemas import (
    AulasDoDiaResponse,
    HorarioAulaCreate,
    HorarioAulaResponse,
    HorarioAulaUpdate,
)
from app.modules.schedule.service import HorarioAulaService
from app.shared.enums import DiaSemana, Perfil

router = APIRouter(prefix="/schedule", tags=["schedule"])

STAFF_GRADE: tuple[Perfil, ...] = (
    Perfil.ADMIN, Perfil.SECRETARIA, Perfil.COORDENADOR, Perfil.PROFESSOR,
)
STAFF_ESCRITA: tuple[Perfil, ...] = (Perfil.ADMIN, Perfil.SECRETARIA)

DIAS_ORDEM: list[DiaSemana] = [
    DiaSemana.SEG, DiaSemana.TER, DiaSemana.QUA,
    DiaSemana.QUI, DiaSemana.SEX, DiaSemana.SAB,
]


@router.get(
    "",
    response_model=list[HorarioAulaResponse],
    dependencies=[Depends(require_roles(*STAFF_GRADE))],
)
async def listar_horarios(
    turma_id: uuid.UUID | None = Query(None),
    professor_id: uuid.UUID | None = Query(None),
    dia: list[DiaSemana] | None = Query(None, description="Repetir para filtrar vários dias"),
    incluir_inativos: bool = Query(False),
    session: AsyncSession = Depends(get_session),
) -> list[HorarioAulaResponse]:
    """Grade crua, filtrada. A grade agrupada por turma é `GET /schedule/grid`."""
    service = HorarioAulaService(session)
    itens, _ = await service.listar(
        turma_id=turma_id,
        professor_id=professor_id,
        dias=dia or None,
        only_active=not incluir_inativos,
        page=1,
        size=200,
    )
    return [await service.response_de(h) for h in itens]


@router.get(
    "/dias",
    response_model=list[DiaSemana],
    dependencies=[Depends(require_roles(*STAFF_GRADE))],
)
async def dias_com_aula() -> list[DiaSemana]:
    """Dias úteis em ordem. Fixo no backend para cliente não duplicar a lista."""
    return DIAS_ORDEM


@router.get(
    "/aulas-do-dia",
    response_model=AulasDoDiaResponse,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.COORDENADOR, Perfil.RESPONSAVEL,
    ))],
)
async def aulas_do_dia(
    aluno_id: uuid.UUID = Query(..., description="Aluno cujas aulas de hoje serão resolvidas"),
    data: date | None = Query(None, description="Padrão: hoje"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AulasDoDiaResponse:
    """Aulas de hoje da turma do aluno, com o professor de cada janela.

    Serve a três coisas ao mesmo tempo: o preview do botão de ausência ("vou avisar a
    professora Ana e o professor Carlos"), a tela de "hoje" do professor, e a
    conferência da secretaria de que a grade está correta.
    """
    service = HorarioAulaService(session)
    perfil = Perfil(current_user["perfil"])
    # Só o responsável passa pelo vínculo; para os papéis de gestão a leitura já é
    # autorizada, e obrigá-los a listar os próprios filhos não faria sentido.
    responsavel_id = uuid.UUID(current_user["sub"]) if perfil == Perfil.RESPONSAVEL else None
    return await service.aulas_do_dia_para_aluno(aluno_id, data, responsavel_id)


@router.get(
    "/grid/{turma_id}",
    response_model=list[HorarioAulaResponse],
    dependencies=[Depends(require_roles(*STAFF_GRADE))],
)
async def grade_da_turma(
    turma_id: uuid.UUID,
    incluir_inativos: bool = Query(False),
    session: AsyncSession = Depends(get_session),
) -> list[HorarioAulaResponse]:
    service = HorarioAulaService(session)
    aulas = await service.listar_da_turma(turma_id, only_active=not incluir_inativos)
    return [await service.response_de(a) for a in aulas]


@router.get(
    "/{id}",
    response_model=HorarioAulaResponse,
    dependencies=[Depends(require_roles(*STAFF_GRADE))],
)
async def obter_horario(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> HorarioAulaResponse:
    service = HorarioAulaService(session)
    return await service.response_de(await service.get_by_id(id))


@router.post(
    "",
    response_model=HorarioAulaResponse,
    status_code=201,
    dependencies=[Depends(require_roles(*STAFF_ESCRITA))],
)
async def criar_horario(
    body: HorarioAulaCreate,
    session: AsyncSession = Depends(get_session),
) -> HorarioAulaResponse:
    """Cria uma janela de aula.

    A escrita é restrita a admin e secretaria de propósito: mexer na agenda é
    decisão administrativa, e um professor que reconfigurasse a própria agenda poderia
    se remover da turma em que dá aula.
    """
    service = HorarioAulaService(session)
    return await service.response_de(await service.criar(body))


@router.put(
    "/{id}",
    response_model=HorarioAulaResponse,
    dependencies=[Depends(require_roles(*STAFF_ESCRITA))],
)
async def atualizar_horario(
    id: uuid.UUID,
    body: HorarioAulaUpdate,
    session: AsyncSession = Depends(get_session),
) -> HorarioAulaResponse:
    service = HorarioAulaService(session)
    return await service.response_de(await service.atualizar(id, body))


@router.patch(
    "/{id}/desativar",
    response_model=HorarioAulaResponse,
    dependencies=[Depends(require_roles(*STAFF_ESCRITA))],
)
async def desativar_horario(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> HorarioAulaResponse:
    service = HorarioAulaService(session)
    return await service.response_de(await service.desativar(id))


@router.patch(
    "/{id}/reativar",
    response_model=HorarioAulaResponse,
    dependencies=[Depends(require_roles(*STAFF_ESCRITA))],
)
async def reativar_horario(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> HorarioAulaResponse:
    service = HorarioAulaService(session)
    return await service.response_de(await service.reativar(id))
