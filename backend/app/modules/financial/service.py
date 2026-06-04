from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationError
from app.modules.bracelets.service import BraceletService
from app.modules.financial.models import Movimentacao, Wallet
from app.modules.financial.repository import MovimentacaoRepository, WalletRepository
from app.modules.financial.schemas import (
    ConsumoRequest,
    ConsumoResponse,
    EstornoResponse,
    ExtratoResponse,
    MovimentacaoItem,
    RecargaRequest,
    RecargaResponse,
    SaldoResponse,
)
from app.modules.students.repository import AlunoRepository
from app.shared.enums import StatusCarteira, TipoMovimentacao


class FinancialService:
    def __init__(self, session: AsyncSession) -> None:
        self._wallet_repo = WalletRepository(session)
        self._mov_repo = MovimentacaoRepository(session)
        self._aluno_repo = AlunoRepository(session)
        self._bracelet_service = BraceletService(session)

    # ── Carteira ─────────────────────────────────────────────────

    async def criar_wallet(self, aluno_id: uuid.UUID) -> Wallet:
        aluno = await self._aluno_repo.get_by_id(aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if await self._wallet_repo.exists_by_aluno(aluno_id):
            raise Conflict("Aluno já possui carteira")
        wallet = Wallet(aluno_id=aluno_id, saldo=Decimal("0.00"), status=StatusCarteira.ATIVA)
        return await self._wallet_repo.create(wallet)

    async def get_wallet_by_aluno(self, aluno_id: uuid.UUID) -> Wallet:
        wallet = await self._wallet_repo.get_by_aluno_id(aluno_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")
        return wallet

    async def get_wallet_by_id(self, wallet_id: uuid.UUID) -> Wallet:
        wallet = await self._wallet_repo.get_by_id(wallet_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")
        return wallet

    async def search_wallets(
        self, status: str | None = None, page: int = 1, size: int = 20,
    ) -> tuple[list[Wallet], int]:
        return await self._wallet_repo.search_paginated(
            status=status, page=page, size=size,
        )

    # ── Saldo ────────────────────────────────────────────────────

    async def consultar_saldo(self, aluno_id: uuid.UUID) -> SaldoResponse:
        wallet = await self.get_wallet_by_aluno(aluno_id)
        return SaldoResponse(aluno_id=aluno_id, saldo=wallet.saldo)

    # ── Recarga ──────────────────────────────────────────────────

    async def realizar_recarga(
        self, aluno_id: uuid.UUID, data: RecargaRequest, usuario_id: uuid.UUID | None = None,
    ) -> RecargaResponse:
        wallet = await self._wallet_repo.get_by_aluno_id_for_update(aluno_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")
        self._validar_wallet_ativa(wallet)

        saldo_anterior = wallet.saldo
        novo_saldo = saldo_anterior + data.valor

        mov = Movimentacao(
            wallet_id=wallet.id,
            tipo=TipoMovimentacao.RECARGA,
            valor=data.valor,
            saldo_anterior=saldo_anterior,
            saldo_posterior=novo_saldo,
            descricao="Recarga via aplicativo",
            criado_por=usuario_id,
        )
        await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
        mov = await self._mov_repo.create(mov)

        return RecargaResponse(
            movimentacao_id=mov.id,
            saldo_anterior=saldo_anterior,
            valor=data.valor,
            saldo_atual=novo_saldo,
        )

    # ── Consumo ──────────────────────────────────────────────────

    async def realizar_consumo(
        self, data: ConsumoRequest, usuario_id: uuid.UUID | None = None,
    ) -> ConsumoResponse:
        bracelet = await self._bracelet_service.get_by_uid(data.uid_pulseira)
        if bracelet.aluno_id is None:
            raise ValidationError("Pulseira não está vinculada a nenhum aluno")

        wallet = await self._wallet_repo.get_by_aluno_id_for_update(bracelet.aluno_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada para este aluno")
        self._validar_wallet_ativa(wallet)

        if wallet.saldo < data.valor:
            raise ValidationError("Saldo insuficiente")

        saldo_anterior = wallet.saldo
        novo_saldo = saldo_anterior - data.valor

        mov = Movimentacao(
            wallet_id=wallet.id,
            tipo=TipoMovimentacao.CONSUMO,
            valor=data.valor,
            saldo_anterior=saldo_anterior,
            saldo_posterior=novo_saldo,
            descricao=data.descricao or "Consumo na cantina",
            criado_por=usuario_id,
        )
        await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
        mov = await self._mov_repo.create(mov)

        return ConsumoResponse(
            movimentacao_id=mov.id,
            saldo_anterior=saldo_anterior,
            valor=data.valor,
            saldo_atual=novo_saldo,
            descricao=mov.descricao,
        )

    # ── Estorno ──────────────────────────────────────────────────

    async def estornar_consumo(
        self, consumo_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> EstornoResponse:
        consumo = await self._mov_repo.get_by_id(consumo_id)
        if consumo is None:
            raise NotFound("Movimentação não encontrada")
        if consumo.tipo != TipoMovimentacao.CONSUMO:
            raise ValidationError("Apenas consumos podem ser estornados")

        wallet = await self._wallet_repo.get_by_id_for_update(consumo.wallet_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")

        saldo_anterior = wallet.saldo
        novo_saldo = saldo_anterior + consumo.valor

        mov = Movimentacao(
            wallet_id=wallet.id,
            tipo=TipoMovimentacao.ESTORNO,
            valor=consumo.valor,
            saldo_anterior=saldo_anterior,
            saldo_posterior=novo_saldo,
            descricao=f"Estorno: {consumo.descricao or 'consumo'}",
            criado_por=usuario_id,
        )
        await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
        mov = await self._mov_repo.create(mov)

        return EstornoResponse(
            movimentacao_id=mov.id,
            consumo_estornado_id=consumo.id,
            saldo_anterior=saldo_anterior,
            valor=consumo.valor,
            saldo_atual=novo_saldo,
        )

    # ── Extrato ──────────────────────────────────────────────────

    async def gerar_extrato(
        self, aluno_id: uuid.UUID, page: int = 1, size: int = 20,
    ) -> ExtratoResponse:
        wallet = await self.get_wallet_by_aluno(aluno_id)
        items, _ = await self._mov_repo.get_by_wallet_paginated(
            wallet_id=wallet.id, page=page, size=size,
        )
        return ExtratoResponse(
            aluno_id=aluno_id,
            movimentacoes=[MovimentacaoItem.model_validate(m) for m in items],
        )

    # ── Validações ───────────────────────────────────────────────

    def _validar_wallet_ativa(self, wallet: Wallet) -> None:
        if wallet.status == StatusCarteira.BLOQUEADA:
            raise Forbidden("Carteira bloqueada")
        if wallet.status == StatusCarteira.CANCELADA:
            raise Forbidden("Carteira cancelada")
