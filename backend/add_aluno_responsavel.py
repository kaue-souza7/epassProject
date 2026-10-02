"""
Adiciona um novo aluno vinculado ao responsável Roberto Alves Ferreira.
Uso: cd backend && python add_aluno_responsavel.py
"""

import asyncio
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.modules.users.models import Usuario
from app.modules.auth.models import Sessao
from app.modules.students.models import Aluno, ResponsavelAluno
from app.modules.enrollments.models import Matricula
from app.modules.classes.models import Turma
from app.modules.academic_years.models import AnoLetivo
from app.shared.enums import Perfil, Parentesco, StatusMatricula, Turno
from app.modules.subjects.models import Disciplina
from app.modules.series.models import Serie
from app.modules.teachers.models import ProfessorProfile
from app.modules.allocations.models import Alocacao
from app.modules.academic_config.models import ConfiguracaoAcademica


async def main():
    print(f"Conectando ao banco: {settings.DATABASE_URL}")
    async with SessionLocal() as session:
        responsavel_email = "roberto.alves.ferreira@epass.edu"

        result = await session.execute(
            select(Usuario).where(
                Usuario.email == responsavel_email,
                Usuario.deleted_at.is_(None),
            )
        )
        responsavel = result.scalar_one_or_none()
        if not responsavel:
            print(f"Erro: responsável {responsavel_email} não encontrado.")
            return

        print(f"Responsável encontrado: {responsavel.nome} ({responsavel.id})")

        result = await session.execute(
            select(AnoLetivo).where(AnoLetivo.ativo.is_(True))
        )
        ano_letivo = result.scalar_one_or_none()
        if not ano_letivo:
            print("Erro: nenhum ano letivo ativo encontrado.")
            return

        result = await session.execute(
            select(Turma).where(Turma.codigo == "3A", Turma.ano_letivo_id == ano_letivo.id)
        )
        turma = result.scalar_one_or_none()
        if not turma:
            print("Erro: turma 3A não encontrada.")
            return

        email_aluno = "miguel.santos.ferreira@aluno.epass.edu"

        result = await session.execute(
            select(Aluno).where(Aluno.email == email_aluno)
        )
        aluno_existente = result.scalar_one_or_none()
        if aluno_existente:
            print(f"Aluno já existe: {aluno_existente.nome} ({aluno_existente.id})")
            aluno = aluno_existente
        else:
            aluno = Aluno(
                id=uuid.uuid4(),
                nome="Miguel Santos Ferreira",
                data_nascimento=date(2013, 7, 15),
                cpf=None,
                rg=None,
                endereco="Rua das Flores, 123",
                telefone="(11) 99999-8888",
                email=email_aluno,
                data_entrada=date(2026, 2, 1),
                ativo=True,
            )
            session.add(aluno)
            await session.flush()
            print(f"Aluno criado: {aluno.nome} ({aluno.id})")

        result = await session.execute(
            select(Matricula).where(
                Matricula.aluno_id == aluno.id,
                Matricula.status == StatusMatricula.ATIVA,
            )
        )
        matricula_existente = result.scalar_one_or_none()
        if not matricula_existente:
            matricula = Matricula(
                id=uuid.uuid4(),
                aluno_id=aluno.id,
                turma_id=turma.id,
                matricula_origem_id=None,
                data_matricula=date(2026, 2, 1),
                status=StatusMatricula.ATIVA,
                data_saida=None,
                motivo_saida=None,
                observacoes=None,
            )
            session.add(matricula)
            await session.flush()
            print(f"Matrícula criada na turma {turma.codigo}")

        result = await session.execute(
            select(ResponsavelAluno).where(
                ResponsavelAluno.aluno_id == aluno.id,
                ResponsavelAluno.responsavel_id == responsavel.id,
            )
        )
        vinculo_existente = result.scalar_one_or_none()
        if not vinculo_existente:
            vinculo = ResponsavelAluno(
                aluno_id=aluno.id,
                responsavel_id=responsavel.id,
                parentesco=Parentesco.PAI,
                responsavel_financeiro=True,
            )
            session.add(vinculo)
            print(f"Vínculo criado: {responsavel.nome} → {aluno.nome}")

        await session.commit()
        print("\n✓ Concluído! Miguel Santos Ferreira agora é filho de Roberto Alves Ferreira.")


if __name__ == "__main__":
    asyncio.run(main())
