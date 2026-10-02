from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedule.models import HorarioAula
from app.shared.enums import DiaSemana


class HorarioAulaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> HorarioAula | None:
        result = await self._session.execute(
            select(HorarioAula).where(HorarioAula.id == id),
        )
        return result.scalar_one_or_none()

    # ── Consultas de conflito ────────────────────────────────────────
    # O banco não tem índice para interseção de intervalos, então a sobreposição é
    # avaliada em Python. Por isso estas duas consultas trazem só as janelas do mesmo
    # (dia, escopo) — recorte pequeno, e o índice (turma_id, dia_semana) /
    # (professor_id, dia_semana) paga a busca.

    async def list_by_turma_dia(
        self, turma_id: uuid.UUID, dia_semana: DiaSemana, only_active: bool = True,
        excluir_id: uuid.UUID | None = None,
    ) -> list[HorarioAula]:
        return await self._list_scope_por_dia(
            HorarioAula.turma_id == turma_id, dia_semana, only_active, excluir_id,
        )

    async def list_by_professor_dia(
        self, professor_id: uuid.UUID, dia_semana: DiaSemana, only_active: bool = True,
        excluir_id: uuid.UUID | None = None,
    ) -> list[HorarioAula]:
        return await self._list_scope_por_dia(
            HorarioAula.professor_id == professor_id, dia_semana, only_active, excluir_id,
        )

    async def _list_scope_por_dia(
        self,
        escopo,
        dia_semana: DiaSemana,
        only_active: bool,
        excluir_id: uuid.UUID | None,
    ) -> list[HorarioAula]:
        condicoes = [HorarioAula.dia_semana == dia_semana, escopo]
        if only_active:
            condicoes.append(HorarioAula.ativo.is_(True))
        if excluir_id is not None:
            # Ao editar, a própria linha não pode colidir consigo mesma.
            condicoes.append(HorarioAula.id != excluir_id)
        result = await self._session.execute(
            select(HorarioAula).where(and_(*condicoes)).order_by(HorarioAula.hora_inicio),
        )
        return list(result.scalars().all())

    # ── Consultas de leitura ─────────────────────────────────────────

    async def list_by_turma(
        self, turma_id: uuid.UUID, only_active: bool = True,
        dias: Sequence[DiaSemana] | None = None,
    ) -> list[HorarioAula]:
        condicoes = [HorarioAula.turma_id == turma_id]
        if only_active:
            condicoes.append(HorarioAula.ativo.is_(True))
        if dias:
            condicoes.append(HorarioAula.dia_semana.in_(list(dias)))
        result = await self._session.execute(
            select(HorarioAula).where(and_(*condicoes)).order_by(
                HorarioAula.dia_semana, HorarioAula.hora_inicio,
            ),
        )
        return list(result.scalars().all())

    async def list_by_turmas_dia(
        self, turma_ids: Sequence[uuid.UUID], dia_semana: DiaSemana, only_active: bool = True,
    ) -> list[HorarioAula]:
        """Janelas de várias turmas num mesmo dia — uma consulta só.

        É o caminho quente do aviso de ausência: um responsável com dois filhos em
        turmas diferentes resolve os dois em uma ida ao banco.
        """
        if not turma_ids:
            return []
        condicoes = [
            HorarioAula.turma_id.in_(list(turma_ids)),
            HorarioAula.dia_semana == dia_semana,
        ]
        if only_active:
            condicoes.append(HorarioAula.ativo.is_(True))
        result = await self._session.execute(
            select(HorarioAula).where(and_(*condicoes)).order_by(
                HorarioAula.turma_id, HorarioAula.hora_inicio,
            ),
        )
        return list(result.scalars().all())

    async def search(
        self,
        turma_id: uuid.UUID | None = None,
        professor_id: uuid.UUID | None = None,
        dias: Sequence[DiaSemana] | None = None,
        only_active: bool = True,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[HorarioAula], int]:
        query = select(HorarioAula)
        if turma_id:
            query = query.where(HorarioAula.turma_id == turma_id)
        if professor_id:
            query = query.where(HorarioAula.professor_id == professor_id)
        if dias:
            query = query.where(HorarioAula.dia_semana.in_(list(dias)))
        if only_active:
            query = query.where(HorarioAula.ativo.is_(True))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        query = query.order_by(
            HorarioAula.dia_semana, HorarioAula.hora_inicio, HorarioAula.turma_id,
        ).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    # ── Escrita ──────────────────────────────────────────────────────

    async def create(self, horario: HorarioAula) -> HorarioAula:
        self._session.add(horario)
        await self._session.flush()
        return horario

    async def update(self, horario: HorarioAula) -> HorarioAula:
        horario.updated_at = datetime.now(timezone.utc)
        self._session.add(horario)
        await self._session.flush()
        return horario

    async def desativar_da_turma(self, turma_id: uuid.UUID) -> int:
        """Desativa todas as janelas de uma turma.

        Usado quando o turno da turma muda: as janelas antigas foram desenhadas para o
        turno anterior, e manter as duas versões ativas colocaria os alunos em dois
        lugares ao mesmo tempo.
        """
        result = await self._session.execute(
            HorarioAula.__table__.update()
            .where(
                and_(HorarioAula.turma_id == turma_id, HorarioAula.ativo.is_(True)),
            )
            .values(ativo=False, updated_at=datetime.now(timezone.utc)),
        )
        return result.rowcount or 0
