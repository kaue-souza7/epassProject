from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound
from app.modules.agenda.models import Evento, EventoDestinatario
from app.modules.agenda.repository import EventoRepository
from app.modules.agenda.schemas import EventoCreate, EventoUpdate
from app.modules.allocations.models import Alocacao
from app.modules.enrollments.models import Matricula
from app.modules.students.models import ResponsavelAluno
from app.shared.enums import Perfil, TipoDestinoEvento


class EventoService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EventoRepository(session)
        self._session = session

    async def criar(
        self, data: EventoCreate, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> Evento:
        evento = Evento(
            titulo=data.titulo,
            descricao=data.descricao,
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
            local=data.local,
            criado_por=usuario_id,
            perfil_criador=perfil,
        )
        evento = await self._repo.create(evento)

        if data.destinatarios:
            destinatarios = [
                EventoDestinatario(
                    evento_id=evento.id,
                    tipo_destino=d.tipo_destino,
                    destino_id=d.destino_id,
                )
                for d in data.destinatarios
            ]
            await self._repo.bulk_create_destinatarios(destinatarios)

        return evento

    async def atualizar(
        self, evento_id: uuid.UUID, data: EventoUpdate,
        usuario_id: uuid.UUID, perfil: Perfil,
    ) -> Evento:
        evento = await self._repo.get_by_id(evento_id)
        if evento is None:
            raise NotFound("Evento não encontrado")

        self._verificar_propriedade(evento, usuario_id, perfil)

        if data.titulo is not None:
            evento.titulo = data.titulo
        if data.descricao is not None:
            evento.descricao = data.descricao
        if data.data_inicio is not None:
            evento.data_inicio = data.data_inicio
        if data.data_fim is not None:
            evento.data_fim = data.data_fim
        if data.local is not None:
            evento.local = data.local

        evento = await self._repo.update(evento)

        if data.destinatarios is not None:
            await self._repo.delete_destinatarios_by_evento(evento_id)
            if data.destinatarios:
                destinatarios = [
                    EventoDestinatario(
                        evento_id=evento.id,
                        tipo_destino=d.tipo_destino,
                        destino_id=d.destino_id,
                    )
                    for d in data.destinatarios
                ]
                await self._repo.bulk_create_destinatarios(destinatarios)

        return evento

    async def excluir(
        self, evento_id: uuid.UUID, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> None:
        evento = await self._repo.get_by_id(evento_id)
        if evento is None:
            raise NotFound("Evento não encontrado")

        self._verificar_propriedade(evento, usuario_id, perfil)
        await self._repo.soft_delete(evento)

    async def obter(
        self, evento_id: uuid.UUID, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> Evento:
        evento = await self._repo.get_by_id(evento_id)
        if evento is None:
            raise NotFound("Evento não encontrado")

        if not await self._tem_visibilidade(evento, usuario_id, perfil):
            raise NotFound("Evento não encontrado")

        return evento

    async def listar(
        self, usuario_id: uuid.UUID, perfil: Perfil,
        page: int = 1, size: int = 20,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> tuple[list[Evento], int]:
        if perfil in (Perfil.ADMIN, Perfil.SECRETARIA):
            return await self._repo.list_all(
                page=page, size=size,
                data_inicio=data_inicio, data_fim=data_fim,
            )

        if perfil == Perfil.PROFESSOR:
            turma_ids = await self._obter_turmas_do_professor(usuario_id)
            return await self._repo.list_by_professor(
                usuario_id=usuario_id, turma_ids=turma_ids,
                page=page, size=size,
                data_inicio=data_inicio, data_fim=data_fim,
            )

        if perfil == Perfil.RESPONSAVEL:
            turma_ids = await self._obter_turmas_do_responsavel(usuario_id)
            return await self._repo.list_by_responsavel(
                usuario_id=usuario_id, turma_ids=turma_ids,
                page=page, size=size,
                data_inicio=data_inicio, data_fim=data_fim,
            )

        return [], 0

    async def _obter_turmas_do_professor(self, usuario_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(Alocacao.turma_id).where(
                Alocacao.professor_id == usuario_id,
            ),
        )
        return list(result.scalars().all())

    async def _obter_turmas_do_responsavel(self, usuario_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(Matricula.turma_id)
            .join(ResponsavelAluno, Matricula.aluno_id == ResponsavelAluno.aluno_id)
            .where(ResponsavelAluno.responsavel_id == usuario_id),
        )
        return list(result.scalars().all())

    async def _tem_visibilidade(
        self, evento: Evento, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> bool:
        if perfil in (Perfil.ADMIN, Perfil.SECRETARIA):
            return True

        if perfil == Perfil.PROFESSOR:
            if evento.criado_por == usuario_id:
                return True
            destinatarios = await self._repo.get_destinatarios_by_evento(evento.id)
            for d in destinatarios:
                if d.tipo_destino == TipoDestinoEvento.PROFESSOR and d.destino_id == usuario_id:
                    return True
                if d.tipo_destino == TipoDestinoEvento.TURMA:
                    turma_ids = await self._obter_turmas_do_professor(usuario_id)
                    if d.destino_id in turma_ids:
                        return True
            return False

        if perfil == Perfil.RESPONSAVEL:
            destinatarios = await self._repo.get_destinatarios_by_evento(evento.id)
            for d in destinatarios:
                if d.tipo_destino == TipoDestinoEvento.RESPONSAVEL and d.destino_id == usuario_id:
                    return True
                if d.tipo_destino == TipoDestinoEvento.TURMA:
                    turma_ids = await self._obter_turmas_do_responsavel(usuario_id)
                    if d.destino_id in turma_ids:
                        return True
            return False

        return False

    def _verificar_propriedade(
        self, evento: Evento, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> None:
        if perfil == Perfil.ADMIN:
            return
        if perfil in (Perfil.SECRETARIA, Perfil.PROFESSOR):
            if evento.criado_por != usuario_id:
                raise Forbidden("Você só pode editar eventos criados por você")
            return
        raise Forbidden("Acesso negado")
