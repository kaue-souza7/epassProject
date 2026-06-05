import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
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
    session: AsyncSession = Depends(get_session),
) -> BoletimBimestral:
    service = BoletimService(session)
    return await service.gerar_boletim_bimestral(enrollment_id, bimestre)


@router.get(
    "/report-card/{enrollment_id}/annual",
    response_model=BoletimAnual,
    dependencies=[Depends(require_roles(
        Perfil.ADMIN, Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.RESPONSAVEL,
    ))],
)
async def boletim_anual(
    enrollment_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> BoletimAnual:
    service = BoletimService(session)
    return await service.gerar_boletim_anual(enrollment_id)


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
