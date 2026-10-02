from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.allocations.models import Alocacao
from app.modules.classes.models import Turma
from app.modules.communication.models import (
    Aviso,
    AvisoDestinatario,
    AvisoMensagem,
    Notificacao,
    Ocorrencia,
    OcorrenciaHistorico,
    PreferenciaNotificacao,
    PushTicket,
    PushToken,
)
from app.modules.enrollments.models import Matricula
from app.modules.students.models import Aluno, ResponsavelAluno
from app.modules.users.models import Usuario
from app.shared.enums import (
    LeituraAviso,
    OrdemAviso,
    Perfil,
    PrioridadeAviso,
    StatusAviso,
    StatusMatricula,
    StatusOcorrencia,
    TipoAviso,
    TipoNotificacao,
)


class OcorrenciaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, ocorrencia_id: uuid.UUID) -> Ocorrencia | None:
        result = await self._session.execute(
            select(Ocorrencia).where(Ocorrencia.id == ocorrencia_id),
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        aluno_id: uuid.UUID | None = None,
        responsavel_id: uuid.UUID | None = None,
        status: StatusOcorrencia | None = None,
        tipo: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Ocorrencia], int]:
        query = select(Ocorrencia)
        if aluno_id:
            query = query.where(Ocorrencia.aluno_id == aluno_id)
        if responsavel_id:
            query = query.where(Ocorrencia.responsavel_id == responsavel_id)
        if status:
            query = query.where(Ocorrencia.status == status)
        if tipo:
            query = query.where(Ocorrencia.tipo == tipo)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        query = query.order_by(Ocorrencia.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def list_by_alunos(
        self,
        aluno_ids: list[uuid.UUID],
        status: StatusOcorrencia | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Ocorrencia], int]:
        if not aluno_ids:
            return [], 0
        query = select(Ocorrencia).where(Ocorrencia.aluno_id.in_(aluno_ids))
        if status:
            query = query.where(Ocorrencia.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        query = query.order_by(Ocorrencia.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def list_by_criador(
        self,
        criador_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Ocorrencia], int]:
        query = select(Ocorrencia).where(Ocorrencia.criado_por == criador_id)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()
        query = query.order_by(Ocorrencia.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def create(self, ocorrencia: Ocorrencia) -> Ocorrencia:
        self._session.add(ocorrencia)
        await self._session.flush()
        return ocorrencia

    async def update(self, ocorrencia: Ocorrencia) -> Ocorrencia:
        ocorrencia.updated_at = datetime.now(timezone.utc)
        self._session.add(ocorrencia)
        await self._session.flush()
        return ocorrencia

    async def add_historico(self, historico: OcorrenciaHistorico) -> OcorrenciaHistorico:
        self._session.add(historico)
        await self._session.flush()
        return historico


class AvisoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, aviso_id: uuid.UUID) -> Aviso | None:
        result = await self._session.execute(
            select(Aviso).where(Aviso.id == aviso_id),
        )
        return result.scalar_one_or_none()

    async def search_avisos(
        self,
        caixa: str,
        usuario_id: uuid.UUID,
        status: StatusAviso | None = None,
        busca: str | None = None,
        prioridade: PrioridadeAviso | None = None,
        tipo: TipoAviso | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        turma_id: uuid.UUID | None = None,
        aluno_id: uuid.UUID | None = None,
        leitura: LeituraAviso = LeituraAviso.TODOS,
        ordem: OrdemAviso = OrdemAviso.RECENTES,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Aviso], int]:
        """Lista avisos por caixa, com filtros e ordenação.

        O recorte por destinatário usa `EXISTS` e não um JOIN com `AvisoDestinatario`:
        o índice único `(aviso_id, usuario_id)` garante no máximo uma linha por par, mas
        um JOIN clássico transformaria "não lidos" em "quantas linhas tem" e quebraria
        o `count` da paginação. Com `EXISTS` a linha de `avisos` aparece uma vez só.
        """
        query = select(Aviso)

        recebidos_sub = select(AvisoDestinatario.aviso_id).where(
            AvisoDestinatario.usuario_id == usuario_id,
        )
        if caixa == "recebidos":
            query = query.where(Aviso.id.in_(recebidos_sub))
        elif caixa == "enviados":
            query = query.where(Aviso.criado_por == usuario_id)
        else:  # todos
            query = query.where(
                or_(Aviso.criado_por == usuario_id, Aviso.id.in_(recebidos_sub)),
            )

        if status:
            query = query.where(Aviso.status == status)
        if prioridade:
            query = query.where(Aviso.prioridade == prioridade)
        if tipo:
            query = query.where(Aviso.tipo == tipo)

        if busca:
            termo = f"%{busca}%"
            query = query.where(
                or_(Aviso.titulo.ilike(termo), Aviso.mensagem.ilike(termo)),
            )

        # Período: `publicado_em` é timestamptz, mas o usuário filtra por *data* civil.
        # Comparar com meia-noite UTC deixaria de fora tudo o que aconteceu depois das
        # 21h do dia final (o banco guarda UTC; o Brasil é -03:00), então o fim é
        # estendido até o próximo dia — exclusivo — para cobrir o dia inteiro.
        if data_inicio:
            query = query.where(
                Aviso.publicado_em >= datetime.combine(data_inicio, time.min, tzinfo=timezone.utc),
            )
        if data_fim:
            fim_exclusivo = datetime.combine(
                data_fim + timedelta(days=1), time.min, tzinfo=timezone.utc,
            )
            query = query.where(Aviso.publicado_em < fim_exclusivo)

        if turma_id:
            query = query.where(Aviso.destinatario_turma_id == turma_id)
        if aluno_id:
            # O aviso pode apontar o aluno pelo campo legado ou ter o aluno no contexto
            # de cada destinatário. Os dois precisam casar, senão "avisos sobre a Maria"
            # perderia os avisos materialized para a turma inteira.
            query = query.where(
                or_(
                    Aviso.destinatario_aluno_id == aluno_id,
                    Aviso.id.in_(
                        select(AvisoDestinatario.aviso_id).where(
                            AvisoDestinatario.aluno_id == aluno_id,
                        ),
                    ),
                ),
            )

        if leitura != LeituraAviso.TODOS:
            # "Lido" só faz sentido para quem é destinatário. O autor de um aviso nunca
            # tem linha em `avisos_destinatarios`, então tratá-lo como não lido faria
            # todo aviso enviado aparecer na aba "não lidos" do próprio remetente.
            meu_lido = exists(
                select(AvisoDestinatario.id).where(
                    AvisoDestinatario.aviso_id == Aviso.id,
                    AvisoDestinatario.usuario_id == usuario_id,
                    AvisoDestinatario.lido_em.isnot(None),
                ),
            )
            sou_destinatario = exists(
                select(AvisoDestinatario.id).where(
                    AvisoDestinatario.aviso_id == Aviso.id,
                    AvisoDestinatario.usuario_id == usuario_id,
                ),
            )
            if leitura == LeituraAviso.NAO_LIDOS:
                query = query.where(sou_destinatario, ~meu_lido)
            else:
                query = query.where(meu_lido)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        if ordem == OrdemAviso.ANTIGOS:
            query = query.order_by(Aviso.publicado_em.asc())
        elif ordem == OrdemAviso.PRIORIDADE:
            # CASE explícito em vez de ordenar pela string: em ordem alfabética
            # "alta" < "baixa" < "media", que é exatamente o oposto do que se quer.
            query = query.order_by(
                case(
                    (Aviso.prioridade == PrioridadeAviso.ALTA, 0),
                    (Aviso.prioridade == PrioridadeAviso.MEDIA, 1),
                    (Aviso.prioridade == PrioridadeAviso.BAIXA, 2),
                    else_=3,
                ),
                Aviso.publicado_em.desc(),
            )
        else:
            query = query.order_by(Aviso.publicado_em.desc())

        query = query.offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def find_ausencia(
        self, aluno_id: uuid.UUID, alvo: date,
    ) -> Aviso | None:
        """Aviso de ausência já existente para o aluno nesta data.

        Suporta a idempotência do botão "não vir hoje": sem esta busca, um segundo
        toque (ou um reenvio por Wifi) criaria um segundo aviso e notificaria a
        secretaria duas vezes.

        A janela de dia é `[00:00, 24:00)` em UTC, e o corte de 24h à frente mantém
        avisos criados às 21h de hoje fora do resultado de amanhã.
        """
        inicio = datetime.combine(alvo, time.min, tzinfo=timezone.utc)
        fim = datetime.combine(alvo + timedelta(days=1), time.min, tzinfo=timezone.utc)
        result = await self._session.execute(
            select(Aviso)
            .where(
                and_(
                    Aviso.tipo == TipoAviso.AUSENCIA,
                    Aviso.destinatario_aluno_id == aluno_id,
                    Aviso.publicado_em >= inicio,
                    Aviso.publicado_em < fim,
                ),
            )
            .order_by(Aviso.publicado_em.desc())
            .limit(1),
        )
        return result.scalars().first()

    async def list_publicados_fora_prazo(
        self,
        cutoff: datetime,
        size: int = 200,
    ) -> list[Aviso]:
        result = await self._session.execute(
            select(Aviso)
            .where(
                and_(
                    Aviso.status == StatusAviso.PUBLICADO,
                    Aviso.publicado_em < cutoff,
                ),
            )
            .order_by(Aviso.publicado_em)
            .limit(size),
        )
        return list(result.scalars().all())

    async def create(self, aviso: Aviso) -> Aviso:
        self._session.add(aviso)
        await self._session.flush()
        return aviso

    async def update(self, aviso: Aviso) -> Aviso:
        aviso.updated_at = datetime.now(timezone.utc)
        self._session.add(aviso)
        await self._session.flush()
        return aviso

    # ── Público disponível para o compositor ─────────────────────

    async def list_professores_publico(self) -> list[dict]:
        result = await self._session.execute(
            select(Usuario.id, Usuario.nome)
            .where(
                Usuario.perfil == Perfil.PROFESSOR,
                Usuario.ativo.is_(True),
                Usuario.deleted_at.is_(None),
            )
            .order_by(Usuario.nome),
        )
        return [{"id": row[0], "nome": row[1]} for row in result.all()]

    async def list_turmas_publico(self, professor_id: uuid.UUID | None = None) -> list[dict]:
        query = select(Turma.id, Turma.codigo, Turma.nome).where(Turma.ativo.is_(True))
        if professor_id is not None:
            query = query.where(
                Turma.id.in_(
                    select(Alocacao.turma_id).where(
                        and_(
                            Alocacao.professor_id == professor_id,
                            Alocacao.data_fim.is_(None),
                        ),
                    ),
                ),
            )
        query = query.order_by(Turma.codigo)
        result = await self._session.execute(query)
        return [{"id": row[0], "codigo": row[1], "nome": row[2]} for row in result.all()]

    async def list_responsaveis_publico(
        self,
        professor_id: uuid.UUID | None = None,
        turma_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Responsáveis que um remetente pode endereçar.

        Com `professor_id`, limita aos responsáveis de alunos matriculados em
        turmas ativas do professor (regra de negócio do aviso).
        """
        query = (
            select(
                Usuario.id,
                Usuario.nome,
                Aluno.id.label("aluno_id"),
                Aluno.nome.label("aluno_nome"),
                Turma.codigo.label("turma_codigo"),
            )
            .select_from(ResponsavelAluno)
            .join(Usuario, Usuario.id == ResponsavelAluno.responsavel_id)
            .join(Aluno, Aluno.id == ResponsavelAluno.aluno_id)
            .outerjoin(
                Matricula,
                and_(
                    Matricula.aluno_id == Aluno.id,
                    Matricula.status == StatusMatricula.ATIVA,
                ),
            )
            .outerjoin(Turma, Turma.id == Matricula.turma_id)
            .where(
                Usuario.ativo.is_(True),
                Usuario.deleted_at.is_(None),
            )
            .distinct()
        )
        if professor_id is not None:
            query = query.where(
                Turma.id.in_(
                    select(Alocacao.turma_id).where(
                        and_(
                            Alocacao.professor_id == professor_id,
                            Alocacao.data_fim.is_(None),
                        ),
                    ),
                ),
            )
        if turma_id is not None:
            query = query.where(Turma.id == turma_id)
        query = query.order_by(Usuario.nome)
        result = await self._session.execute(query)
        return [
            {
                "id": row[0],
                "nome": row[1],
                "aluno_id": row[2],
                "aluno_nome": row[3],
                "turma_codigo": row[4],
            }
            for row in result.all()
        ]

    async def list_responsaveis_do_aluno(self, aluno_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(ResponsavelAluno.responsavel_id).where(
                ResponsavelAluno.aluno_id == aluno_id,
            ),
        )
        return list(result.scalars().all())

    async def list_responsaveis_das_turmas(
        self, turma_ids: list[uuid.UUID],
    ) -> list[tuple[uuid.UUID, uuid.UUID]]:
        """Pares (responsavel_id, aluno_id) de turmas com matrícula ativa."""
        if not turma_ids:
            return []
        result = await self._session.execute(
            select(ResponsavelAluno.responsavel_id, ResponsavelAluno.aluno_id)
            .join(Matricula, Matricula.aluno_id == ResponsavelAluno.aluno_id)
            .where(
                and_(
                    Matricula.turma_id.in_(turma_ids),
                    Matricula.status == StatusMatricula.ATIVA,
                ),
            )
            .distinct(),
        )
        return [(row[0], row[1]) for row in result.all()]

    async def list_todos_responsaveis(self) -> list[tuple[uuid.UUID, uuid.UUID]]:
        """Todos os pares (responsavel_id, aluno_id) vinculados."""
        result = await self._session.execute(
            select(ResponsavelAluno.responsavel_id, ResponsavelAluno.aluno_id).distinct(),
        )
        return [(row[0], row[1]) for row in result.all()]

    async def list_turmas_do_professor(self, professor_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(Alocacao.turma_id)
            .where(
                and_(
                    Alocacao.professor_id == professor_id,
                    Alocacao.data_fim.is_(None),
                ),
            )
            .distinct(),
        )
        return list(result.scalars().all())

    async def responsaveis_do_professor_por_responsavel(
        self, professor_id: uuid.UUID, responsavel_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """Subconjunto de responsáveis vinculados às turmas do professor."""
        if not responsavel_ids:
            return set()
        turmas_sub = select(Alocacao.turma_id).where(
            and_(
                Alocacao.professor_id == professor_id,
                Alocacao.data_fim.is_(None),
            ),
        )
        result = await self._session.execute(
            select(ResponsavelAluno.responsavel_id)
            .join(Matricula, Matricula.aluno_id == ResponsavelAluno.aluno_id)
            .where(
                and_(
                    ResponsavelAluno.responsavel_id.in_(responsavel_ids),
                    Matricula.turma_id.in_(turmas_sub),
                    Matricula.status == StatusMatricula.ATIVA,
                ),
            )
            .distinct(),
        )
        return set(result.scalars().all())


class AvisoDestinatarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_aviso_usuario(
        self, aviso_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> AvisoDestinatario | None:
        result = await self._session.execute(
            select(AvisoDestinatario).where(
                and_(
                    AvisoDestinatario.aviso_id == aviso_id,
                    AvisoDestinatario.usuario_id == usuario_id,
                ),
            ),
        )
        return result.scalar_one_or_none()

    async def list_by_aviso(self, aviso_id: uuid.UUID) -> list[AvisoDestinatario]:
        result = await self._session.execute(
            select(AvisoDestinatario)
            .where(AvisoDestinatario.aviso_id == aviso_id)
            .order_by(AvisoDestinatario.created_at),
        )
        return list(result.scalars().all())

    async def list_by_aviso_ids_usuario(
        self, aviso_ids: list[uuid.UUID], usuario_id: uuid.UUID,
    ) -> list[AvisoDestinatario]:
        if not aviso_ids:
            return []
        result = await self._session.execute(
            select(AvisoDestinatario).where(
                and_(
                    AvisoDestinatario.aviso_id.in_(aviso_ids),
                    AvisoDestinatario.usuario_id == usuario_id,
                ),
            ),
        )
        return list(result.scalars().all())

    async def list_nao_lidas_sem_escalada(
        self, aviso_ids: list[uuid.UUID],
    ) -> list[AvisoDestinatario]:
        if not aviso_ids:
            return []
        result = await self._session.execute(
            select(AvisoDestinatario).where(
                and_(
                    AvisoDestinatario.aviso_id.in_(aviso_ids),
                    AvisoDestinatario.lido_em.is_(None),
                    AvisoDestinatario.escalado_em.is_(None),
                ),
            ),
        )
        return list(result.scalars().all())

    async def create(self, destinatario: AvisoDestinatario) -> AvisoDestinatario:
        self._session.add(destinatario)
        await self._session.flush()
        return destinatario

    async def update(self, destinatario: AvisoDestinatario) -> AvisoDestinatario:
        self._session.add(destinatario)
        await self._session.flush()
        return destinatario


class AvisoMensagemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, mensagem_id: uuid.UUID) -> AvisoMensagem | None:
        result = await self._session.execute(
            select(AvisoMensagem).where(AvisoMensagem.id == mensagem_id),
        )
        return result.scalar_one_or_none()

    async def list_by_aviso(self, aviso_id: uuid.UUID) -> list[AvisoMensagem]:
        result = await self._session.execute(
            select(AvisoMensagem)
            .where(AvisoMensagem.aviso_id == aviso_id)
            .order_by(AvisoMensagem.created_at),
        )
        return list(result.scalars().all())

    async def list_visiveis_para(
        self, aviso_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> list[AvisoMensagem]:
        """Mensagens em que o usuário é autor ou destinatário."""
        result = await self._session.execute(
            select(AvisoMensagem)
            .where(
                and_(
                    AvisoMensagem.aviso_id == aviso_id,
                    or_(
                        AvisoMensagem.autor_id == usuario_id,
                        AvisoMensagem.destinatario_id == usuario_id,
                    ),
                ),
            )
            .order_by(AvisoMensagem.created_at),
        )
        return list(result.scalars().all())

    async def create(self, mensagem: AvisoMensagem) -> AvisoMensagem:
        self._session.add(mensagem)
        await self._session.flush()
        return mensagem

    async def update(self, mensagem: AvisoMensagem) -> AvisoMensagem:
        self._session.add(mensagem)
        await self._session.flush()
        return mensagem


class PushTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_ativos(self, usuario_id: uuid.UUID) -> list[PushToken]:
        result = await self._session.execute(
            select(PushToken).where(
                and_(PushToken.usuario_id == usuario_id, PushToken.ativo.is_(True)),
            ),
        )
        return list(result.scalars().all())

    async def upsert(
        self, usuario_id: uuid.UUID, token: str, plataforma: str = "expo",
    ) -> PushToken:
        agora = datetime.now(timezone.utc)
        stmt = (
            pg_insert(PushToken)
            .values(
                id=uuid.uuid4(),
                usuario_id=usuario_id,
                token=token,
                plataforma=plataforma,
                ativo=True,
                created_at=agora,
                updated_at=agora,
                last_seen_at=agora,
            )
            .on_conflict_do_update(
                index_elements=[PushToken.token],
                set_={
                    "usuario_id": usuario_id,
                    "plataforma": plataforma,
                    "ativo": True,
                    "updated_at": agora,
                    "last_seen_at": agora,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        result = await self._session.execute(
            select(PushToken).where(PushToken.token == token),
        )
        return result.scalar_one()

    async def deactivate(self, token: str) -> None:
        result = await self._session.execute(
            select(PushToken).where(PushToken.token == token),
        )
        registro = result.scalar_one_or_none()
        if registro is not None and registro.ativo:
            registro.ativo = False
            registro.updated_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def remove(self, usuario_id: uuid.UUID, token: str) -> None:
        result = await self._session.execute(
            select(PushToken).where(
                and_(PushToken.usuario_id == usuario_id, PushToken.token == token),
            ),
        )
        registro = result.scalar_one_or_none()
        if registro is not None:
            await self._session.delete(registro)
            await self._session.flush()


class PushTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, tickets: list[PushTicket]) -> None:
        if not tickets:
            return
        for ticket in tickets:
            if ticket.id is None:
                ticket.id = uuid.uuid4()
            if ticket.criado_em is None:
                ticket.criado_em = datetime.now(timezone.utc)
        savepoint = await self._session.begin_nested()
        try:
            self._session.add_all(tickets)
            await self._session.flush()
            await savepoint.commit()
        except IntegrityError:
            await savepoint.rollback()

    async def list_pendentes(
        self, limite: int = 1000, idade_minima_segundos: int = 60,
    ) -> list[PushTicket]:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=idade_minima_segundos)
        result = await self._session.execute(
            select(PushTicket)
            .where(
                and_(
                    PushTicket.verificado_em.is_(None),
                    PushTicket.criado_em <= cutoff,
                ),
            )
            .order_by(PushTicket.criado_em)
            .limit(limite),
        )
        return list(result.scalars().all())

    async def marcar_verificado(
        self, ticket: PushTicket, sucesso: bool, erro: str | None = None,
    ) -> None:
        ticket.verificado_em = datetime.now(timezone.utc)
        ticket.sucesso = sucesso
        ticket.erro = erro
        self._session.add(ticket)
        await self._session.flush()


class NotificacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        notificacao: Notificacao,
        evento_key: str | None = None,
    ) -> tuple[Notificacao | None, bool]:
        """Cria a notificação. Com `evento_key`, é idempotente (não duplica em retries).

        Retorna `(notificacao, criada)`: `criada=False` quando a chave já existia,
        permitindo ao dispatcher não reenviar realtime/push em retries.
        """
        if evento_key:
            notificacao.evento_key = evento_key
            # Defaults de coluna só são aplicados no flush; o INSERT direto
            # (on_conflict) precisa dos valores explícitos.
            if notificacao.id is None:
                notificacao.id = uuid.uuid4()
            if notificacao.created_at is None:
                notificacao.created_at = datetime.now(timezone.utc)
            stmt = pg_insert(Notificacao).values(
                id=notificacao.id,
                destinatario_id=notificacao.destinatario_id,
                tipo=notificacao.tipo,
                titulo=notificacao.titulo,
                mensagem=notificacao.mensagem,
                canal=notificacao.canal,
                entidade_tipo=notificacao.entidade_tipo,
                entidade_id=notificacao.entidade_id,
                evento_key=evento_key,
                dados=notificacao.dados,
                lida=False,
                created_at=notificacao.created_at,
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[Notificacao.destinatario_id, Notificacao.evento_key],
                index_where=Notificacao.evento_key.isnot(None),
            )
            result = await self._session.execute(stmt)
            criada = (result.rowcount or 0) > 0
            await self._session.flush()
            existente = await self._session.execute(
                select(Notificacao).where(
                    and_(
                        Notificacao.destinatario_id == notificacao.destinatario_id,
                        Notificacao.evento_key == evento_key,
                    ),
                ),
            )
            return existente.scalar_one_or_none(), criada
        else:
            self._session.add(notificacao)
            try:
                await self._session.flush()
            except IntegrityError:
                return None, False
            return notificacao, True

    async def list_by_destinatario(
        self,
        destinatario_id: uuid.UUID,
        apenas_nao_lidas: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Notificacao], int]:
        query = select(Notificacao).where(Notificacao.destinatario_id == destinatario_id)
        if apenas_nao_lidas:
            query = query.where(Notificacao.lida.is_(False))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        query = query.order_by(Notificacao.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def count_nao_lidas(self, destinatario_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Notificacao).where(
                and_(
                    Notificacao.destinatario_id == destinatario_id,
                    Notificacao.lida.is_(False),
                ),
            ),
        )
        return result.scalar_one()

    async def get_by_id(self, notificacao_id: uuid.UUID) -> Notificacao | None:
        result = await self._session.execute(
            select(Notificacao).where(Notificacao.id == notificacao_id),
        )
        return result.scalar_one_or_none()

    async def marcar_lida(self, notificacao: Notificacao) -> Notificacao:
        notificacao.lida = True
        notificacao.lida_em = datetime.now(timezone.utc)
        self._session.add(notificacao)
        await self._session.flush()
        return notificacao

    async def marcar_lidas_por_entidade(
        self, destinatario_id: uuid.UUID, entidade_tipo: str, entidade_id: uuid.UUID,
    ) -> int:
        result = await self._session.execute(
            select(Notificacao).where(
                and_(
                    Notificacao.destinatario_id == destinatario_id,
                    Notificacao.entidade_tipo == entidade_tipo,
                    Notificacao.entidade_id == entidade_id,
                    Notificacao.lida.is_(False),
                ),
            ),
        )
        registros = list(result.scalars().all())
        agora = datetime.now(timezone.utc)
        for registro in registros:
            registro.lida = True
            registro.lida_em = agora
        await self._session.flush()
        return len(registros)

    async def marcar_todas_lidas(self, destinatario_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(Notificacao).where(
                and_(
                    Notificacao.destinatario_id == destinatario_id,
                    Notificacao.lida.is_(False),
                ),
            ),
        )
        todas = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        for n in todas:
            n.lida = True
            n.lida_em = now
        await self._session.flush()
        return len(todas)


class PreferenciaNotificacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_usuario(
        self, usuario_id: uuid.UUID,
    ) -> list[PreferenciaNotificacao]:
        result = await self._session.execute(
            select(PreferenciaNotificacao).where(
                PreferenciaNotificacao.usuario_id == usuario_id,
            ),
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        usuario_id: uuid.UUID,
        tipo: TipoNotificacao,
        email: bool,
    ) -> PreferenciaNotificacao:
        agora = datetime.now(timezone.utc)
        stmt = (
            pg_insert(PreferenciaNotificacao)
            .values(
                id=uuid.uuid4(),
                usuario_id=usuario_id,
                tipo=tipo,
                email=email,
                created_at=agora,
                updated_at=agora,
            )
            .on_conflict_do_update(
                constraint="uq_preferencia_notificacao_tipo",
                set_={"email": email, "updated_at": agora},
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        result = await self._session.execute(
            select(PreferenciaNotificacao).where(
                and_(
                    PreferenciaNotificacao.usuario_id == usuario_id,
                    PreferenciaNotificacao.tipo == tipo,
                ),
            ),
        )
        return result.scalar_one()

    async def email_habilitado(
        self, usuario_id: uuid.UUID, tipo: TipoNotificacao,
    ) -> bool:
        """Consulta única do caminho quente do dispatch.

        Ausência de linha significa desligado, então o padrão do `SELECT` já é
        o comportamento esperado e não é preciso materializar linha para todo
        usuário que nunca optou por e-mail.
        """
        result = await self._session.execute(
            select(PreferenciaNotificacao.email).where(
                and_(
                    PreferenciaNotificacao.usuario_id == usuario_id,
                    PreferenciaNotificacao.tipo == tipo,
                ),
            ),
        )
        return bool(result.scalar())
