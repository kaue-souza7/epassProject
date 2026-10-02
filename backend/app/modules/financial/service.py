from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
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
from app.shared.enums import StatusCarteira, StatusPulseira, TipoMovimentacao


class FinancialService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
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

    async def _get_or_create_wallet(self, aluno_id: uuid.UUID) -> Wallet:
        wallet = await self._wallet_repo.get_by_aluno_id(aluno_id)
        if wallet is not None:
            return wallet

        aluno = await self._aluno_repo.get_by_id(aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")

        wallet = Wallet(
            aluno_id=aluno_id,
            saldo=Decimal("0.00"),
            status=StatusCarteira.ATIVA,
        )
        savepoint = await self._session.begin_nested()
        try:
            await self._wallet_repo.create(wallet)
            await savepoint.commit()
            return wallet
        except IntegrityError:
            await savepoint.rollback()
            wallet = await self._wallet_repo.get_by_aluno_id(aluno_id)
            if wallet is None:
                raise NotFound("Carteira não encontrada")
            return wallet

    async def _get_or_create_wallet_for_update(self, aluno_id: uuid.UUID) -> Wallet:
        """Obtém a carteira com lock, criando-a antes se ainda não existir.

        A criação é idempotente (índice único por aluno); após criar (ou perder
        a corrida), o lock é adquirido para serializar o débito/crédito.
        """
        wallet = await self._wallet_repo.get_by_aluno_id_for_update(aluno_id)
        if wallet is not None:
            return wallet

        await self._get_or_create_wallet(aluno_id)
        wallet = await self._wallet_repo.get_by_aluno_id_for_update(aluno_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")
        return wallet

    # ── Saldo ────────────────────────────────────────────────────

    async def consultar_saldo(self, aluno_id: uuid.UUID) -> SaldoResponse:
        wallet = await self._get_or_create_wallet(aluno_id)
        return SaldoResponse(aluno_id=aluno_id, saldo=wallet.saldo)

    # ── Recarga ──────────────────────────────────────────────────

    async def realizar_recarga(
        self, aluno_id: uuid.UUID, data: RecargaRequest, usuario_id: uuid.UUID | None = None,
    ) -> RecargaResponse:
        if data.idempotency_key:
            existente = await self._mov_repo.get_by_idempotency_key(data.idempotency_key)
            if existente is not None:
                return self._recarga_response(existente)

        wallet = await self._get_or_create_wallet_for_update(aluno_id)
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
            idempotency_key=data.idempotency_key,
        )
        try:
            async with self._session.begin_nested():
                await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
                mov = await self._mov_repo.create(mov)
        except IntegrityError:
            # Corrida de retry: a chave já foi persistida por outra requisição.
            if data.idempotency_key:
                existente = await self._mov_repo.get_by_idempotency_key(data.idempotency_key)
                if existente is not None:
                    return self._recarga_response(existente)
            raise Conflict("Recarga já processada")

        return RecargaResponse(
            movimentacao_id=mov.id,
            saldo_anterior=saldo_anterior,
            valor=mov.valor,
            saldo_atual=mov.saldo_posterior,
        )

    @staticmethod
    def _recarga_response(mov: Movimentacao) -> RecargaResponse:
        return RecargaResponse(
            movimentacao_id=mov.id,
            saldo_anterior=mov.saldo_anterior,
            valor=mov.valor,
            saldo_atual=mov.saldo_posterior,
        )

    # ── Consumo ──────────────────────────────────────────────────

    async def realizar_consumo(
        self, data: ConsumoRequest, usuario_id: uuid.UUID | None = None,
    ) -> ConsumoResponse:
        if data.idempotency_key:
            existente = await self._mov_repo.get_by_idempotency_key(data.idempotency_key)
            if existente is not None:
                return self._consumo_response(existente)

        bracelet = await self._bracelet_service.get_by_uid(data.uid_pulseira)
        if bracelet.status != StatusPulseira.ATIVA:
            raise Forbidden("Pulseira bloqueada ou cancelada")
        if bracelet.aluno_id is None:
            raise ValidationError("Pulseira não está vinculada a nenhum aluno")

        aluno = await self._aluno_repo.get_by_id(bracelet.aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if not aluno.ativo:
            raise ValidationError("Aluno inativo não pode consumir")

        wallet = await self._get_or_create_wallet_for_update(bracelet.aluno_id)
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
            idempotency_key=data.idempotency_key,
        )
        try:
            async with self._session.begin_nested():
                await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
                mov = await self._mov_repo.create(mov)
        except IntegrityError:
            if data.idempotency_key:
                existente = await self._mov_repo.get_by_idempotency_key(data.idempotency_key)
                if existente is not None:
                    return self._consumo_response(existente)
            raise Conflict("Consumo já processado")

        return ConsumoResponse(
            movimentacao_id=mov.id,
            saldo_anterior=saldo_anterior,
            valor=mov.valor,
            saldo_atual=mov.saldo_posterior,
            descricao=mov.descricao,
        )

    @staticmethod
    def _consumo_response(mov: Movimentacao) -> ConsumoResponse:
        return ConsumoResponse(
            movimentacao_id=mov.id,
            saldo_anterior=mov.saldo_anterior,
            valor=mov.valor,
            saldo_atual=mov.saldo_posterior,
            descricao=mov.descricao,
        )

    # ── Estorno ──────────────────────────────────────────────────

    async def estornar_consumo(
        self, consumo_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> EstornoResponse:
        mov = await self.realizar_estorno_cantina(
            consumo_id=consumo_id,
            usuario_id=usuario_id,
        )
        return EstornoResponse(
            movimentacao_id=mov.id,
            consumo_estornado_id=consumo_id,
            saldo_anterior=mov.saldo_anterior,
            valor=mov.valor,
            saldo_atual=mov.saldo_posterior,
        )

    # ── Extrato ──────────────────────────────────────────────────

    async def gerar_extrato(
        self, aluno_id: uuid.UUID, page: int = 1, size: int = 20,
    ) -> ExtratoResponse:
        wallet = await self._get_or_create_wallet(aluno_id)
        items, total = await self._mov_repo.get_by_wallet_paginated(
            wallet_id=wallet.id, page=page, size=size,
        )
        return ExtratoResponse(
            aluno_id=aluno_id,
            movimentacoes=[MovimentacaoItem.model_validate(m) for m in items],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )

    # ── Validações ───────────────────────────────────────────────

    def _validar_wallet_ativa(self, wallet: Wallet) -> None:
        if wallet.status == StatusCarteira.BLOQUEADA:
            raise Forbidden("Carteira bloqueada")
        if wallet.status == StatusCarteira.CANCELADA:
            raise Forbidden("Carteira cancelada")

    # ── Consumo Cantina ───────────────────────────────────────────

    async def realizar_consumo_cantina(
        self,
        aluno_id: uuid.UUID,
        valor: Decimal,
        descricao: str,
        usuario_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> Movimentacao:
        if idempotency_key:
            existente = await self._mov_repo.get_by_idempotency_key(idempotency_key)
            if existente is not None:
                return existente

        wallet = await self._wallet_repo.get_by_aluno_id_for_update(aluno_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada para este aluno")
        self._validar_wallet_ativa(wallet)

        if wallet.saldo < valor:
            raise ValidationError("Saldo insuficiente")

        saldo_anterior = wallet.saldo
        novo_saldo = saldo_anterior - valor

        mov = Movimentacao(
            wallet_id=wallet.id,
            tipo=TipoMovimentacao.CONSUMO,
            valor=valor,
            saldo_anterior=saldo_anterior,
            saldo_posterior=novo_saldo,
            descricao=descricao,
            criado_por=usuario_id,
            idempotency_key=idempotency_key,
        )
        try:
            async with self._session.begin_nested():
                await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
                mov = await self._mov_repo.create(mov)
        except IntegrityError:
            if idempotency_key:
                existente = await self._mov_repo.get_by_idempotency_key(idempotency_key)
                if existente is not None:
                    return existente
            raise Conflict("Consumo já processado")

        return mov

    # ── Bloqueio/desbloqueio de carteira ─────────────────────────

    async def bloquear_wallet(self, wallet_id: uuid.UUID) -> Wallet:
        wallet = await self._wallet_repo.get_by_id_for_update(wallet_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")
        if wallet.status == StatusCarteira.CANCELADA:
            raise Conflict("Carteira cancelada não pode ser bloqueada")
        if wallet.status != StatusCarteira.BLOQUEADA:
            wallet.status = StatusCarteira.BLOQUEADA
            wallet = await self._wallet_repo.update(wallet)
        return wallet

    async def desbloquear_wallet(self, wallet_id: uuid.UUID) -> Wallet:
        wallet = await self._wallet_repo.get_by_id_for_update(wallet_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")
        if wallet.status == StatusCarteira.CANCELADA:
            raise Conflict("Carteira cancelada não pode ser desbloqueada")
        if wallet.status != StatusCarteira.ATIVA:
            wallet.status = StatusCarteira.ATIVA
            wallet = await self._wallet_repo.update(wallet)
        return wallet

    # ── Estorno Cantina ────────────────────────────────────────────

    async def realizar_estorno_cantina(
        self,
        consumo_id: uuid.UUID,
        usuario_id: uuid.UUID | None = None,
    ) -> Movimentacao:
        consumo = await self._mov_repo.get_by_id(consumo_id)
        if consumo is None:
            raise NotFound("Movimentação não encontrada")
        if consumo.tipo != TipoMovimentacao.CONSUMO:
            raise ValidationError("Apenas consumos podem ser estornados")

        # A carteira é o ponto de serialização: o lock é adquirido antes de
        # verificar estornos existentes, impedindo estorno duplicado sob
        # concorrência (o índice único em movimentacoes é o backstop).
        wallet = await self._wallet_repo.get_by_id_for_update(consumo.wallet_id)
        if wallet is None:
            raise NotFound("Carteira não encontrada")

        existing = await self._mov_repo.get_estorno_by_consumo_id(consumo_id)
        if existing is not None:
            raise Conflict("Estorno já foi realizado para esta movimentação")

        saldo_anterior = wallet.saldo
        novo_saldo = saldo_anterior + consumo.valor

        descricao_base = (consumo.descricao or "consumo")[:160]
        mov = Movimentacao(
            wallet_id=wallet.id,
            tipo=TipoMovimentacao.ESTORNO,
            valor=consumo.valor,
            saldo_anterior=saldo_anterior,
            saldo_posterior=novo_saldo,
            descricao=f"Estorno cantina: {descricao_base} (consumo {consumo_id})",
            criado_por=usuario_id,
            consumo_original_id=consumo_id,
        )
        try:
            async with self._session.begin_nested():
                await self._wallet_repo.atualizar_saldo(wallet.id, novo_saldo)
                mov = await self._mov_repo.create(mov)
        except IntegrityError:
            raise Conflict("Estorno já foi realizado para esta movimentação")

        return mov
