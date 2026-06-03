import uuid
from datetime import UTC, datetime, timedelta, date

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
    ano: int = 2026,
    ativo: bool = True,
) -> AnoLetivo:
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
    numero: int = 1,
    nome: str = "1º Ano",
) -> Serie:
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
    codigo: str = "MAT",
    nome: str = "Matemática",
) -> Disciplina:
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
    from datetime import timezone
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
