import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.database import get_session
from app.modules.reports.schemas import (
    BoletimAnual,
    BoletimBimestral,
    ComprovantePagamento,
    DadosEvolucao,
    DeclaracaoMatricula,
    DocumentoPdf,
    HistoricoEscolar,
    RelatorioFrequencia,
)
from app.modules.reports.service import BoletimService
from app.modules.reports.stub_service import RelatorioStubService
from app.shared.enums import Perfil

router = APIRouter(prefix="/reports", tags=["reports"])


async def _verificar_acesso_boletim(
    current_user: dict,
    session: AsyncSession,
    enrollment_id: uuid.UUID,
) -> None:
    from app.core.exceptions import Forbidden, NotFound
    from app.modules.allocations.repository import AlocacaoRepository
    from app.modules.enrollments.repository import MatriculaRepository
    from app.modules.students.repository import ResponsavelAlunoRepository

    perfil = current_user.get("perfil")
    matricula = await MatriculaRepository(session).get_by_id(enrollment_id)
    if matricula is None:
        raise NotFound("Matrícula não encontrada")

    if perfil == Perfil.RESPONSAVEL:
        vinculo = await ResponsavelAlunoRepository(session).get_by_aluno_and_responsavel(
            matricula.aluno_id,
            uuid.UUID(current_user["sub"]),
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a esta matrícula")
    elif perfil == Perfil.PROFESSOR:
        alocacoes, _ = await AlocacaoRepository(session).search(
            professor_id=uuid.UUID(current_user["sub"]),
            turma_id=matricula.turma_id,
            only_active=True,
            size=100,
        )
        if not alocacoes:
            raise Forbidden("Você não leciona nesta turma")


@router.get(
    "/report-card/{enrollment_id}",
    response_model=BoletimBimestral,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def boletim_bimestral(
    enrollment_id: uuid.UUID,
    bimestre: int = Query(..., ge=1, le=4),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BoletimBimestral:
    await _verificar_acesso_boletim(current_user, session, enrollment_id)
    service = BoletimService(session)
    is_responsavel = current_user.get("perfil") == Perfil.RESPONSAVEL
    return await service.gerar_boletim_bimestral(enrollment_id, bimestre, is_responsavel)


@router.get(
    "/report-card/{enrollment_id}/annual",
    response_model=BoletimAnual,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def boletim_anual(
    enrollment_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BoletimAnual:
    await _verificar_acesso_boletim(current_user, session, enrollment_id)
    service = BoletimService(session)
    is_responsavel = current_user.get("perfil") == Perfil.RESPONSAVEL
    return await service.gerar_boletim_anual(enrollment_id, is_responsavel)


@router.get(
    "/frequency/{enrollment_id}",
    response_model=RelatorioFrequencia,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def relatorio_frequencia(
    enrollment_id: uuid.UUID,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
) -> RelatorioFrequencia:
    service = RelatorioStubService()
    return await service.obter_relatorio_frequencia(enrollment_id, start_date, end_date)


@router.get(
    "/school-history/{student_id}",
    response_model=HistoricoEscolar,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def historico_escolar(
    student_id: uuid.UUID,
) -> HistoricoEscolar:
    service = RelatorioStubService()
    return await service.obter_historico_escolar(student_id)


@router.get(
    "/enrollment-certificate/{enrollment_id}",
    response_model=DeclaracaoMatricula,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def declaracao_matricula(
    enrollment_id: uuid.UUID,
) -> DeclaracaoMatricula:
    service = RelatorioStubService()
    return await service.obter_declaracao_matricula(enrollment_id)


@router.get(
    "/payment-receipt/{movement_id}",
    response_model=ComprovantePagamento,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def comprovante_pagamento(
    movement_id: uuid.UUID,
) -> ComprovantePagamento:
    service = RelatorioStubService()
    return await service.obter_comprovante_pagamento(movement_id)


@router.get(
    "/evolution/{enrollment_id}",
    response_model=DadosEvolucao,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def dados_evolucao(
    enrollment_id: uuid.UUID,
) -> DadosEvolucao:
    service = RelatorioStubService()
    return await service.obter_dados_evolucao(enrollment_id)


@router.post(
    "/generate-pdf",
    response_model=DocumentoPdf,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def gerar_pdf(
    tipo: str = Query(...),
    matricula_id: uuid.UUID | None = Query(None),
    aluno_id: uuid.UUID | None = Query(None),
    movimento_id: uuid.UUID | None = Query(None),
) -> DocumentoPdf:
    service = RelatorioStubService()
    ids = {}
    if matricula_id:
        ids["matricula_id"] = str(matricula_id)
    if aluno_id:
        ids["aluno_id"] = str(aluno_id)
    if movimento_id:
        ids["movimento_id"] = str(movimento_id)
    return await service.gerar_pdf(tipo, ids)
