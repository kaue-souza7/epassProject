from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationError
from app.modules.cantina.models import Produto
from app.modules.cantina.programacao_models import ProgramacaoCantina, ProgramacaoItem
from app.modules.cantina.programacao_repository import ProgramacaoRepository
from app.modules.cantina.programacao_schemas import (
    ProgramacaoCreate,
    ProgramacaoResponse,
    ProgramacaoSemanaResponse,
    ProgramacaoUpdate,
)
from app.modules.cantina.repository import ProdutoRepository
from app.modules.students.repository import AlunoRepository, ResponsavelAlunoRepository
from app.shared.enums import DiaSemana, TipoProgramacao


class ProgramacaoService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProgramacaoRepository(session)
        self._produto_repo = ProdutoRepository(session)
        self._aluno_repo = AlunoRepository(session)
        self._vinculo_repo = ResponsavelAlunoRepository(session)

    async def listar_semana(
        self, aluno_id: uuid.UUID, responsavel_id: uuid.UUID,
    ) -> ProgramacaoSemanaResponse:
        vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
            aluno_id, responsavel_id,
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a este aluno")

        programacoes = await self._repo.get_by_aluno(aluno_id)
        return ProgramacaoSemanaResponse(
            aluno_id=aluno_id,
            programacoes=[self._to_response(p) for p in programacoes],
        )

    async def criar_ou_atualizar(
        self, data: ProgramacaoCreate, responsavel_id: uuid.UUID,
    ) -> ProgramacaoResponse:
        vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
            data.aluno_id, responsavel_id,
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a este aluno")

        aluno = await self._aluno_repo.get_by_id(data.aluno_id)
        if aluno is None:
            raise NotFound("Aluno não encontrado")
        if not aluno.ativo:
            raise ValidationError("Aluno inativo não pode receber programação")

        for item_data in data.itens:
            produto = await self._produto_repo.get_by_id(item_data.produto_id)
            if produto is None:
                raise NotFound(f"Produto {item_data.produto_id} não encontrado")
            if not produto.ativo:
                raise ValidationError(f"Produto '{produto.nome}' está inativo")

        # GERAL e DIARIA coexistem: DIARIA sobrescreve GERAL apenas no seu dia.
        if data.tipo == TipoProgramacao.GERAL:
            existing = await self._repo.get_by_aluno_tipo(data.aluno_id, data.tipo)
        else:
            existing = await self._repo.get_by_aluno_tipo_dia(
                data.aluno_id, data.tipo, data.dia_semana,
            )

        if existing:
            existing.tipo = data.tipo
            existing.dia_semana = data.dia_semana
            existing.responsavel_id = responsavel_id
            existing.observacoes = data.observacoes
            existing.ativo = True
            existing.itens.clear()
            for item_data in data.itens:
                existing.itens.append(ProgramacaoItem(
                    produto_id=item_data.produto_id,
                    quantidade=item_data.quantidade,
                ))
            programacao = await self._repo.update(existing)
        else:
            programacao = ProgramacaoCantina(
                aluno_id=data.aluno_id,
                responsavel_id=responsavel_id,
                dia_semana=data.dia_semana,
                tipo=data.tipo,
                observacoes=data.observacoes,
                ativo=True,
            )
            for item_data in data.itens:
                programacao.itens.append(ProgramacaoItem(
                    produto_id=item_data.produto_id,
                    quantidade=item_data.quantidade,
                ))
            programacao = await self._repo.create(programacao)

        return self._to_response(programacao)

    async def remover(
        self, programacao_id: uuid.UUID, responsavel_id: uuid.UUID,
    ) -> None:
        programacao = await self._repo.get_by_id(programacao_id)
        if programacao is None:
            raise NotFound("Programação não encontrada")
        vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
            programacao.aluno_id, responsavel_id,
        )
        if vinculo is None:
            raise Forbidden("Você não possui acesso a esta programação")
        await self._repo.delete(programacao)

    def _to_response(self, p: ProgramacaoCantina) -> ProgramacaoResponse:
        return ProgramacaoResponse(
            id=p.id,
            aluno_id=p.aluno_id,
            responsavel_id=p.responsavel_id,
            dia_semana=p.dia_semana,
            tipo=p.tipo,
            ativo=p.ativo,
            observacoes=p.observacoes,
            itens=[
                {
                    "id": item.id,
                    "produto_id": item.produto_id,
                    "produto_nome": item.produto.nome if item.produto else None,
                    "quantidade": item.quantidade,
                }
                for item in p.itens
            ],
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
