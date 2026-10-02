from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationError
from app.modules.allocations.repository import AlocacaoRepository
from app.modules.classes.repository import TurmaRepository
from app.modules.communication.models import (
    Aviso,
    AvisoDestinatario,
    AvisoMensagem,
    Notificacao,
    Ocorrencia,
    OcorrenciaHistorico,
    PreferenciaNotificacao,
    PushToken,
)
from app.modules.communication.repository import (
    AvisoDestinatarioRepository,
    AvisoMensagemRepository,
    AvisoRepository,
    NotificacaoRepository,
    OcorrenciaRepository,
    PreferenciaNotificacaoRepository,
    PushTokenRepository,
)
from app.modules.communication.schemas import (
    AusenciaCreate,
    AusenciaResponse,
    AvisoCreate,
    AvisoEstatisticasResponse,
    AvisoUpdate,
    OcorrenciaCreate,
    OcorrenciaStatusUpdate,
    OcorrenciaUpdate,
    PublicoDisponivelResponse,
    PublicoPessoaResponse,
    PublicoTurmaResponse,
)
from app.modules.enrollments.repository import MatriculaRepository
from app.modules.students.repository import AlunoRepository, ResponsavelAlunoRepository
from app.shared.enums import (
    LeituraAviso,
    OrdemAviso,
    Perfil,
    PrioridadeAviso,
    StatusAviso,
    StatusOcorrencia,
    TipoAviso,
    TipoNotificacao,
)

logger = logging.getLogger(__name__)

STATUS_TRANSICOES_OCORRENCIA: dict[StatusOcorrencia, list[StatusOcorrencia]] = {
    StatusOcorrencia.ABERTA: [StatusOcorrencia.EM_ANDAMENTO, StatusOcorrencia.RESOLVIDA, StatusOcorrencia.ARQUIVADA],
    StatusOcorrencia.EM_ANDAMENTO: [StatusOcorrencia.RESOLVIDA, StatusOcorrencia.ARQUIVADA],
    StatusOcorrencia.RESOLVIDA: [StatusOcorrencia.ARQUIVADA],
    StatusOcorrencia.ARQUIVADA: [],
}

GESTORES: tuple[Perfil, ...] = (Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA)


class OcorrenciaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OcorrenciaRepository(session)
        self._aluno_repo = AlunoRepository(session)
        self._vinculo_repo = ResponsavelAlunoRepository(session)
        self._alocacao_repo = AlocacaoRepository(session)
        self._turma_repo = TurmaRepository(session)

    async def criar(
        self,
        body: OcorrenciaCreate,
        criado_por: uuid.UUID,
        perfil: Perfil,
    ) -> Ocorrencia:
        if body.aluno_id:
            aluno = await self._aluno_repo.get_by_id(body.aluno_id)
            if aluno is None:
                raise NotFound("Aluno não encontrado")
        if body.turma_id:
            turma = await self._turma_repo.get_by_id(body.turma_id)
            if turma is None:
                raise NotFound("Turma não encontrada")

        # Professor só registra para alunos/turmas em que leciona.
        if perfil == Perfil.PROFESSOR:
            if body.turma_id and not await self._alocacao_repo.professor_leciona_turma(
                criado_por, body.turma_id,
            ):
                raise Forbidden("Você não leciona para esta turma")
            if body.aluno_id and not await self._alocacao_repo.professor_leciona_aluno(
                criado_por, body.aluno_id,
            ):
                raise Forbidden(
                    "Você só pode registrar ocorrências para alunos das suas turmas",
                )

        if body.responsavel_id:
            if body.aluno_id is None:
                raise ValidationError(
                    "Informe o aluno para vincular um responsável à ocorrência",
                )
            vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
                body.aluno_id, body.responsavel_id,
            )
            if vinculo is None and perfil not in (
                Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA,
            ):
                raise ValidationError("Responsável informado não está vinculado ao aluno")

        ocorrencia = Ocorrencia(
            aluno_id=body.aluno_id,
            turma_id=body.turma_id,
            titulo=body.titulo,
            descricao=body.descricao,
            tipo=body.tipo,
            severidade=body.severidade,
            responsavel_id=body.responsavel_id,
            criado_por=criado_por,
        )
        ocorrencia = await self._repo.create(ocorrencia)
        await self._repo.add_historico(OcorrenciaHistorico(
            ocorrencia_id=ocorrencia.id,
            status_novo=StatusOcorrencia.ABERTA,
            acao="Ocorrência criada",
            autor_id=criado_por,
        ))

        await self._notificar_responsaveis(ocorrencia)
        return ocorrencia

    async def _notificar_responsaveis(
        self,
        ocorrencia: Ocorrencia,
        evento_sufixo: str = "criada",
        titulo: str = "Nova ocorrência",
    ) -> None:
        """Notifica o responsável informado ou todos os vinculados ao aluno.

        A ocorrência já está persistida (flush) quando esta rotina roda. Cada
        notificação é criada em um savepoint: uma falha de notificação/entrega
        não desfaz a ocorrência (e o `evento_key` permite reprocessar depois).
        """
        if ocorrencia.responsavel_id:
            destinatarios = [ocorrencia.responsavel_id]
        elif ocorrencia.aluno_id:
            vinculos = await self._vinculo_repo.get_by_aluno(ocorrencia.aluno_id)
            destinatarios = [v.responsavel_id for v in vinculos]
        else:
            destinatarios = []
        destinatarios = list(dict.fromkeys(destinatarios))

        aluno_nome = None
        if ocorrencia.aluno_id:
            aluno = await self._aluno_repo.get_by_id(ocorrencia.aluno_id)
            aluno_nome = aluno.nome if aluno else None

        corpo = (
            f"Foi registrada uma nova ocorrência para {aluno_nome}."
            if aluno_nome
            else "Foi registrada uma nova ocorrência."
        )

        dados = {
            "tipo": "ocorrencia",
            "ocorrencia_id": str(ocorrencia.id),
            "aluno_id": str(ocorrencia.aluno_id) if ocorrencia.aluno_id else None,
            "aluno_nome": aluno_nome,
        }

        from app.core.notifications import NotificationDispatcher

        for responsavel_id in destinatarios:
            evento_key = f"ocorrencia:{ocorrencia.id}:{evento_sufixo}:{responsavel_id}"
            try:
                async with self._session.begin_nested():
                    await NotificationDispatcher(self._session).dispatch(
                        usuario_id=responsavel_id,
                        titulo=titulo,
                        corpo=corpo,
                        dados=dados,
                        canal="inapp",
                        tipo=TipoNotificacao.OCORRENCIA,
                        entidade_tipo="ocorrencia",
                        entidade_id=ocorrencia.id,
                        evento_key=evento_key,
                    )
            except Exception:
                logger.exception(
                    "Falha ao notificar responsável %s sobre a ocorrência %s "
                    "(evento_key=%s). A ocorrência foi mantida.",
                    responsavel_id, ocorrencia.id, evento_key,
                )

        # O savepoint do dispatcher expira os objetos da sessão; recarrega os
        # relacionamentos usados na serialização da resposta (evita lazy load
        # fora do greenlet na router).
        await self._session.refresh(ocorrencia, attribute_names=["aluno", "turma"])

    async def listar(
        self,
        current_user_id: uuid.UUID,
        perfil: Perfil,
        aluno_id: uuid.UUID | None = None,
        status: StatusOcorrencia | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Ocorrencia], int]:
        if perfil in (Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA):
            return await self._repo.search(
                aluno_id=aluno_id, status=status, page=page, size=size,
            )
        if perfil == Perfil.RESPONSAVEL:
            vinculos = await self._vinculo_repo.get_by_responsavel(current_user_id)
            aluno_ids = [v.aluno_id for v in vinculos]
            if not aluno_ids:
                return [], 0
            return await self._repo.list_by_alunos(
                aluno_ids=aluno_ids, status=status, page=page, size=size,
            )
        if perfil == Perfil.PROFESSOR:
            return await self._repo.list_by_criador(
                criador_id=current_user_id, page=page, size=size,
            )
        raise Forbidden("Perfil sem permissão para listar ocorrências")

    async def obter(
        self,
        ocorrencia_id: uuid.UUID,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> Ocorrencia:
        ocorrencia = await self._repo.get_by_id(ocorrencia_id)
        if ocorrencia is None:
            raise NotFound("Ocorrência não encontrada")

        if perfil in (Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA):
            return ocorrencia
        if perfil == Perfil.PROFESSOR:
            if ocorrencia.criado_por != current_user_id:
                raise Forbidden("Você não possui acesso a esta ocorrência")
            return ocorrencia
        if perfil == Perfil.RESPONSAVEL:
            if ocorrencia.aluno_id is None:
                raise Forbidden("Você não possui acesso a esta ocorrência")
            vinculo = await self._vinculo_repo.get_by_aluno_and_responsavel(
                ocorrencia.aluno_id, current_user_id,
            )
            if vinculo is None:
                raise Forbidden("Você não possui acesso a esta ocorrência")
            return ocorrencia
        raise Forbidden("Perfil sem permissão para acessar ocorrências")

    async def atualizar(
        self,
        ocorrencia_id: uuid.UUID,
        body: OcorrenciaUpdate,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> Ocorrencia:
        ocorrencia = await self.obter(ocorrencia_id, current_user_id, perfil)
        if perfil not in (Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA):
            raise Forbidden("Apenas coordenação e administração podem editar ocorrências")

        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            return ocorrencia

        campos_alterados = []
        for campo, valor in update_data.items():
            setattr(ocorrencia, campo, valor)
            campos_alterados.append(campo)

        ocorrencia = await self._repo.update(ocorrencia)
        await self._repo.add_historico(OcorrenciaHistorico(
            ocorrencia_id=ocorrencia.id,
            acao=f"Ocorrência atualizada ({', '.join(campos_alterados)})",
            autor_id=current_user_id,
        ))
        await self._notificar_responsaveis(
            ocorrencia,
            evento_sufixo=f"atualizada:{int(ocorrencia.updated_at.timestamp())}",
            titulo="Ocorrência atualizada",
        )
        return ocorrencia

    async def mudar_status(
        self,
        ocorrencia_id: uuid.UUID,
        body: OcorrenciaStatusUpdate,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> Ocorrencia:
        ocorrencia = await self.obter(ocorrencia_id, current_user_id, perfil)
        if perfil not in (Perfil.ADMIN, Perfil.COORDENADOR, Perfil.SECRETARIA):
            raise Forbidden("Apenas coordenação e administração podem alterar o status")

        if body.status == ocorrencia.status:
            raise ValidationError("Ocorrência já está neste status")

        transicoes = STATUS_TRANSICOES_OCORRENCIA.get(ocorrencia.status, [])
        if body.status not in transicoes:
            raise ValidationError(
                f"Transição inválida: {ocorrencia.status.value} → {body.status.value}",
            )

        status_anterior = ocorrencia.status
        ocorrencia.status = body.status
        if body.status == StatusOcorrencia.RESOLVIDA:
            ocorrencia.resolvida_em = datetime.now(UTC)

        ocorrencia = await self._repo.update(ocorrencia)
        await self._repo.add_historico(OcorrenciaHistorico(
            ocorrencia_id=ocorrencia.id,
            status_anterior=status_anterior,
            status_novo=body.status,
            acao=body.observacao or f"Status alterado para {body.status.value}",
            autor_id=current_user_id,
        ))
        await self._notificar_responsaveis(
            ocorrencia,
            evento_sufixo=f"status:{body.status.value}",
            titulo=f"Ocorrência {body.status.value.replace('_', ' ')}",
        )
        return ocorrencia

    async def listar_historico(
        self,
        ocorrencia_id: uuid.UUID,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> list[OcorrenciaHistorico]:
        ocorrencia = await self.obter(ocorrencia_id, current_user_id, perfil)
        result = await self._session.execute(
            select(OcorrenciaHistorico)
            .where(OcorrenciaHistorico.ocorrencia_id == ocorrencia.id)
            .order_by(OcorrenciaHistorico.created_at),
        )
        return list(result.scalars().all())


class AvisoService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AvisoRepository(session)
        self._dest_repo = AvisoDestinatarioRepository(session)
        self._msg_repo = AvisoMensagemRepository(session)
        self._notificacao_repo = NotificacaoRepository(session)
        self._vinculo_repo = ResponsavelAlunoRepository(session)
        self._aluno_repo = AlunoRepository(session)
        self._turma_repo = TurmaRepository(session)
        self._alocacao_repo = AlocacaoRepository(session)
        self._matricula_repo = MatriculaRepository(session)

    # ── Público disponível ────────────────────────────────────────

    async def publico_disponivel(
        self, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> PublicoDisponivelResponse:
        if perfil == Perfil.RESPONSAVEL:
            raise Forbidden("Responsável não pode enviar avisos")

        if perfil == Perfil.PROFESSOR:
            turmas = await self._repo.list_turmas_publico(usuario_id)
            responsaveis = await self._repo.list_responsaveis_publico(usuario_id)
            return PublicoDisponivelResponse(
                professores=[],
                responsaveis=[PublicoPessoaResponse(**r) for r in responsaveis],
                turmas=[PublicoTurmaResponse(**t) for t in turmas],
                pode_enviar_para_professores=False,
                pode_enviar_para_todos_responsaveis=True,
            )

        if perfil in GESTORES:
            professores = await self._repo.list_professores_publico()
            responsaveis = await self._repo.list_responsaveis_publico()
            turmas = await self._repo.list_turmas_publico()
            return PublicoDisponivelResponse(
                professores=[PublicoPessoaResponse(**p) for p in professores],
                responsaveis=[PublicoPessoaResponse(**r) for r in responsaveis],
                turmas=[PublicoTurmaResponse(**t) for t in turmas],
                pode_enviar_para_professores=True,
                pode_enviar_para_todos_responsaveis=True,
            )

        raise Forbidden("Perfil sem permissão para enviar avisos")

    # ── Aviso de ausência (responsável) ───────────────────────────

    async def registrar_ausencia(
        self,
        body: AusenciaCreate,
        responsavel_id: uuid.UUID,
    ) -> AusenciaResponse:
        """Responsável avisa que o filho não vem hoje.

        Diferente de `criar`, aqui o destinatário NÃO é escolhido: é a própria
        secretaria mais os professores que têm aula com a criança no dia, resolvidos
        pela grade horária. No ensino fundamental 1 são um ou dois professores por
        turma, então o aviso chega em segundos e sem ninguém precisar seleccionar
        destinatários.

        Idempotente por (aluno, data): o botão é clicado com pressa, às vezes duas
        vezes, e o Wifi da escola derruba requisição. Reenviar devolve o aviso
        existente em vez de notificar a secretaria duas vezes.
        """
        from app.modules.schedule.service import HorarioAulaService

        # Anti-IDOR: o `aluno_id` vem do corpo, então precisa ser um filho de quem pede.
        if not await self._vinculo_repo.exists(body.aluno_id, responsavel_id):
            raise Forbidden("Você não é responsável por este aluno")

        alvo = body.data or date.today()

        existing = await self._repo.find_ausencia(body.aluno_id, alvo)
        if existing is not None:
            # Já avisado. Devolve o mesmo aviso com o estado atual dos destinatários, em
            # vez de 409: para o usuário, a intenção ("a escola sabe") já foi satisfeita.
            return await self._resposta_ausencia(existing, ja_existia=True)

        aulas = await HorarioAulaService(self._session).aulas_do_dia_para_aluno(body.aluno_id)
        if aulas.data != alvo:  # o service resolve "hoje"; para outro dia, recalcular
            aulas = await HorarioAulaService(self._session).aulas_do_dia_para_aluno(
                body.aluno_id, alvo,
            )

        matricula = await self._matricula_repo.get_active_by_aluno(body.aluno_id)
        aluno_nome = (
            matricula.aluno.nome if matricula and matricula.aluno else "o aluno"
        )
        turma_codigo = aulas.turma_codigo or (
            matricula.turma.codigo if matricula and matricula.turma else None
        )
        turno = aulas.turma_turno

        # Professores da grade do dia. Sem grade cadastrada, o aviso vai só para a
        # secretaria — que é quem cobra o cadastro — e a resposta diz isso explicitamente
        # em vez de o responsável achar que avisou a professora.
        professores = list(dict.fromkeys(aulas.professores_ids))

        secretaria = await self._usuarios_por_perfil([Perfil.SECRETARIA])

        # O autor também entra como destinatário: sem isso ele não consegue ver o
        # próprio aviso na caixa "recebidos", que é onde ele procura depois de clicar.
        destinos: dict[uuid.UUID, uuid.UUID | None] = {responsavel_id: body.aluno_id}
        for uid in [*secretaria, *professores]:
            destinos.setdefault(uid, body.aluno_id)

        titulo = f"Ausência — {aluno_nome}"
        partes = [
            f"{aluno_nome} não virá à escola em {alvo.strftime('%d/%m/%Y')}.",
        ]
        if turma_codigo:
            partes.append(f"Turma {turma_codigo}.")
        if turno:
            partes.append(f"Turno {turno}.")
        if body.motivo:
            partes.append(f"Motivo informado: {body.motivo.strip()}")
        partes.append(
            "Aviso enviado pelo responsável. A chamada pode ser registrada normalmente."
        )

        aviso = await self._repo.create(Aviso(
            titulo=titulo,
            mensagem=" ".join(partes),
            tipo=TipoAviso.AUSENCIA,
            # Sempre alta: ausência é a única informação que a professora precisa ter
            # antes de passar a lista, e a cor do cartão no app do responsável depende
            # disso para não ficar escondida entre os avisos informativos.
            prioridade=PrioridadeAviso.ALTA,
            permite_respostas=True,
            destinatario_aluno_id=body.aluno_id,
            destinatario_turma_id=(
                matricula.turma_id if matricula and len(destinos) <= 2 else None
            ),
            criado_por=responsavel_id,
        ))
        await self._session.refresh(aviso, attribute_names=["criador"])
        await self._materializar_destinatarios(aviso, destinos)
        await self._session.refresh(aviso, attribute_names=["destinatarios"])

        return await self._resposta_ausencia(
            aviso,
            secretaria=len(secretaria),
            professores=professores,
            aulas=aulas,
            matricula=matricula,
        )

    async def _resposta_ausencia(
        self,
        aviso: Aviso,
        secretaria: int | None = None,
        professores: list[uuid.UUID] | None = None,
        aulas=None,
        matricula=None,
        ja_existia: bool = False,
    ) -> AusenciaResponse:
        """Monta o retorno a partir do aviso já gravado.

        Existe para o caminho idempotente devolver o MESMO formato do caminho novo, com
        os destinatários reais — sem isso o segundo clique responderia 201 com zeros e o
        cliente pintaria "ninguém notificado".
        """
        dests = await self._dest_repo.list_by_aviso(aviso.id)
        ids_secretaria = set(await self._usuarios_por_perfil([Perfil.SECRETARIA]))

        if secretaria is None or professores is None:
            secretaria = sum(1 for d in dests if d.usuario_id in ids_secretaria)
            if aulas is not None:
                professores = list(dict.fromkeys(aulas.professores_ids))
            else:
                # Recalcula pelos destinatários que não são secretaria nem o autor.
                professores = [
                    d.usuario_id
                    for d in dests
                    if d.usuario_id not in ids_secretaria
                    and d.usuario_id != aviso.criado_por
                ]

        nomes: list[str] = []
        for d in dests:
            if d.usuario_id in ids_secretaria or d.usuario_id == aviso.criado_por:
                continue
            if d.usuario and d.usuario.nome not in nomes:
                nomes.append(d.usuario.nome)

        aluno_nome = matricula.aluno.nome if matricula and matricula.aluno else None
        if aluno_nome is None:
            aluno_nome = await self._aluno_repo.get_by_id(aviso.destinatario_aluno_id)
            aluno_nome = aluno_nome.nome if aluno_nome else None

        return AusenciaResponse(
            aviso_id=aviso.id,
            aluno_id=aviso.destinatario_aluno_id,
            aluno_nome=aluno_nome,
            data=aviso.publicado_em.date(),
            turma_codigo=aviso.destinatario_turma.codigo
            if aviso.destinatario_turma
            else None,
            turno=aviso.destinatario_turma.turno.value if aviso.destinatario_turma else None,
            secretaria=len(ids_secretaria) if secretaria == 0 else secretaria,
            professores=len(professores),
            professores_nomes=nomes,
            sem_grade=not professores,
            ja_existia=ja_existia,
        )

    async def _usuarios_por_perfil(self, perfis: list[Perfil]) -> list[uuid.UUID]:
        from app.modules.users.repository import UsuarioRepository

        usuarios = await UsuarioRepository(self._session).get_by_perfis(perfis)
        return [u.id for u in usuarios]

    # ── Criação ───────────────────────────────────────────────────

    async def criar(
        self,
        body: AvisoCreate,
        criado_por: uuid.UUID,
        perfil: Perfil,
    ) -> Aviso:
        if perfil == Perfil.RESPONSAVEL:
            raise Forbidden("Responsável não pode criar avisos")

        destinos = await self._resolver_destinatarios(body, criado_por, perfil)
        if not destinos:
            raise ValidationError(
                "Selecione pelo menos um destinatário autorizado para o aviso",
            )

        aviso = Aviso(
            titulo=body.titulo,
            mensagem=body.mensagem,
            tipo=body.tipo,
            prioridade=body.prioridade,
            permite_respostas=body.permite_respostas,
            destinatario_aluno_id=body.destinatario_aluno_id,
            destinatario_turma_id=(
                body.destinatario_turma_id
                if body.destinatario_turma_id
                else (body.turma_ids[0] if len(body.turma_ids) == 1 else None)
            ),
            criado_por=criado_por,
        )
        aviso = await self._repo.create(aviso)
        # Carrega o criador antes de notificar: `_notificar_destinatario` usa
        # `aviso.criador.nome` e o lazy load fora do greenlet quebraria a request.
        await self._session.refresh(aviso, attribute_names=["criador"])
        await self._materializar_destinatarios(aviso, destinos)
        # Carrega os destinatários para serialização segura (sem lazy load).
        await self._session.refresh(aviso, attribute_names=["destinatarios"])
        return aviso

    async def _resolver_destinatarios(
        self,
        body: AvisoCreate | AvisoUpdate,
        autor_id: uuid.UUID,
        perfil: Perfil,
    ) -> dict[uuid.UUID, uuid.UUID | None]:
        """Resolve e valida os destinatários autorizados para o remetente.

        Retorna um mapa usuario_id -> aluno_id (contexto opcional). IDs enviados
        pelo cliente nunca são aceitos sem validação de vínculo.
        """
        destinos: dict[uuid.UUID, uuid.UUID | None] = {}
        turma_ids = set(body.turma_ids or [])
        professor_ids = set(body.professor_ids or [])
        responsavel_ids = set(body.responsavel_ids or [])
        para_professores = bool(body.para_professores)
        para_responsaveis = bool(body.para_responsaveis)
        aluno_legado = getattr(body, "destinatario_aluno_id", None)
        turma_legado = getattr(body, "destinatario_turma_id", None)
        if turma_legado:
            turma_ids.add(turma_legado)

        # Valida ids enviados pelo cliente antes de qualquer resolução.
        if aluno_legado is not None:
            aluno = await self._aluno_repo.get_by_id(aluno_legado)
            if aluno is None:
                raise NotFound("Aluno destinatário não encontrado")
        for turma_id in turma_ids:
            turma = await self._turma_repo.get_by_id(turma_id)
            if turma is None:
                raise NotFound("Turma destinatária não encontrada")

        # Sem público declarado: gestores enviam para todos os responsáveis
        # (compatível com o fluxo anterior de "aviso global").
        sem_publico = not (
            para_professores or professor_ids or para_responsaveis
            or responsavel_ids or turma_ids or aluno_legado
        )
        if sem_publico:
            if perfil in GESTORES:
                para_responsaveis = True
            else:
                raise ValidationError(
                    "Selecione os destinatários autorizados para este aviso",
                )

        if perfil == Perfil.PROFESSOR:
            if para_professores or professor_ids:
                raise Forbidden("Professor não pode enviar avisos para professores")

            minhas_turmas = set(await self._repo.list_turmas_do_professor(autor_id))
            invalidas = turma_ids - minhas_turmas
            if invalidas:
                raise Forbidden("Você só pode enviar avisos para as suas turmas")

            if responsavel_ids:
                autorizados = await self._repo.responsaveis_do_professor_por_responsavel(
                    autor_id, list(responsavel_ids),
                )
                nao_autorizados = responsavel_ids - autorizados
                if nao_autorizados:
                    raise Forbidden(
                        "Há responsáveis selecionados fora das suas turmas",
                    )
                for rid in responsavel_ids:
                    destinos[rid] = None

            if para_responsaveis:
                turma_ids |= minhas_turmas

            if aluno_legado:
                if not await self._alocacao_repo.professor_leciona_aluno(
                    autor_id, aluno_legado,
                ):
                    raise Forbidden("Este aluno não pertence às suas turmas")
                for rid in await self._repo.list_responsaveis_do_aluno(aluno_legado):
                    destinos[rid] = aluno_legado
        else:
            if para_professores:
                for p in await self._repo.list_professores_publico():
                    destinos[p["id"]] = None
            if professor_ids:
                validos = {p["id"] for p in await self._repo.list_professores_publico()}
                invalidos = professor_ids - validos
                if invalidos:
                    raise ValidationError(
                        "Professor(es) selecionado(s) não encontrado(s) ou inativo(s)",
                    )
                for pid in professor_ids:
                    destinos[pid] = None

            if para_responsaveis:
                for rid, aid in await self._repo.list_todos_responsaveis():
                    destinos.setdefault(rid, aid)

            if responsavel_ids:
                validos_resp = {
                    r["id"] for r in await self._repo.list_responsaveis_publico()
                }
                invalidos = responsavel_ids - validos_resp
                if invalidos:
                    raise ValidationError("Responsável(is) selecionado(s) não encontrado(s)")
                for rid in responsavel_ids:
                    destinos.setdefault(rid, None)

            if aluno_legado:
                responsaveis_aluno = await self._repo.list_responsaveis_do_aluno(aluno_legado)
                if not responsaveis_aluno:
                    raise ValidationError("Aluno sem responsáveis vinculados")
                for rid in responsaveis_aluno:
                    destinos[rid] = aluno_legado

        if turma_ids:
            for rid, aid in await self._repo.list_responsaveis_das_turmas(list(turma_ids)):
                destinos.setdefault(rid, aid)

        return destinos

    async def _materializar_destinatarios(
        self,
        aviso: Aviso,
        destinos: dict[uuid.UUID, uuid.UUID | None],
    ) -> list[AvisoDestinatario]:
        criados: list[AvisoDestinatario] = []
        for usuario_id, aluno_id in destinos.items():
            existente = await self._dest_repo.get_by_aviso_usuario(aviso.id, usuario_id)
            if existente is not None:
                continue
            destinatario = AvisoDestinatario(
                aviso_id=aviso.id,
                usuario_id=usuario_id,
                aluno_id=aluno_id,
            )
            await self._dest_repo.create(destinatario)
            await self._notificar_destinatario(aviso, usuario_id)
            criados.append(destinatario)
        return criados

    async def _notificar_destinatario(self, aviso: Aviso, usuario_id: uuid.UUID) -> None:
        from app.core.notifications import NotificationDispatcher

        autor_nome = aviso.criador.nome if aviso.criador else "Sistema"
        resumo = aviso.mensagem.strip().replace("\n", " ")[:140]
        await NotificationDispatcher(self._session).dispatch(
            usuario_id=usuario_id,
            titulo="Novo aviso",
            corpo=f"{autor_nome} enviou um novo aviso: {aviso.titulo}",
            dados={
                "aviso_id": str(aviso.id),
                "autor_nome": autor_nome,
                "resumo": resumo,
                "permite_respostas": aviso.permite_respostas,
                # Prioridade vai no payload (e não numa coluna nova) porque a
                # notificacao é um espelho do aviso: ela carrega `entidade_tipo`/
                # `entidade_id` e o cliente ja sabe onde buscar o resto. Aqui ela
                # serve para pintar a notificacao em tempo real, que chega pelo SSE
                # sem o cliente ter aberto o aviso ainda.
                "prioridade": aviso.prioridade.value,
                "tipo": aviso.tipo.value,
            },
            canal="inapp",
            tipo=TipoNotificacao.AVISO,
            entidade_tipo="aviso",
            entidade_id=aviso.id,
            evento_key=f"aviso:{aviso.id}:{usuario_id}",
        )

    # ── Consultas ─────────────────────────────────────────────────

    def _caixa_padrao(self, perfil: Perfil) -> str:
        if perfil == Perfil.ADMIN:
            return "global"
        if perfil in (Perfil.COORDENADOR, Perfil.SECRETARIA):
            return "todos"
        return "recebidos"

    async def listar(
        self,
        current_user_id: uuid.UUID,
        perfil: Perfil,
        caixa: str | None = None,
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
    ) -> tuple[list[Aviso], int, dict[uuid.UUID, AvisoDestinatario]]:
        caixa = (caixa or self._caixa_padrao(perfil)).lower()
        if caixa == "global" and perfil != Perfil.ADMIN:
            raise Forbidden("Somente administradores podem ver todos os avisos")
        if caixa not in ("recebidos", "enviados", "todos", "global"):
            raise ValidationError("Caixa inválida")

        if data_inicio and data_fim and data_inicio > data_fim:
            raise ValidationError("A data inicial não pode ser depois da final")

        # O filtro por aluno é o único que depende do papel, porque é o único que
        # atravessa a fronteira do "meu": um responsável só pode filtrar pelos próprios
        # filhos, qualquer outro papel filtra pela escola. Sem isto, o `aluno_id` do
        # query param viraria um oráculo — o conjunto de avisos existiria para todos.
        if aluno_id is not None and perfil == Perfil.RESPONSAVEL:
            if not await self._vinculo_repo.exists(aluno_id, current_user_id):
                raise Forbidden("Você não é responsável por este aluno")

        # Os dois caminhos viram o mesmo argumento: o repositório trata "global" como
        # o caso sem recorte por usuário.
        itens, total = await self._repo.search_avisos(
            caixa,
            current_user_id,
            status=status,
            busca=busca,
            prioridade=prioridade,
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            turma_id=turma_id,
            aluno_id=aluno_id,
            leitura=leitura,
            ordem=ordem,
            page=page,
            size=size,
        )

        meus: dict[uuid.UUID, AvisoDestinatario] = {}
        if itens:
            registros = await self._dest_repo.list_by_aviso_ids_usuario(
                [a.id for a in itens], current_user_id,
            )
            meus = {r.aviso_id: r for r in registros}
        return itens, total, meus

    async def obter(
        self,
        aviso_id: uuid.UUID,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> Aviso:
        aviso = await self._repo.get_by_id(aviso_id)
        if aviso is None:
            raise NotFound("Aviso não encontrado")
        if await self._pode_ver(aviso, current_user_id, perfil):
            return aviso
        raise Forbidden("Você não possui acesso a este aviso")

    async def _pode_ver(
        self, aviso: Aviso, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> bool:
        if perfil in GESTORES:
            return True
        if aviso.criado_por == usuario_id:
            return True
        destinatario = await self._dest_repo.get_by_aviso_usuario(aviso.id, usuario_id)
        return destinatario is not None

    async def _pode_gerenciar(
        self, aviso: Aviso, usuario_id: uuid.UUID, perfil: Perfil,
    ) -> bool:
        return perfil in GESTORES or aviso.criado_por == usuario_id

    async def obter_destinatario(
        self, aviso_id: uuid.UUID, usuario_id: uuid.UUID,
    ) -> AvisoDestinatario | None:
        return await self._dest_repo.get_by_aviso_usuario(aviso_id, usuario_id)

    # ── Edição ────────────────────────────────────────────────────

    async def atualizar(
        self,
        aviso_id: uuid.UUID,
        body: AvisoUpdate,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> Aviso:
        aviso = await self.obter(aviso_id, current_user_id, perfil)
        if not await self._pode_gerenciar(aviso, current_user_id, perfil):
            raise Forbidden("Você não pode editar este aviso")

        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            return aviso

        # Campos de público exigem nova resolução; texto/flag são diretos.
        publico_keys = {
            "para_professores", "professor_ids",
            "para_responsaveis", "responsavel_ids", "turma_ids",
        }
        publico_data = {k: update_data.pop(k) for k in list(update_data) if k in publico_keys}

        for campo, valor in update_data.items():
            setattr(aviso, campo, valor)

        aviso = await self._repo.update(aviso)

        if publico_data:
            publico_body = AvisoUpdate(**publico_data)
            destinos = await self._resolver_destinatarios(
                publico_body, current_user_id, perfil,
            )
            if destinos:
                await self._materializar_destinatarios(aviso, destinos)
        return aviso

    async def arquivar(
        self,
        aviso_id: uuid.UUID,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> Aviso:
        aviso = await self.obter(aviso_id, current_user_id, perfil)
        if not await self._pode_gerenciar(aviso, current_user_id, perfil):
            raise Forbidden("Você não pode arquivar este aviso")
        aviso.status = StatusAviso.ARQUIVADO
        return await self._repo.update(aviso)

    # ── Leitura ───────────────────────────────────────────────────

    async def marcar_lido(
        self,
        aviso_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> AvisoDestinatario:
        aviso = await self._repo.get_by_id(aviso_id)
        if aviso is None or aviso.status != StatusAviso.PUBLICADO:
            raise NotFound("Aviso não encontrado")

        destinatario = await self._dest_repo.get_by_aviso_usuario(aviso_id, usuario_id)
        if destinatario is None:
            raise Forbidden("Você não é destinatário deste aviso")

        if destinatario.lido_em is None:
            destinatario.lido_em = datetime.now(UTC)
            destinatario = await self._dest_repo.update(destinatario)
        # A leitura do aviso marca as notificações correspondentes como lidas.
        await self._notificacao_repo.marcar_lidas_por_entidade(
            usuario_id, "aviso", aviso_id,
        )
        return destinatario

    async def listar_destinatarios(
        self,
        aviso_id: uuid.UUID,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> list[AvisoDestinatario]:
        aviso = await self.obter(aviso_id, current_user_id, perfil)
        if not await self._pode_gerenciar(aviso, current_user_id, perfil):
            raise Forbidden("Você não pode ver os destinatários deste aviso")
        return await self._dest_repo.list_by_aviso(aviso_id)

    def estatisticas(self, destinatarios: list[AvisoDestinatario]) -> AvisoEstatisticasResponse:
        lidos = sum(1 for d in destinatarios if d.lido_em is not None)
        total = len(destinatarios)
        return AvisoEstatisticasResponse(
            total=total, lidos=lidos, nao_lidos=total - lidos,
        )

    # ── Thread/conversa ───────────────────────────────────────────

    async def responder(
        self,
        aviso_id: uuid.UUID,
        body,
        autor_id: uuid.UUID,
        perfil: Perfil,
    ) -> AvisoMensagem:
        aviso = await self._repo.get_by_id(aviso_id)
        if aviso is None:
            raise NotFound("Aviso não encontrado")
        if aviso.status != StatusAviso.PUBLICADO:
            raise Conflict("Aviso arquivado não aceita novas mensagens")
        if not aviso.permite_respostas:
            raise ValidationError("Este aviso não permite respostas")

        destinatario_registro = await self._dest_repo.get_by_aviso_usuario(aviso_id, autor_id)
        is_autor = aviso.criado_por == autor_id
        if not is_autor and destinatario_registro is None:
            raise Forbidden("Você não participa desta conversa")

        if is_autor:
            if body.destinatario_id is None:
                raise ValidationError("Informe o destinatário da resposta")
            alvo = await self._dest_repo.get_by_aviso_usuario(aviso_id, body.destinatario_id)
            if alvo is None:
                raise ValidationError("Destinatário não pertence a este aviso")
            destinatario_id = body.destinatario_id
        else:
            destinatario_id = body.destinatario_id or aviso.criado_por
            if destinatario_id != aviso.criado_por:
                raise Forbidden("Você só pode responder ao autor do aviso")

        mensagem = AvisoMensagem(
            aviso_id=aviso_id,
            autor_id=autor_id,
            destinatario_id=destinatario_id,
            conteudo=body.conteudo,
        )
        mensagem = await self._msg_repo.create(mensagem)
        # Carrega autor/destinatário para serialização segura (sem lazy load).
        await self._session.refresh(mensagem, attribute_names=["autor", "destinatario"])

        from app.core.notifications import NotificationDispatcher

        autor_nome = mensagem.autor.nome if mensagem.autor else "Usuário"
        await NotificationDispatcher(self._session).dispatch(
            usuario_id=destinatario_id,
            titulo="Nova mensagem",
            corpo=f"{autor_nome}: {body.conteudo.strip()[:140]}",
            dados={
                "aviso_id": str(aviso_id),
                "mensagem_id": str(mensagem.id),
                "autor_nome": autor_nome,
            },
            canal="inapp",
            tipo=TipoNotificacao.AVISO,
            entidade_tipo="aviso",
            entidade_id=aviso_id,
            evento_key=f"aviso-resposta:{mensagem.id}:{destinatario_id}",
        )
        return mensagem

    async def listar_mensagens(
        self,
        aviso_id: uuid.UUID,
        current_user_id: uuid.UUID,
        perfil: Perfil,
    ) -> list[AvisoMensagem]:
        aviso = await self.obter(aviso_id, current_user_id, perfil)
        if aviso.criado_por == current_user_id or perfil == Perfil.ADMIN:
            return await self._msg_repo.list_by_aviso(aviso_id)
        return await self._msg_repo.list_visiveis_para(aviso_id, current_user_id)

    async def marcar_mensagem_lida(
        self,
        aviso_id: uuid.UUID,
        mensagem_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> AvisoMensagem:
        mensagem = await self._msg_repo.get_by_id(mensagem_id)
        if mensagem is None or mensagem.aviso_id != aviso_id:
            raise NotFound("Mensagem não encontrada")
        if mensagem.destinatario_id != usuario_id:
            raise Forbidden("Você não é destinatário desta mensagem")
        if mensagem.lida_em is None:
            mensagem.lida_em = datetime.now(UTC)
            mensagem = await self._msg_repo.update(mensagem)
        return mensagem

    # ── Escalonamento ─────────────────────────────────────────────

    async def escalar_nao_lidos(self, horas: int) -> int:
        """Escalona avisos publicados há mais de X horas e ainda não lidos.

        Marca `escalado_em` no destinatário (uma única vez) e notifica a
        coordenação e a administração. Notificações são idempotentes.
        """
        if horas <= 0:
            return 0

        cutoff = datetime.now(UTC) - timedelta(hours=horas)
        avisos = await self._repo.list_publicados_fora_prazo(cutoff)
        if not avisos:
            return 0

        from app.modules.users.repository import UsuarioRepository

        usuarios = await UsuarioRepository(self._session).get_by_perfis(
            [Perfil.ADMIN, Perfil.COORDENADOR],
        )
        agora = datetime.now(UTC)
        escalados = 0

        for aviso in avisos:
            leituras = await self._dest_repo.list_nao_lidas_sem_escalada([aviso.id])
            if not leituras:
                continue

            for leitura in leituras:
                leitura.escalado_em = agora
                await self._dest_repo.update(leitura)

            mensagem = (
                f"{len(leituras)} destinatário(s) ainda não leram o aviso: {aviso.titulo}"
            )
            for usuario in usuarios:
                await NotificationService(self._session).criar(
                    destinatario_id=usuario.id,
                    tipo=TipoNotificacao.AVISO,
                    titulo="Aviso não lido — escalonamento",
                    mensagem=mensagem,
                    entidade_tipo="aviso",
                    entidade_id=aviso.id,
                    evento_key=f"aviso-escalado:{aviso.id}:{usuario.id}",
                )
            escalados += 1

        return escalados


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificacaoRepository(session)
        self._push_repo = PushTokenRepository(session)
        self._pref_repo = PreferenciaNotificacaoRepository(session)

    async def criar(
        self,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        canal: str = "inapp",
        entidade_tipo: str | None = None,
        entidade_id: uuid.UUID | None = None,
        evento_key: str | None = None,
        dados: dict | None = None,
    ) -> Notificacao | None:
        notificacao, _criada = await self.criar_detalhado(
            destinatario_id=destinatario_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            canal=canal,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            evento_key=evento_key,
            dados=dados,
        )
        return notificacao

    async def criar_detalhado(
        self,
        destinatario_id: uuid.UUID,
        tipo: TipoNotificacao,
        titulo: str,
        mensagem: str,
        canal: str = "inapp",
        entidade_tipo: str | None = None,
        entidade_id: uuid.UUID | None = None,
        evento_key: str | None = None,
        dados: dict | None = None,
    ) -> tuple[Notificacao | None, bool]:
        """Cria a notificação e informa se ela é nova (para realtime/push)."""
        notificacao = Notificacao(
            destinatario_id=destinatario_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            canal=canal,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            dados=dados,
        )
        return await self._repo.create(notificacao, evento_key=evento_key)

    async def listar(
        self,
        destinatario_id: uuid.UUID,
        apenas_nao_lidas: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Notificacao], int]:
        return await self._repo.list_by_destinatario(
            destinatario_id=destinatario_id,
            apenas_nao_lidas=apenas_nao_lidas,
            page=page,
            size=size,
        )

    async def contar_nao_lidas(self, destinatario_id: uuid.UUID) -> int:
        return await self._repo.count_nao_lidas(destinatario_id)

    async def marcar_lida(
        self,
        notificacao_id: uuid.UUID,
        destinatario_id: uuid.UUID,
    ) -> Notificacao:
        notificacao = await self._repo.get_by_id(notificacao_id)
        if notificacao is None:
            raise NotFound("Notificação não encontrada")
        if notificacao.destinatario_id != destinatario_id:
            raise Forbidden("Você não possui acesso a esta notificação")
        if not notificacao.lida:
            notificacao = await self._repo.marcar_lida(notificacao)
        return notificacao

    async def marcar_todas_lidas(self, destinatario_id: uuid.UUID) -> int:
        return await self._repo.marcar_todas_lidas(destinatario_id)

    # ── Push tokens ──────────────────────────────────────────────

    async def registrar_push_token(
        self,
        usuario_id: uuid.UUID,
        token: str,
        plataforma: str = "expo",
    ) -> PushToken:
        return await self._push_repo.upsert(usuario_id, token, plataforma)

    async def remover_push_token(self, usuario_id: uuid.UUID, token: str) -> None:
        await self._push_repo.remove(usuario_id, token)

    # ── Preferências de canal ────────────────────────────────────

    async def obter_preferencias(
        self, usuario_id: uuid.UUID,
    ) -> dict[TipoNotificacao, bool]:
        """Mapa tipo → e-mail habilitado.

        Tipos sem linha não aparecem no mapa; o app trata ausência como
        desligado, que é o mesmo comportamento do banco.
        """
        registros = await self._pref_repo.list_by_usuario(usuario_id)
        return {r.tipo: r.email for r in registros}

    async def definir_preferencia(
        self,
        usuario_id: uuid.UUID,
        tipo: TipoNotificacao,
        email: bool,
    ) -> PreferenciaNotificacao:
        return await self._pref_repo.upsert(usuario_id, tipo, email)

    async def email_habilitado(
        self, usuario_id: uuid.UUID, tipo: TipoNotificacao,
    ) -> bool:
        return await self._pref_repo.email_habilitado(usuario_id, tipo)
