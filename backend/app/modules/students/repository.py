from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.models import Aluno, ResponsavelAluno


class AlunoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Aluno | None:
        result = await self._session.execute(
            select(Aluno).where(Aluno.id == id),
        )
        return result.scalar_one_or_none()

    async def get_by_cpf(self, cpf: str) -> Aluno | None:
        result = await self._session.execute(
            select(Aluno).where(Aluno.cpf == cpf),
        )
        return result.scalar_one_or_none()

    async def search_by_nome(self, nome: str) -> list[Aluno]:
        result = await self._session.execute(
            select(Aluno).where(Aluno.nome.ilike(f"%{nome}%")).order_by(Aluno.nome),
        )
        return list(result.scalars().all())

    async def get_all(self, only_active: bool = False) -> list[Aluno]:
        query = select(Aluno).order_by(Aluno.nome)
        if only_active:
            query = query.where(Aluno.ativo.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def search_paginated(
        self,
        nome: str | None = None,
        only_active: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Aluno], int]:
        query = select(Aluno)

        if nome:
            query = query.where(Aluno.nome.ilike(f"%{nome}%"))
        if only_active:
            query = query.where(Aluno.ativo.is_(True))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Aluno.nome).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def exists_by_cpf(self, cpf: str) -> bool:
        result = await self._session.execute(
            select(Aluno.id).where(Aluno.cpf == cpf).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def create(self, aluno: Aluno) -> Aluno:
        self._session.add(aluno)
        await self._session.flush()
        return aluno

    async def update(self, aluno: Aluno) -> Aluno:
        aluno.updated_at = datetime.now(timezone.utc)
        self._session.add(aluno)
        await self._session.flush()
        return aluno


class ResponsavelAlunoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_aluno(self, aluno_id: uuid.UUID) -> list[ResponsavelAluno]:
        result = await self._session.execute(
            select(ResponsavelAluno).where(ResponsavelAluno.aluno_id == aluno_id),
        )
        return list(result.scalars().all())

    async def get_by_responsavel(self, responsavel_id: uuid.UUID) -> list[ResponsavelAluno]:
        result = await self._session.execute(
            select(ResponsavelAluno).where(ResponsavelAluno.responsavel_id == responsavel_id),
        )
        return list(result.scalars().all())

    async def get_by_aluno_and_responsavel(
        self, aluno_id: uuid.UUID, responsavel_id: uuid.UUID,
    ) -> ResponsavelAluno | None:
        result = await self._session.execute(
            select(ResponsavelAluno).where(
                and_(
                    ResponsavelAluno.aluno_id == aluno_id,
                    ResponsavelAluno.responsavel_id == responsavel_id,
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def exists(self, aluno_id: uuid.UUID, responsavel_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(ResponsavelAluno.aluno_id).where(
                and_(
                    ResponsavelAluno.aluno_id == aluno_id,
                    ResponsavelAluno.responsavel_id == responsavel_id,
                ),
            ).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def create(self, vinculo: ResponsavelAluno) -> ResponsavelAluno:
        self._session.add(vinculo)
        await self._session.flush()
        return vinculo

    async def delete(self, vinculo: ResponsavelAluno) -> None:
        await self._session.delete(vinculo)
        await self._session.flush()
