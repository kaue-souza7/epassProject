from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agenda.models import Evento, EventoDestinatario
from app.shared.enums import TipoDestinoEvento


class EventoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: uuid.UUID) -> Evento | None:
        result = await self._session.execute(
            select(Evento).where(Evento.id == id, Evento.ativo.is_(True)),
        )
        return result.scalar_one_or_none()

    async def create(self, evento: Evento) -> Evento:
        self._session.add(evento)
        await self._session.flush()
        return evento

    async def update(self, evento: Evento) -> Evento:
        evento.updated_at = datetime.now(timezone.utc)
        self._session.add(evento)
        await self._session.flush()
        return evento

    async def soft_delete(self, evento: Evento) -> Evento:
        evento.ativo = False
        evento.updated_at = datetime.now(timezone.utc)
        self._session.add(evento)
        await self._session.flush()
        return evento

    async def list_all(
        self, page: int = 1, size: int = 20,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> tuple[list[Evento], int]:
        query = select(Evento).where(Evento.ativo.is_(True))

        if data_inicio is not None:
            query = query.where(Evento.data_inicio >= data_inicio)
        if data_fim is not None:
            query = query.where(Evento.data_fim <= data_fim)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Evento.data_inicio.asc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def list_by_professor(
        self, usuario_id: uuid.UUID, turma_ids: list[uuid.UUID],
        page: int = 1, size: int = 20,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> tuple[list[Evento], int]:
        query = (
            select(Evento)
            .outerjoin(EventoDestinatario, Evento.id == EventoDestinatario.evento_id)
            .where(
                and_(
                    Evento.ativo.is_(True),
                    or_(
                        Evento.criado_por == usuario_id,
                        and_(
                            EventoDestinatario.tipo_destino == TipoDestinoEvento.PROFESSOR,
                            EventoDestinatario.destino_id == usuario_id,
                        ),
                        and_(
                            EventoDestinatario.tipo_destino == TipoDestinoEvento.TURMA,
                            EventoDestinatario.destino_id.in_(turma_ids),
                        ),
                    ),
                ),
            )
        )

        if data_inicio is not None:
            query = query.where(Evento.data_inicio >= data_inicio)
        if data_fim is not None:
            query = query.where(Evento.data_fim <= data_fim)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.distinct().order_by(Evento.data_inicio.asc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def list_by_responsavel(
        self, usuario_id: uuid.UUID, turma_ids: list[uuid.UUID],
        page: int = 1, size: int = 20,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> tuple[list[Evento], int]:
        query = (
            select(Evento)
            .outerjoin(EventoDestinatario, Evento.id == EventoDestinatario.evento_id)
            .where(
                and_(
                    Evento.ativo.is_(True),
                    or_(
                        and_(
                            EventoDestinatario.tipo_destino == TipoDestinoEvento.TURMA,
                            EventoDestinatario.destino_id.in_(turma_ids),
                        ),
                        and_(
                            EventoDestinatario.tipo_destino == TipoDestinoEvento.RESPONSAVEL,
                            EventoDestinatario.destino_id == usuario_id,
                        ),
                    ),
                ),
            )
        )

        if data_inicio is not None:
            query = query.where(Evento.data_inicio >= data_inicio)
        if data_fim is not None:
            query = query.where(Evento.data_fim <= data_fim)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.distinct().order_by(Evento.data_inicio.asc()).offset(
            (page - 1) * size,
        ).limit(size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_destinatarios_by_evento(self, evento_id: uuid.UUID) -> list[EventoDestinatario]:
        result = await self._session.execute(
            select(EventoDestinatario).where(EventoDestinatario.evento_id == evento_id),
        )
        return list(result.scalars().all())

    async def delete_destinatarios_by_evento(self, evento_id: uuid.UUID) -> None:
        await self._session.execute(
            EventoDestinatario.__table__.delete().where(
                EventoDestinatario.evento_id == evento_id,
            ),
        )
        await self._session.flush()

    async def bulk_create_destinatarios(
        self, destinatarios: list[EventoDestinatario],
    ) -> list[EventoDestinatario]:
        self._session.add_all(destinatarios)
        await self._session.flush()
        return destinatarios
