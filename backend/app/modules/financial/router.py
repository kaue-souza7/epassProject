import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.core.exceptions import Forbidden, NotFound
from app.database import get_session
from app.modules.financial.schemas import (
    ConsumoRequest,
    ConsumoResponse,
    EstornoResponse,
    ExtratoResponse,
    RecargaRequest,
    RecargaResponse,
    SaldoResponse,
    WalletDetailResponse,
)
from app.modules.financial.service import FinancialService
from app.modules.students.repository import ResponsavelAlunoRepository
from app.shared.enums import Perfil
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/financial", tags=["financial"])


# ══════════════════════════════════════════════════════════════════
# RESPONSÁVEL — descoberta automática do aluno via token
# ══════════════════════════════════════════════════════════════════


async def _get_aluno_id_do_responsavel(
    current_user: dict,
    session: AsyncSession,
    aluno_id: uuid.UUID | None = None,
) -> uuid.UUID:
    responsavel_id = uuid.UUID(current_user["sub"])
    repo = ResponsavelAlunoRepository(session)

    if aluno_id is not None:
        vinculo = await repo.get_by_aluno_and_responsavel(aluno_id, responsavel_id)
        if vinculo is None:
            raise Forbidden("Você não possui acesso a este aluno")
        return aluno_id

    vinculos = await repo.get_by_responsavel(responsavel_id)
    if not vinculos:
        raise NotFound("Nenhum aluno vinculado a este responsável")
    return vinculos[0].aluno_id


@router.get("/me/balance", response_model=SaldoResponse)
async def meu_saldo(
    aluno_id: uuid.UUID | None = Query(None),
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> SaldoResponse:
    service = FinancialService(session)
    target_aluno = await _get_aluno_id_do_responsavel(current_user, session, aluno_id)
    return await service.consultar_saldo(target_aluno)


@router.get("/me/statement", response_model=ExtratoResponse)
async def meu_extrato(
    aluno_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> ExtratoResponse:
    service = FinancialService(session)
    target_aluno = await _get_aluno_id_do_responsavel(current_user, session, aluno_id)
    return await service.gerar_extrato(aluno_id=target_aluno, page=page, size=size)


@router.post("/me/recharge", response_model=RecargaResponse, status_code=201)
async def minha_recarga(
    body: RecargaRequest,
    aluno_id: uuid.UUID | None = Query(None),
    current_user: dict = Depends(require_roles(Perfil.RESPONSAVEL)),
    session: AsyncSession = Depends(get_session),
) -> RecargaResponse:
    service = FinancialService(session)
    # Aceita o aluno no query param ou no corpo, sempre validando o vínculo.
    target_aluno = await _get_aluno_id_do_responsavel(
        current_user, session, aluno_id or body.aluno_id,
    )
    return await service.realizar_recarga(
        aluno_id=target_aluno,
        data=body,
        usuario_id=uuid.UUID(current_user["sub"]),
    )


# ══════════════════════════════════════════════════════════════════
# CANTINA
# ══════════════════════════════════════════════════════════════════


@router.post("/consumption", response_model=ConsumoResponse, status_code=201)
async def realizar_consumo(
    body: ConsumoRequest,
    current_user: dict = Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA)),
    session: AsyncSession = Depends(get_session),
) -> ConsumoResponse:
    service = FinancialService(session)
    return await service.realizar_consumo(
        data=body,
        usuario_id=uuid.UUID(current_user["sub"]),
    )


@router.post("/consumption/{id}/refund", response_model=EstornoResponse, status_code=201)
async def estornar_consumo(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.ADMIN, Perfil.SECRETARIA)),
    session: AsyncSession = Depends(get_session),
) -> EstornoResponse:
    service = FinancialService(session)
    return await service.estornar_consumo(
        consumo_id=id,
        usuario_id=uuid.UUID(current_user["sub"]),
    )


# ══════════════════════════════════════════════════════════════════
# ADMINISTRAÇÃO
# ══════════════════════════════════════════════════════════════════


@router.get("/wallets", response_model=PaginatedResponse)
async def listar_wallets(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles(Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    service = FinancialService(session)
    items, total = await service.search_wallets(status=status, page=page, size=size)
    return PaginatedResponse(
        items=[WalletDetailResponse(
            id=w.id,
            aluno_id=w.aluno_id,
            saldo=w.saldo,
            status=w.status,
            created_at=w.created_at,
            updated_at=w.updated_at,
            aluno_nome=w.aluno.nome if w.aluno else None,
        ).model_dump() for w in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/wallets/{id}", response_model=WalletDetailResponse)
async def get_wallet(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> WalletDetailResponse:
    service = FinancialService(session)
    wallet = await service.get_wallet_by_id(id)
    return _wallet_detail(wallet)


def _wallet_detail(wallet) -> WalletDetailResponse:
    return WalletDetailResponse(
        id=wallet.id,
        aluno_id=wallet.aluno_id,
        saldo=wallet.saldo,
        status=wallet.status,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
        aluno_nome=wallet.aluno.nome if wallet.aluno else None,
    )


@router.patch("/wallets/{id}/block", response_model=WalletDetailResponse)
async def bloquear_wallet(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> WalletDetailResponse:
    service = FinancialService(session)
    wallet = await service.bloquear_wallet(id)
    return _wallet_detail(wallet)


@router.patch("/wallets/{id}/unblock", response_model=WalletDetailResponse)
async def desbloquear_wallet(
    id: uuid.UUID,
    current_user: dict = Depends(require_roles(Perfil.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> WalletDetailResponse:
    service = FinancialService(session)
    wallet = await service.desbloquear_wallet(id)
    return _wallet_detail(wallet)
