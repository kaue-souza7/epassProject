import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.academic_years.models import AnoLetivo
from app.modules.allocations.models import Alocacao
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.auth.models import Sessao
from app.modules.classes.models import Turma
from app.modules.enrollments.models import Matricula
from app.modules.series.models import Serie
from app.modules.students.models import Aluno, ResponsavelAluno
from app.modules.subjects.models import Disciplina
from app.modules.teachers.models import ProfessorProfile
from app.modules.users.models import Usuario
from app.shared.enums import (
    Parentesco,
    Perfil,
    StatusFrequencia,
    StatusMatricula,
    TipoAvaliacao,
    Turno,
)

PASSWORD = "test123"
_PASSWORD_HASH: str | None = None
_serie_counter = 0
_disciplina_counter = 0
_ano_counter = 0


def _get_hash() -> str:
    global _PASSWORD_HASH
    if _PASSWORD_HASH is None:
        _PASSWORD_HASH = hash_password(PASSWORD)
    return _PASSWORD_HASH


async def create_usuario(
    session: AsyncSession,
    nome: str = "Test User",
    email: str | None = None,
    perfil: Perfil = Perfil.ADMIN,
    ativo: bool = True,
) -> Usuario:
    usuario = Usuario(
        nome=nome,
        email=email or f"{uuid.uuid4().hex[:8]}@test.com",
        senha_hash=_get_hash(),
        perfil=perfil,
        ativo=ativo,
    )
    session.add(usuario)
    await session.flush()
    return usuario


async def create_ano_letivo(
    session: AsyncSession,
    ano: int | None = None,
    ativo: bool = True,
) -> AnoLetivo:
    global _ano_counter
    _ano_counter += 1
    ano = ano or (2024 + _ano_counter)
    obj = AnoLetivo(
        ano=ano,
        data_inicio=date(ano, 2, 1),
        data_fim=date(ano, 12, 15),
        ativo=ativo,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_serie(
    session: AsyncSession,
    numero: int | None = None,
    nome: str | None = None,
) -> Serie:
    global _serie_counter
    _serie_counter += 1
    numero = numero if numero is not None else _serie_counter
    nome = nome or f"{numero}º Ano"
    obj = Serie(numero=numero, nome=nome, descricao=None, ativo=True)
    session.add(obj)
    await session.flush()
    return obj


async def create_turma(
    session: AsyncSession,
    codigo: str = "A",
    nome: str | None = "Turma A",
    serie_id: uuid.UUID | None = None,
    ano_letivo_id: uuid.UUID | None = None,
    turno: Turno = Turno.MANHA,
    vagas_total: int = 30,
) -> Turma:
    if serie_id is None:
        serie = await create_serie(session)
        serie_id = serie.id
    if ano_letivo_id is None:
        ano = await create_ano_letivo(session)
        ano_letivo_id = ano.id
    obj = Turma(
        codigo=codigo,
        nome=nome,
        serie_id=serie_id,
        ano_letivo_id=ano_letivo_id,
        turno=turno,
        vagas_total=vagas_total,
        ativo=True,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_aluno(
    session: AsyncSession,
    nome: str = "João Aluno",
    cpf: str | None = None,
) -> Aluno:
    obj = Aluno(
        nome=nome,
        data_nascimento=date(2010, 5, 10),
        cpf=cpf or None,
        rg=None,
        endereco=None,
        telefone=None,
        email=None,
        data_entrada=date(2026, 2, 1),
        ativo=True,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_responsavel_aluno(
    session: AsyncSession,
    aluno_id: uuid.UUID,
    responsavel_id: uuid.UUID,
    parentesco: Parentesco = Parentesco.MAE,
) -> ResponsavelAluno:
    obj = ResponsavelAluno(
        aluno_id=aluno_id,
        responsavel_id=responsavel_id,
        parentesco=parentesco,
        responsavel_financeiro=True,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_disciplina(
    session: AsyncSession,
    codigo: str | None = None,
    nome: str | None = None,
) -> Disciplina:
    global _disciplina_counter
    _disciplina_counter += 1
    codigo = codigo or f"MAT{_disciplina_counter}"
    nome = nome or f"Matemática {_disciplina_counter}"
    obj = Disciplina(codigo=codigo, nome=nome, descricao=None, ativo=True)
    session.add(obj)
    await session.flush()
    return obj


async def create_professor(
    session: AsyncSession,
    usuario_id: uuid.UUID | None = None,
) -> ProfessorProfile:
    if usuario_id is None:
        user = await create_usuario(session, perfil=Perfil.PROFESSOR)
        usuario_id = user.id
    obj = ProfessorProfile(
        usuario_id=usuario_id,
        formacao_principal="Licenciatura",
        matricula_funcional=f"MF{uuid.uuid4().hex[:6]}",
        data_contratacao=date(2024, 1, 1),
        observacoes=None,
        ativo=True,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_alocacao(
    session: AsyncSession,
    professor_id: uuid.UUID | None = None,
    turma_id: uuid.UUID | None = None,
    disciplina_id: uuid.UUID | None = None,
) -> Alocacao:
    if professor_id is None:
        prof = await create_professor(session)
        professor_id = prof.usuario_id
    if turma_id is None:
        turma = await create_turma(session)
        turma_id = turma.id
    if disciplina_id is None:
        disc = await create_disciplina(session)
        disciplina_id = disc.id
    obj = Alocacao(
        professor_id=professor_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        data_inicio=date(2026, 2, 1),
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_matricula(
    session: AsyncSession,
    aluno_id: uuid.UUID | None = None,
    turma_id: uuid.UUID | None = None,
    status: StatusMatricula = StatusMatricula.ATIVA,
) -> Matricula:
    if aluno_id is None:
        aluno = await create_aluno(session)
        aluno_id = aluno.id
    if turma_id is None:
        turma = await create_turma(session)
        turma_id = turma.id
    obj = Matricula(
        aluno_id=aluno_id,
        turma_id=turma_id,
        data_matricula=date(2026, 2, 1),
        status=status,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_avaliacao(
    session: AsyncSession,
    alocacao_id: uuid.UUID | None = None,
    titulo: str = "Prova Bimestral",
    bimestre: int = 1,
    peso: int = 1,
    nota_maxima: float = 10.0,
) -> Avaliacao:
    if alocacao_id is None:
        aloc = await create_alocacao(session)
        alocacao_id = aloc.id
    from decimal import Decimal
    obj = Avaliacao(
        alocacao_id=alocacao_id,
        titulo=titulo,
        tipo=TipoAvaliacao.PROVA,
        peso=peso,
        nota_maxima=Decimal(str(nota_maxima)),
        bimestre=bimestre,
        data_aplicacao=date(2026, 3, 15),
        observacoes=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_nota(
    session: AsyncSession,
    avaliacao_id: uuid.UUID,
    matricula_id: uuid.UUID,
    valor: float = 8.0,
) -> Nota:
    from decimal import Decimal
    obj = Nota(
        avaliacao_id=avaliacao_id,
        matricula_id=matricula_id,
        valor=Decimal(str(valor)),
        observacoes=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_chamada(
    session: AsyncSession,
    alocacao_id: uuid.UUID | None = None,
    data_hora_aula: datetime | None = None,
) -> Chamada:
    if alocacao_id is None:
        aloc = await create_alocacao(session)
        alocacao_id = aloc.id
    if data_hora_aula is None:
        data_hora_aula = datetime.now(UTC).replace(tzinfo=None)
    obj = Chamada(
        alocacao_id=alocacao_id,
        data_hora_aula=data_hora_aula,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_frequencia(
    session: AsyncSession,
    chamada_id: uuid.UUID,
    matricula_id: uuid.UUID,
    status: StatusFrequencia = StatusFrequencia.PRESENTE,
) -> Frequencia:
    obj = Frequencia(
        chamada_id=chamada_id,
        matricula_id=matricula_id,
        status=status,
        observacoes=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_sessao(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    jti: str | None = None,
    expires_at: datetime | None = None,
    revoked: bool = False,
) -> Sessao:
    if jti is None:
        jti = uuid.uuid4().hex
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(days=7)
    obj = Sessao(
        usuario_id=usuario_id,
        refresh_token_jti=jti,
        expires_at=expires_at,
        revoked_at=datetime.now(UTC) if revoked else None,
    )
    session.add(obj)
    await session.flush()
    return obj


# ---------------------------------------------------------------------------
# Fábricas das áreas cobertas pela Atena além de nota/frequência
# ---------------------------------------------------------------------------
# Estas existem porque os context builders consultam essas tabelas. Sem elas,
# testar um builder significaria montar SQL à mão dentro do teste — e o teste
# passaria a dizer mais sobre o SQL do que sobre o comportamento.


async def create_configuracao_academica(
    session: AsyncSession,
    ano_letivo_id: uuid.UUID | None = None,
    media_aprovacao: float = 6.0,
    frequencia_minima: float = 75.0,
):
    from app.modules.academic_config.models import ConfiguracaoAcademica

    if ano_letivo_id is None:
        ano = await create_ano_letivo(session)
        ano_letivo_id = ano.id
    from decimal import Decimal

    obj = ConfiguracaoAcademica(
        ano_letivo_id=ano_letivo_id,
        media_aprovacao=Decimal(str(media_aprovacao)),
        frequencia_minima=Decimal(str(frequencia_minima)),
        possui_recuperacao=True,
        media_minima_recuperacao=Decimal("4.00"),
        quantidade_periodos=4,
        ativo=True,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_wallet(
    session: AsyncSession,
    aluno_id: uuid.UUID,
    saldo: float = 0.0,
    status=None,
):
    from decimal import Decimal

    from app.modules.financial.models import Wallet
    from app.shared.enums import StatusCarteira

    obj = Wallet(
        aluno_id=aluno_id,
        saldo=Decimal(str(saldo)),
        status=status or StatusCarteira.ATIVA,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_movimentacao(
    session: AsyncSession,
    wallet_id: uuid.UUID,
    valor: float = 10.0,
    tipo=None,
    descricao: str | None = None,
    criado_por: uuid.UUID | None = None,
):
    from decimal import Decimal

    from app.modules.financial.models import Movimentacao, Wallet
    from app.shared.enums import TipoMovimentacao

    wallet = await session.get(Wallet, wallet_id)
    anterior = wallet.saldo
    tipo = tipo or TipoMovimentacao.CONSUMO

    # Recarga soma, consumo subtrai, estorno devolve. `saldo_anterior` e
    # `saldo_posterior` são mantidos coerentes porque a IA os lê no extrato.
    if tipo == TipoMovimentacao.CONSUMO:
        saldo = anterior - Decimal(str(valor))
    else:
        saldo = anterior + Decimal(str(valor))
    wallet.saldo = saldo

    obj = Movimentacao(
        wallet_id=wallet_id,
        tipo=tipo,
        valor=Decimal(str(valor)),
        saldo_anterior=anterior,
        saldo_posterior=saldo,
        descricao=descricao,
        criado_por=criado_por,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_ocorrencia(
    session: AsyncSession,
    aluno_id: uuid.UUID | None = None,
    turma_id: uuid.UUID | None = None,
    titulo: str = "Ocorrência",
    status=None,
    severidade=None,
    criado_por: uuid.UUID | None = None,
):
    from app.modules.communication.models import Ocorrencia
    from app.shared.enums import SeveridadeOcorrencia, StatusOcorrencia

    if criado_por is None:
        user = await create_usuario(session, perfil=Perfil.ADMIN)
        criado_por = user.id

    obj = Ocorrencia(
        aluno_id=aluno_id,
        turma_id=turma_id,
        titulo=titulo,
        descricao="Descrição da ocorrência",
        tipo="comportamento",
        severidade=severidade or SeveridadeOcorrencia.BAIXA,
        status=status or StatusOcorrencia.ABERTA,
        criado_por=criado_por,
        resolvida_em=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_horario_aula(
    session: AsyncSession,
    turma_id: uuid.UUID,
    professor_id: uuid.UUID,
    dia_semana: str = "seg",
    hora_inicio: str = "08:00",
    hora_fim: str = "08:50",
    disciplina_id: uuid.UUID | None = None,
    ativo: bool = True,
):
    """Janela de aula na grade.

    Aceita string ("08:00") em vez de `time` porque é mais legível nos testes; o
    SQLAlchemy converte na hora do bind.
    """
    from datetime import time as _time

    from app.modules.schedule.models import HorarioAula

    def _hhmm(v: str) -> _time:
        h, _, m = v.partition(":")
        return _time(int(h), int(m or 0))

    obj = HorarioAula(
        turma_id=turma_id,
        professor_id=professor_id,
        disciplina_id=disciplina_id,
        dia_semana=dia_semana,
        hora_inicio=_hhmm(hora_inicio),
        hora_fim=_hhmm(hora_fim),
        ativo=ativo,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_aviso(
    session: AsyncSession,
    titulo: str = "Aviso Geral",
    mensagem: str = "Conteúdo do aviso",
    criado_por: uuid.UUID | None = None,
    destinatario_aluno_id: uuid.UUID | None = None,
    destinatario_turma_id: uuid.UUID | None = None,
    status=None,
    prioridade=None,
    tipo=None,
    publicado_em: datetime | None = None,
):
    from app.modules.communication.models import Aviso
    from app.shared.enums import PrioridadeAviso, StatusAviso, TipoAviso

    if criado_por is None:
        user = await create_usuario(session, perfil=Perfil.ADMIN)
        criado_por = user.id
    obj = Aviso(
        titulo=titulo,
        mensagem=mensagem,
        tipo=tipo or TipoAviso.GERAL,
        prioridade=prioridade or PrioridadeAviso.MEDIA,
        destinatario_aluno_id=destinatario_aluno_id,
        destinatario_turma_id=destinatario_turma_id,
        permite_respostas=True,
        status=status or StatusAviso.PUBLICADO,
        criado_por=criado_por,
        publicado_em=publicado_em or datetime.now(UTC),
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_aviso_destinatario(
    session: AsyncSession,
    aviso_id: uuid.UUID,
    usuario_id: uuid.UUID,
    lido: bool = False,
):
    from app.modules.communication.models import AvisoDestinatario

    obj = AvisoDestinatario(
        aviso_id=aviso_id,
        usuario_id=usuario_id,
        lido_em=datetime.now(UTC) if lido else None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_aviso_mensagem(
    session: AsyncSession,
    aviso_id: uuid.UUID,
    autor_id: uuid.UUID,
    conteudo: str = "Resposta da secretaria",
):
    from app.modules.communication.models import AvisoMensagem

    obj = AvisoMensagem(
        aviso_id=aviso_id,
        autor_id=autor_id,
        destinatario_id=None,
        conteudo=conteudo,
        lida_em=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_notificacao(
    session: AsyncSession,
    destinatario_id: uuid.UUID,
    titulo: str = "Notificação",
    lida: bool = False,
):
    from app.modules.communication.models import Notificacao

    obj = Notificacao(
        destinatario_id=destinatario_id,
        tipo="sistema",
        titulo=titulo,
        mensagem="Mensagem da notificação",
        canal="inapp",
        lida=lida,
        lida_em=datetime.now(UTC) if lida else None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_produto(
    session: AsyncSession,
    nome: str = "Salgado",
    preco: float = 5.0,
    estoque_atual: int = 10,
    estoque_minimo: int = 2,
    ativo: bool = True,
):
    from decimal import Decimal

    from app.modules.cantina.models import Produto

    obj = Produto(
        nome=nome,
        descricao=None,
        preco=Decimal(str(preco)),
        categoria="SALGADO",
        estoque_atual=estoque_atual,
        estoque_minimo=estoque_minimo,
        codigo=f"P{uuid.uuid4().hex[:6]}",
        ativo=ativo,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_pedido(
    session: AsyncSession,
    aluno_id: uuid.UUID,
    responsavel_id: uuid.UUID,
    status=None,
    data_referencia: date | None = None,
    valor_total: float = 10.0,
):
    from decimal import Decimal

    from app.modules.cantina.models import Pedido
    from app.shared.enums import StatusPedido

    obj = Pedido(
        aluno_id=aluno_id,
        responsavel_id=responsavel_id,
        origem="RESPONSAVEL",
        data_referencia=data_referencia or date.today(),
        status=status or StatusPedido.PENDENTE,
        valor_total=Decimal(str(valor_total)),
        saldo_debitado=Decimal("0.00"),
        observacoes=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_item_pedido(
    session: AsyncSession,
    pedido_id: uuid.UUID,
    produto_id: uuid.UUID,
    quantidade: int = 1,
):
    from app.modules.cantina.models import ItemPedido, Produto

    produto = await session.get(Produto, produto_id)
    obj = ItemPedido(
        pedido_id=pedido_id,
        produto_id=produto_id,
        quantidade=quantidade,
        preco_unitario=produto.preco,
        preco_total=produto.preco * quantidade,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_programacao_cantina(
    session: AsyncSession,
    aluno_id: uuid.UUID,
    responsavel_id: uuid.UUID,
    dia_semana: str = "seg",
    tipo=None,
):
    from app.modules.cantina.programacao_models import ProgramacaoCantina
    from app.shared.enums import TipoProgramacao

    obj = ProgramacaoCantina(
        aluno_id=aluno_id,
        responsavel_id=responsavel_id,
        dia_semana=dia_semana,
        tipo=tipo or TipoProgramacao.GERAL,
        ativo=True,
        observacoes=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_programacao_item(
    session: AsyncSession,
    programacao_id: uuid.UUID,
    produto_id: uuid.UUID,
    quantidade: int = 1,
):
    from app.modules.cantina.programacao_models import ProgramacaoItem

    obj = ProgramacaoItem(
        programacao_id=programacao_id,
        produto_id=produto_id,
        quantidade=quantidade,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_solicitacao_documento(
    session: AsyncSession,
    responsavel_id: uuid.UUID,
    aluno_id: uuid.UUID,
    status=None,
    resposta: str | None = None,
):
    from app.modules.document_requests.models import SolicitacaoDocumento
    from app.shared.enums import StatusSolicitacaoDocumento

    obj = SolicitacaoDocumento(
        responsavel_id=responsavel_id,
        aluno_id=aluno_id,
        tipo="declaracao_matricula",
        status=status or StatusSolicitacaoDocumento.PENDENTE,
        observacoes=None,
        resposta=resposta,
        documento_url=None,
        atendido_por=None,
        atendido_em=None,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_evento(
    session: AsyncSession,
    titulo: str = "Reunião de Pais",
    data_inicio: datetime | None = None,
    perfil_criador: Perfil = Perfil.ADMIN,
    criado_por: uuid.UUID | None = None,
    ativo: bool = True,
):
    from app.modules.agenda.models import Evento

    if criado_por is None:
        user = await create_usuario(session, perfil=perfil_criador)
        criado_por = user.id
    if data_inicio is None:
        data_inicio = datetime.now(UTC) + timedelta(days=1)
    obj = Evento(
        titulo=titulo,
        descricao="Descrição do evento",
        data_inicio=data_inicio,
        data_fim=None,
        local="Auditório",
        criado_por=criado_por,
        perfil_criador=perfil_criador,
        ativo=ativo,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_evento_destinatario(
    session: AsyncSession,
    evento_id: uuid.UUID,
    tipo_destino: str,
    destino_id: uuid.UUID,
):
    from app.modules.agenda.models import EventoDestinatario

    obj = EventoDestinatario(
        evento_id=evento_id,
        tipo_destino=tipo_destino,
        destino_id=destino_id,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_pulseira(
    session: AsyncSession,
    aluno_id: uuid.UUID,
    status=None,
):
    from app.modules.bracelets.models import Bracelet
    from app.shared.enums import StatusPulseira

    obj = Bracelet(
        uid=f"UID{uuid.uuid4().hex[:10]}",
        codigo=f"PUL{uuid.uuid4().hex[:6]}",
        aluno_id=aluno_id,
        status=status or StatusPulseira.ATIVA,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_liberacao_boletim(
    session: AsyncSession,
    professor_id: uuid.UUID,
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    alocacao_id: uuid.UUID,
    ano_letivo_id: uuid.UUID,
    bimestre: int = 1,
):
    from app.modules.boletim.models import LiberacaoBoletim

    obj = LiberacaoBoletim(
        professor_id=professor_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        alocacao_id=alocacao_id,
        ano_letivo_id=ano_letivo_id,
        bimestre=bimestre,
        liberado_em=datetime.now(UTC),
        ativo=True,
    )
    session.add(obj)
    await session.flush()
    return obj


async def create_prazo_liberacao(
    session: AsyncSession,
    ano_letivo_id: uuid.UUID,
    bimestre: int = 1,
    data_limite: date | None = None,
):
    from datetime import time as _time

    from app.modules.boletim.models import PrazoLiberacao

    obj = PrazoLiberacao(
        ano_letivo_id=ano_letivo_id,
        bimestre=bimestre,
        data_limite=data_limite or date(2026, 6, 30),
        hora_limite=_time(23, 59, 59),
        notificado_em=None,
        ativo=True,
    )
    session.add(obj)
    await session.flush()
    return obj
