import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.modules.academic_years.models import AnoLetivo
from app.modules.series.models import Serie
from app.modules.subjects.models import Disciplina
from app.modules.classes.models import Turma
from app.modules.students.models import Aluno, ResponsavelAluno
from app.modules.enrollments.models import Matricula
from app.modules.teachers.models import ProfessorProfile
from app.modules.allocations.models import Alocacao
from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.users.models import Usuario
from app.modules.auth.models import Sessao  # needed for relationship resolution
from app.modules.financial.models import Wallet
from app.modules.bracelets.models import Bracelet
from app.shared.enums import Perfil, Turno, StatusMatricula, Parentesco, StatusCarteira, StatusPulseira


async def seed():
    print(f"Conectando ao banco: {settings.DATABASE_URL}")
    async with SessionLocal() as session:
        # ── 1. USUÁRIOS ──────────────────────────────────────────
        existing = await session.execute(select(Usuario).where(Usuario.email == "admin@teste.com"))
        if existing.scalar_one_or_none():
            print("⚠  Seed já executado anteriormente. Pulando.")
            return

        senha_hash = hash_password("123456")

        users_data = [
            Usuario(id=uuid.uuid4(), nome="Administrador Teste", email="admin@teste.com", senha_hash=senha_hash, perfil=Perfil.ADMIN, ativo=True),
            Usuario(id=uuid.uuid4(), nome="Secretaria Teste", email="secretaria@teste.com", senha_hash=senha_hash, perfil=Perfil.SECRETARIA, ativo=True),
            Usuario(id=uuid.uuid4(), nome="Professor Teste", email="professor@teste.com", senha_hash=senha_hash, perfil=Perfil.PROFESSOR, ativo=True),
            Usuario(id=uuid.uuid4(), nome="Responsável Teste", email="responsavel@teste.com", senha_hash=senha_hash, perfil=Perfil.RESPONSAVEL, ativo=True),
        ]

        for u in users_data:
            session.add(u)
        await session.flush()
        print(f"✓ {len(users_data)} usuários criados")

        admin = users_data[0]
        professor = users_data[2]
        responsavel = users_data[3]

        # ── 2. PROFESSOR PROFILE ─────────────────────────────────
        prof_profile = ProfessorProfile(
            usuario_id=professor.id,
            formacao_principal="Licenciatura em Matemática",
            matricula_funcional="PROF001",
            data_contratacao=date(2024, 1, 15),
            ativo=True,
        )
        session.add(prof_profile)
        await session.flush()
        print(f"✓ Perfil de professor criado (usuario_id={professor.id})")

        # ── 3. ANO LETIVO ────────────────────────────────────────
        ano_letivo = AnoLetivo(
            id=uuid.uuid4(), ano=2026,
            data_inicio=date(2026, 2, 1), data_fim=date(2026, 12, 20),
            ativo=True,
        )
        session.add(ano_letivo)
        await session.flush()
        print(f"✓ Ano letivo criado: 2026 (id={ano_letivo.id})")

        # ── 4. SÉRIE ──────────────────────────────────────────────
        serie = Serie(id=uuid.uuid4(), numero=1, nome="1º Ano", descricao="Primeiro ano do ensino fundamental", ativo=True)
        session.add(serie)
        await session.flush()
        print(f"✓ Série criada: 1º Ano (id={serie.id})")

        # ── 5. DISCIPLINA ─────────────────────────────────────────
        disciplina = Disciplina(id=uuid.uuid4(), codigo="MAT", nome="Matemática", descricao="Disciplina de Matemática", ativo=True)
        session.add(disciplina)
        await session.flush()
        print(f"✓ Disciplina criada: Matemática (id={disciplina.id})")

        # ── 6. TURMA ──────────────────────────────────────────────
        turma = Turma(
            id=uuid.uuid4(), codigo="1A", nome="1º Ano A",
            serie_id=serie.id, ano_letivo_id=ano_letivo.id,
            turno=Turno.MANHA, vagas_total=30, ativo=True,
        )
        session.add(turma)
        await session.flush()
        print(f"✓ Turma criada: 1A (id={turma.id})")

        # ── 7. ALUNO ──────────────────────────────────────────────
        aluno = Aluno(
            id=uuid.uuid4(), nome="Aluno Teste",
            data_nascimento=date(2015, 5, 10),
            cpf=None, rg=None, endereco=None, telefone=None, email=None,
            data_entrada=date(2026, 2, 1), ativo=True,
        )
        session.add(aluno)
        await session.flush()
        print(f"✓ Aluno criado: Aluno Teste (id={aluno.id})")

        # ── 8. MATRÍCULA ──────────────────────────────────────────
        matricula = Matricula(
            id=uuid.uuid4(), aluno_id=aluno.id, turma_id=turma.id,
            matricula_origem_id=None, data_matricula=date(2026, 2, 1),
            status=StatusMatricula.ATIVA, data_saida=None, motivo_saida=None, observacoes=None,
        )
        session.add(matricula)
        await session.flush()
        print(f"✓ Matrícula criada (id={matricula.id})")

        # ── 9. VÍNCULO RESPONSÁVEL-ALUNO ─────────────────────────
        vinculo = ResponsavelAluno(
            aluno_id=aluno.id, responsavel_id=responsavel.id,
            parentesco=Parentesco.PAI, responsavel_financeiro=True,
        )
        session.add(vinculo)
        await session.flush()
        print(f"✓ Vínculo responsável-aluno criado")

        # ── 9.1 CARTEIRA DIGITAL ────────────────────────────────
        wallet = Wallet(
            aluno_id=aluno.id,
            saldo=Decimal("50.00"),
            status=StatusCarteira.ATIVA,
        )
        session.add(wallet)
        await session.flush()
        print(f"✓ Carteira criada com saldo inicial de R$ 50,00 (id={wallet.id})")

        # ── 9.2 PULSEIRA ─────────────────────────────────────────
        bracelet = Bracelet(
            uid="RFID001",
            codigo="PLS-001",
            aluno_id=aluno.id,
            status=StatusPulseira.ATIVA,
        )
        session.add(bracelet)
        await session.flush()
        print(f"✓ Pulseira criada (uid=RFID001, id={bracelet.id})")

        # ── 10. ALOCAÇÃO ──────────────────────────────────────────
        alocacao = Alocacao(
            id=uuid.uuid4(), professor_id=professor.id, turma_id=turma.id,
            disciplina_id=disciplina.id,
            data_inicio=date(2026, 2, 1), data_fim=None,
        )
        session.add(alocacao)
        await session.flush()
        print(f"✓ Alocação criada (id={alocacao.id})")

        # ── 11. CONFIGURAÇÃO ACADÊMICA ───────────────────────────
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        config = ConfiguracaoAcademica(
            id=uuid.uuid4(), ano_letivo_id=ano_letivo.id,
            media_aprovacao=6.0, frequencia_minima=75.0,
            possui_recuperacao=True, media_minima_recuperacao=4.0,
            quantidade_periodos=4, ativo=True,
            created_at=now_naive, updated_at=now_naive,
        )
        session.add(config)
        await session.flush()
        print(f"✓ Configuração acadêmica criada")

        await session.commit()
        print()
        print("=" * 50)
        print("  ✅  SEED CONCLUÍDO COM SUCESSO")
        print("=" * 50)
        print()
        print("Usuários criados:")
        print(f"  admin@teste.com      / 123456  ({Perfil.ADMIN.value})")
        print(f"  secretaria@teste.com / 123456  ({Perfil.SECRETARIA.value})")
        print(f"  professor@teste.com  / 123456  ({Perfil.PROFESSOR.value})")
        print(f"  responsavel@teste.com/ 123456  ({Perfil.RESPONSAVEL.value})")
        print()
        print(f"IDs gerados:")
        print(f"  Ano Letivo:    {ano_letivo.id}")
        print(f"  Série:         {serie.id}")
        print(f"  Disciplina:    {disciplina.id}")
        print(f"  Turma:         {turma.id}")
        print(f"  Aluno:         {aluno.id}")
        print(f"  Matrícula:     {matricula.id}")
        print(f"  Alocação:      {alocacao.id}")
        print(f"  Carteira:      {wallet.id}")
        print(f"  Pulseira:      {bracelet.id}")
        print()


if __name__ == "__main__":
    asyncio.run(seed())
