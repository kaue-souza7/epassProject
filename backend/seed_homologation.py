"""
Seed de homologação — ePass
Cria massa de dados realista simulando uma escola em operação.

Idempotente: verifica existência antes de cada criação.
Reutiliza entidades preexistentes (ex: seed_data.py já rodou).
Pode ser executado múltiplas vezes sem duplicar dados.

Uso:
  cd backend && python seed_homologation.py
"""

import asyncio
import uuid
import random
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import select, func

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
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.financial.models import Wallet, Movimentacao
from app.modules.agenda.models import Evento, EventoDestinatario
from app.modules.bracelets.models import Bracelet
from app.shared.enums import (
    Perfil, Turno, StatusMatricula, Parentesco,
    StatusCarteira, StatusPulseira, TipoAvaliacao,
    StatusFrequencia, TipoMovimentacao, TipoDestinoEvento,
)

SENHA = hash_password("123456")

# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

async def get_or_create(
    session: Any,
    model: Any,
    filter_kwargs: dict,
    factory: Callable,
) -> tuple[Any, bool]:
    result = await session.execute(select(model).filter_by(**filter_kwargs))
    instance = result.scalar_one_or_none()
    if instance is not None:
        return instance, False
    instance = factory()
    session.add(instance)
    await session.flush()
    return instance, True


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


# ═══════════════════════════════════════════════════════
# DADOS
# ═══════════════════════════════════════════════════════

PROFESSORES = [
    ("Carlos Alberto Mendes", "carlos.mendes@epass.edu", "Licenciatura em Matemática", "MAT001"),
    ("Fernanda Cristina Lima", "fernanda.lima@epass.edu", "Licenciatura em Letras", "MAT002"),
    ("Ricardo de Souza Oliveira", "ricardo.souza@epass.edu", "Licenciatura em Biologia", "MAT003"),
]

DISCIPLINAS_DATA = [
    ("MAT", "Matemática", "Matemática básica e intermediária"),
    ("FIS", "Física", "Física geral"),
    ("POR", "Português", "Língua portuguesa e literatura"),
    ("HIS", "História", "História geral e do Brasil"),
    ("GEO", "Geografia", "Geografia geral e do Brasil"),
    ("CIE", "Ciências", "Ciências naturais"),
    ("ING", "Inglês", "Língua inglesa"),
]

ALOCACOES_CONFIG = [
    (0, "MAT"), (0, "FIS"),
    (1, "POR"), (1, "HIS"),
    (2, "CIE"), (2, "GEO"),
]

TURMAS_DATA = [
    ("3A", "3º Ano A", 3, Turno.MANHA),
    ("3B", "3º Ano B", 3, Turno.MANHA),
    ("3C", "3º Ano C", 3, Turno.MANHA),
]

RESPONSAVEIS = [
    "Roberto Alves Ferreira", "Maria Conceição Oliveira", "Paulo Henrique Silva",
    "Cristina Aparecida Lima", "Fernando José Santos", "Lucia Helena Pereira",
    "Marcos Antônio Costa", "Rita de Cássia Souza", "Jorge Luiz Rodrigues",
    "Simone Cristina Almeida", "André Luiz Nascimento", "Patrícia Gomes Barbosa",
    "Ricardo Augusto Martins", "Débora Cristina Rocha", "Eduardo Henrique Dias",
    "Camila Fernandes Moreira", "Gustavo Henrique Araújo", "Fernanda Ribeiro Carvalho",
    "Luciano Santos Teixeira", "Adriana Oliveira Pinto", "Ronaldo José Campos",
    "Tatiane Rodrigues Ferreira", "Daniel Almeida Costa", "Vanessa Cristina Silva",
    "Alexandre Pereira Santos", "Juliana Maria Oliveira", "Fábio Henrique Lima",
    "Renata Cristina Souza", "Thiago Augusto Pereira", "Bruna Alves Rodrigues",
]

ALUNOS = [
    "Arthur Silva Oliveira", "Beatriz Santos Lima", "Caio Pereira Costa",
    "Daniela Oliveira Souza", "Eduardo Almeida Rodrigues", "Fernanda Castro Dias",
    "Gabriel Rocha Martins", "Helena Moreira Barbosa", "Igor Nascimento Teixeira",
    "Julia Campos Araújo",
    "Lucas Carvalho Pinto", "Manuela Gomes Ribeiro", "Nicolas Azevedo Farias",
    "Olivia Barros Monteiro", "Pedro Henrique Neves", "Quintino Lopes Cunha",
    "Rafaela Machado Campos", "Samuel Tavares Vargas", "Tais Correia Peixoto",
    "Ulysses Pires Cavalcante",
    "Valentina Xavier Moreira", "Vinicius Braga Assunção", "Willian Teixeira Cardoso",
    "Yasmin Figueiredo Lemos", "Zacarias Andrade Matos", "Alice Freitas Assis",
    "Benjamin Duarte Toledo", "Cecília Fonseca Bonfim", "Davi Alencar Padilha",
    "Elisa Marinho Chaves",
]

# índice do aluno -> índice da turma (0=3A, 1=3B, 2=3C)
ALUNOS_TURMA_MAP = [0] * 10 + [1] * 10 + [2] * 10

EVENTOS_CONFIG = [
    ("Reunião de Pais", "Reunião geral para alinhamento do ano letivo.", "reuniao"),
    ("Feira de Ciências", "Exposição de projetos científicos dos alunos.", "cultural"),
    ("Festa Junina", "Arraial com apresentações, brincadeiras e comidas típicas.", "cultural"),
    ("Simulado ENEM", "Simulado geral nos moldes do ENEM para todas as turmas.", "prova"),
    ("Conselho de Classe", "Reunião pedagógica para avaliação dos alunos.", "reuniao"),
    ("Prova Bimestral de Matemática", "Avaliação bimestral de Matemática.", "prova"),
    ("Prova Bimestral de Português", "Avaliação bimestral de Português.", "prova"),
    ("Prova Bimestral de Ciências", "Avaliação bimestral de Ciências.", "prova"),
    ("Entrega de Boletins", "Entrega dos resultados bimestrais aos responsáveis.", "boletim"),
    ("Campeonato Esportivo", "Competições de futsal, vôlei e queimada.", "esporte"),
    ("Passeio ao Museu", "Visita educativa ao museu de ciências.", "passeio"),
    ("Oficina de Redação", "Workshop de produção textual para o ENEM.", "oficina"),
    ("Semana de Provas", "Semana de avaliações bimestrais.", "prova"),
    ("Palestra sobre Profissões", "Palestra com profissionais de diversas áreas.", "cultural"),
    ("Dia da Família na Escola", "Integração entre famílias e comunidade escolar.", "cultural"),
]

TIPO_AVAL_NOMES = {
    0: ("Prova", TipoAvaliacao.PROVA, 3),
    1: ("Trabalho", TipoAvaliacao.TRABALHO, 2),
    2: ("Atividade", TipoAvaliacao.ATIVIDADE, 1),
}

# ═══════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════

async def seed():
    print(f"Conectando ao banco: {settings.DATABASE_URL}")
    async with SessionLocal() as session:
        # ── SENTINELA ──────────────────────────────────────────────
        sentinel = await session.execute(
            select(Usuario).where(Usuario.email == "admin@epass.edu")
        )
        if sentinel.scalar_one_or_none():
            print("⚠ Seed de homologação já executado. Pulando.")
            return
        print("▶ Iniciando seed de homologação...\n")

        # ── 1. ANO LETIVO ─────────────────────────────────────────
        ano_letivo, created = await get_or_create(
            session, AnoLetivo, {"ano": 2026},
            lambda: AnoLetivo(
                id=uuid.uuid4(), ano=2026,
                data_inicio=date(2026, 2, 1), data_fim=date(2026, 12, 20),
                ativo=True,
            ),
        )
        print(f"  {'✓' if created else '→'} Ano letivo 2026 (id={ano_letivo.id})")

        # ── 2. CONFIGURAÇÃO ACADÊMICA ─────────────────────────────
        config, created = await get_or_create(
            session, ConfiguracaoAcademica, {"ano_letivo_id": ano_letivo.id},
            lambda: ConfiguracaoAcademica(
                id=uuid.uuid4(), ano_letivo_id=ano_letivo.id,
                media_aprovacao=Decimal("6.0"), frequencia_minima=Decimal("75.0"),
                possui_recuperacao=True, media_minima_recuperacao=Decimal("4.0"),
                quantidade_periodos=4, ativo=True,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ),
        )
        if created:
            print(f"  ✓ Configuração acadêmica criada")

        # ── 3. SÉRIES ─────────────────────────────────────────────
        series_data = [
            (1, "1º Ano", "Primeiro ano"),
            (2, "2º Ano", "Segundo ano"),
            (3, "3º Ano", "Terceiro ano"),
        ]
        series = {}
        for num, nome, desc in series_data:
            s, _ = await get_or_create(
                session, Serie, {"numero": num},
                lambda n=nome, num=num, d=desc: Serie(
                    id=uuid.uuid4(), numero=num, nome=n, descricao=d, ativo=True,
                ),
            )
            series[num] = s
        print(f"  ✓ {len(series)} séries disponíveis")

        # ── 4. DISCIPLINAS ────────────────────────────────────────
        # Nota: nome tem UNIQUE, pode existir com codigo diferente
        disciplinas = {}
        for cod, nome, desc in DISCIPLINAS_DATA:
            d = (await session.execute(select(Disciplina).filter_by(codigo=cod))).scalar_one_or_none()
            if d is None:
                d = (await session.execute(select(Disciplina).filter_by(nome=nome))).scalar_one_or_none()
            if d is None:
                d = Disciplina(id=uuid.uuid4(), codigo=cod, nome=nome, descricao=desc, ativo=True)
                session.add(d)
                await session.flush()
            disciplinas[cod] = d
        print(f"  ✓ {len(disciplinas)} disciplinas disponíveis")

        # ── 5. TURMAS ─────────────────────────────────────────────
        turmas = {}
        for cod, nome, serie_num, turno in TURMAS_DATA:
            t, _ = await get_or_create(
                session, Turma, {"codigo": cod, "ano_letivo_id": ano_letivo.id},
                lambda c=cod, n=nome, sn=serie_num, tn=turno, al=ano_letivo: Turma(
                    id=uuid.uuid4(), codigo=c, nome=n,
                    serie_id=series[sn].id, ano_letivo_id=al.id,
                    turno=tn, vagas_total=30, ativo=True,
                ),
            )
            turmas[cod] = t
        print(f"  ✓ {len(turmas)} turmas disponíveis")

        # ── 6. ADMIN ──────────────────────────────────────────────
        admin, created = await get_or_create(
            session, Usuario, {"email": "admin@epass.edu"},
            lambda: Usuario(
                id=uuid.uuid4(), nome="Administrador ePass",
                email="admin@epass.edu", senha_hash=SENHA,
                perfil=Perfil.ADMIN, ativo=True,
            ),
        )
        print(f"  {'✓' if created else '→'} Admin criado")

        # ── 6.1 SECRETARIA ────────────────────────────────────────
        secretaria, created = await get_or_create(
            session, Usuario, {"email": "secretaria@epass.edu"},
            lambda: Usuario(
                id=uuid.uuid4(), nome="Secretaria ePass",
                email="secretaria@epass.edu", senha_hash=SENHA,
                perfil=Perfil.SECRETARIA, ativo=True,
            ),
        )
        print(f"  {'✓' if created else '→'} Secretaria criada")

        # ── 7. PROFESSORES ────────────────────────────────────────
        prof_users = {}
        for nome, email, formacao, matricula_func in PROFESSORES:
            user, _ = await get_or_create(
                session, Usuario, {"email": email},
                lambda n=nome, e=email: Usuario(
                    id=uuid.uuid4(), nome=n, email=e,
                    senha_hash=SENHA, perfil=Perfil.PROFESSOR, ativo=True,
                ),
            )
            prof, _ = await get_or_create(
                session, ProfessorProfile, {"usuario_id": user.id},
                lambda u=user, f=formacao, mf=matricula_func: ProfessorProfile(
                    usuario_id=u.id, formacao_principal=f,
                    matricula_funcional=mf,
                    data_contratacao=date(2025, 1, random.randint(5, 20)),
                    ativo=True,
                ),
            )
            prof_users[email] = user
        print(f"  ✓ {len(prof_users)} professores disponíveis")

        # ── 8. RESPONSÁVEIS ──────────────────────────────────────
        resp_users = {}
        for nome in RESPONSAVEIS:
            email = f"{nome.lower().replace(' ', '.')}@epass.edu"
            user, created = await get_or_create(
                session, Usuario, {"email": email},
                lambda n=nome, e=email: Usuario(
                    id=uuid.uuid4(), nome=n, email=e,
                    senha_hash=SENHA, perfil=Perfil.RESPONSAVEL, ativo=True,
                ),
            )
            resp_users[email] = user
        print(f"  ✓ {len(resp_users)} responsáveis disponíveis")

        # ── 9. ALUNOS ─────────────────────────────────────────────
        alunos = []
        for nome in ALUNOS:
            email_aluno = f"{nome.lower().replace(' ', '.').replace('ó', 'o').replace('ã', 'a').replace('ç', 'c').replace('é', 'e')}@aluno.epass.edu"
            alun, created = await get_or_create(
                session, Aluno, {"email": email_aluno},
                lambda n=nome, ea=email_aluno: Aluno(
                    id=uuid.uuid4(), nome=n,
                    data_nascimento=date(
                        random.choice([2012, 2013, 2014, 2015, 2016]),
                        random.randint(1, 12), random.randint(1, 28),
                    ),
                    cpf=None, rg=None,
                    endereco=f"Rua {random.choice(['das Flores', 'dos Lírios', 'das Acácias', 'dos Ipês', 'dos Pinheiros'])}, {random.randint(100, 999)}",
                    telefone=f"({random.randint(11, 99)}) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                    email=ea,
                    data_entrada=date(2026, 2, 1), ativo=True,
                ),
            )
            alunos.append(alun)
        print(f"  ✓ {len(alunos)} alunos disponíveis")

        # ── 10. VÍNCULOS RESPONSÁVEL-ALUNO ───────────────────────
        parentescos = [Parentesco.PAI, Parentesco.MAE, Parentesco.TUTOR,
                       Parentesco.TIO, Parentesco.AVO, Parentesco.IRMAO]
        vinculos_count = 0
        for i, aluno in enumerate(alunos):
            resp_email = list(resp_users.keys())[i % len(resp_users)]
            vinculo, created = await get_or_create(
                session, ResponsavelAluno,
                {"aluno_id": aluno.id, "responsavel_id": resp_users[resp_email].id},
                lambda a=aluno, r=resp_users[resp_email], p=parentescos[(i // len(resp_users)) % len(parentescos)]: ResponsavelAluno(
                    aluno_id=a.id, responsavel_id=r.id,
                    parentesco=p, responsavel_financeiro=(i % 2 == 0),
                ),
            )
            if created:
                vinculos_count += 1
        print(f"  {'✓' if vinculos_count > 0 else '→'} {vinculos_count} vínculos criados")

        # ── 11. MATRÍCULAS ────────────────────────────────────────
        matriculas = {}
        for i, aluno in enumerate(alunos):
            turma_idx = ALUNOS_TURMA_MAP[i]
            turma_cod = list(turmas.keys())[turma_idx]
            mat, created = await get_or_create(
                session, Matricula,
                {"aluno_id": aluno.id, "turma_id": turmas[turma_cod].id},
                lambda a=aluno, t=turmas[turma_cod]: Matricula(
                    id=uuid.uuid4(), aluno_id=a.id, turma_id=t.id,
                    matricula_origem_id=None, data_matricula=date(2026, 2, 1),
                    status=StatusMatricula.ATIVA, data_saida=None,
                    motivo_saida=None, observacoes=None,
                ),
            )
            matriculas[i] = mat
        print(f"  ✓ {len(matriculas)} matrículas disponíveis")

        # ── 12. ALOCAÇÕES ─────────────────────────────────────────
        # Unique: (turma_id, disciplina_id) — pode existir com prof diferente
        alocacoes = []
        for cod_turma, turma in turmas.items():
            for prof_index, disc_cod in ALOCACOES_CONFIG:
                prof_user = list(prof_users.values())[prof_index]
                aloc = (await session.execute(
                    select(Alocacao).filter_by(turma_id=turma.id, disciplina_id=disciplinas[disc_cod].id)
                )).scalar_one_or_none()
                if aloc is None:
                    aloc = Alocacao(
                        id=uuid.uuid4(), professor_id=prof_user.id, turma_id=turma.id,
                        disciplina_id=disciplinas[disc_cod].id,
                        data_inicio=date(2026, 2, 1), data_fim=None,
                    )
                    session.add(aloc)
                    await session.flush()
                elif aloc.professor_id != prof_user.id:
                    aloc.professor_id = prof_user.id
                alocacoes.append(aloc)
        await session.flush()
        print(f"  ✓ {len(alocacoes)} alocações disponíveis")

        # ── 13. AVALIAÇÕES ────────────────────────────────────────
        # Verificar se já existem avaliações para estas alocações
        existing_aval_count = (await session.execute(
            select(func.count(Avaliacao.id)).where(
                Avaliacao.alocacao_id.in_([a.id for a in alocacoes])
            )
        )).scalar()
        if existing_aval_count and existing_aval_count > 0:
            print(f"  → Avaliações já existem ({existing_aval_count})")
            # carregar as existentes
            result = await session.execute(
                select(Avaliacao).where(Avaliacao.alocacao_id.in_([a.id for a in alocacoes]))
            )
            avaliacoes = result.scalars().all()
        else:
            avaliacoes = []
            for aloc in alocacoes:
                for bimestre in range(1, 5):
                    for aval_idx in range(3):
                        nome_tipo, tipo, peso = TIPO_AVAL_NOMES[aval_idx]
                        mes_base = 2 + (bimestre - 1) * 3
                        data_aval = date(2026, mes_base, random.randint(5, 20))
                        aval = Avaliacao(
                            id=uuid.uuid4(),
                            alocacao_id=aloc.id,
                            titulo=f"{nome_tipo} — Bimestre {bimestre}",
                            tipo=tipo, peso=peso,
                            nota_maxima=Decimal("10.00"),
                            bimestre=bimestre,
                            data_aplicacao=data_aval,
                            observacoes=None,
                        )
                        session.add(aval)
                        avaliacoes.append(aval)
            await session.flush()
            print(f"  ✓ {len(avaliacoes)} avaliações criadas")

        # ── 14. NOTAS ─────────────────────────────────────────────
        def nota_por_perfil(aluno_index):
            if aluno_index % 5 == 0:
                return round(random.uniform(7.0, 10.0), 1)
            elif aluno_index % 5 <= 2:
                return round(random.uniform(5.0, 8.5), 1)
            else:
                return round(random.uniform(4.0, 6.5), 1)

        turma_matriculas = {cod: [] for cod in turmas}
        for i, mat in matriculas.items():
            turma_idx = ALUNOS_TURMA_MAP[i]
            cod = list(turmas.keys())[turma_idx]
            turma_matriculas[cod].append((i, mat))

        aloc_turma_map = {}
        for aloc in alocacoes:
            for cod, turma in turmas.items():
                if aloc.turma_id == turma.id:
                    aloc_turma_map[aloc.id] = cod
                    break

        notas_count = 0
        for aval in avaliacoes:
            turma_cod = aloc_turma_map[aval.alocacao_id]
            for mat_idx, mat in turma_matriculas[turma_cod]:
                _, created = await get_or_create(
                    session, Nota,
                    {"avaliacao_id": aval.id, "matricula_id": mat.id},
                    lambda a=aval, m=mat, mi=mat_idx: Nota(
                        id=uuid.uuid4(), avaliacao_id=a.id, matricula_id=m.id,
                        valor=Decimal(str(nota_por_perfil(mi))),
                        observacoes=None,
                    ),
                )
                if created:
                    notas_count += 1
        print(f"  {'✓' if notas_count > 0 else '→'} {notas_count} notas criadas ({len(avaliacoes)} avaliações × ~10 alunos)")

        # ── 15. CHAMADAS ─────────────────────────────────────────
        hoje = date.today()
        inicio_chamadas = hoje - timedelta(days=120)

        chamadas_count = 0
        frequencias_count = 0
        for aloc in alocacoes:
            num_aulas = random.randint(12, 18)
            datas_aula = set()
            while len(datas_aula) < num_aulas:
                d = random_date(inicio_chamadas, hoje)
                if d.weekday() < 5:
                    datas_aula.add(d)
            for d in sorted(datas_aula):
                hora = random.choice([7, 8, 9, 10, 13, 14, 15])
                chamada, created = await get_or_create(
                    session, Chamada,
                    {"alocacao_id": aloc.id, "data_hora_aula": datetime(d.year, d.month, d.day, hora, 0, tzinfo=timezone.utc)},
                    lambda a=aloc, dd=d, hh=hora: Chamada(
                        id=uuid.uuid4(), alocacao_id=a.id,
                        data_hora_aula=datetime(dd.year, dd.month, dd.day, hh, 0, tzinfo=timezone.utc),
                    ),
                )
                if created:
                    chamadas_count += 1

                turma_cod = aloc_turma_map[aloc.id]
                for mat_idx, mat in turma_matriculas[turma_cod]:
                    _, created = await get_or_create(
                        session, Frequencia,
                        {"chamada_id": chamada.id, "matricula_id": mat.id},
                        lambda c=chamada, m=mat: Frequencia(
                            id=uuid.uuid4(), chamada_id=c.id, matricula_id=m.id,
                            status=random.choices(
                                [StatusFrequencia.PRESENTE, StatusFrequencia.FALTA, StatusFrequencia.FALTA_JUSTIFICADA],
                                weights=[0.80, 0.15, 0.05],
                            )[0],
                            observacoes=None,
                        ),
                    )
                    if created:
                        frequencias_count += 1
        print(f"  {'✓' if chamadas_count > 0 else '→'} {chamadas_count} chamadas criadas")
        print(f"  {'✓' if frequencias_count > 0 else '→'} {frequencias_count} frequências criadas")

        # ── 16. WALLETS ──────────────────────────────────────────
        wallets_count = 0
        for aluno in alunos:
            _, created = await get_or_create(
                session, Wallet, {"aluno_id": aluno.id},
                lambda a=aluno: Wallet(
                    id=uuid.uuid4(), aluno_id=a.id,
                    saldo=Decimal(str(round(random.uniform(20.0, 300.0), 2))),
                    status=StatusCarteira.ATIVA,
                ),
            )
            if created:
                wallets_count += 1
        print(f"  {'✓' if wallets_count > 0 else '→'} {wallets_count} wallets criadas")

        # ── 17. MOVIMENTAÇÕES ────────────────────────────────────
        descricoes_recarga = [
            "Recarga via aplicativo", "Recarga em dinheiro",
            "Recarga via PIX", "Recarga no totem", "Recarga online",
        ]
        descricoes_consumo = [
            "Lanche — cantina", "Suco natural", "Salgado",
            "Sanduíche", "Biscoito e suco", "Almoço", "Fruta",
        ]

        mov_count = 0
        wallets = (await session.execute(select(Wallet).where(Wallet.aluno_id.in_([a.id for a in alunos])))).scalars().all()

        for wallet in wallets:
            existing_mov = await session.execute(
                select(func.count(Movimentacao.id)).where(Movimentacao.wallet_id == wallet.id)
            )
            if existing_mov.scalar() > 0:
                continue

            num_mov = random.randint(20, 50)
            saldo_corrente = wallet.saldo
            for _ in range(num_mov):
                if random.random() < 0.4 or saldo_corrente < Decimal("2.00"):
                    tipo = TipoMovimentacao.RECARGA
                    valor = Decimal(str(round(random.uniform(10.0, 100.0), 2)))
                    desc = random.choice(descricoes_recarga)
                else:
                    tipo = TipoMovimentacao.CONSUMO
                    max_valor = min(saldo_corrente, Decimal("25.00"))
                    if max_valor < Decimal("1.00"):
                        continue
                    valor = Decimal(str(round(random.uniform(1.0, float(max_valor)), 2)))
                    desc = random.choice(descricoes_consumo)

                saldo_anterior = saldo_corrente
                if tipo == TipoMovimentacao.RECARGA:
                    saldo_posterior = saldo_anterior + valor
                else:
                    saldo_posterior = saldo_anterior - valor
                saldo_corrente = saldo_posterior

                session.add(Movimentacao(
                    id=uuid.uuid4(), wallet_id=wallet.id, tipo=tipo,
                    valor=valor, saldo_anterior=saldo_anterior,
                    saldo_posterior=saldo_posterior, descricao=desc,
                    criado_por=admin.id,
                ))
                mov_count += 1

            wallet.saldo = saldo_corrente
        print(f"  {'✓' if mov_count > 0 else '→'} {mov_count} movimentações criadas")

        # ── 18. EVENTOS ──────────────────────────────────────────
        for titulo, descricao, _ in EVENTOS_CONFIG:
            mes = random.randint(2, 12)
            data_inicio = datetime(2026, mes, min(random.randint(1, 28), 28), 8, 0, tzinfo=timezone.utc)
            data_fim = data_inicio + timedelta(hours=random.choice([1, 2, 3]))

            evento, created = await get_or_create(
                session, Evento, {"titulo": titulo, "data_inicio": data_inicio},
                lambda t=titulo, d=descricao, di=data_inicio, df=data_fim, a=admin: Evento(
                    id=uuid.uuid4(), titulo=t, descricao=d,
                    data_inicio=di,
                    data_fim=df if random.random() < 0.6 else None,
                    local=random.choice(["Auditório principal", "Quadra poliesportiva", "Sala de reuniões", "Pátio central", None]),
                    criado_por=a.id, perfil_criador=Perfil.ADMIN, ativo=True,
                ),
            )
            if created:
                tipo_destino = random.choice([
                    TipoDestinoEvento.TURMA, TipoDestinoEvento.RESPONSAVEL, TipoDestinoEvento.PROFESSOR,
                ])
                if tipo_destino == TipoDestinoEvento.TURMA:
                    targets = list(turmas.values())
                elif tipo_destino == TipoDestinoEvento.RESPONSAVEL:
                    targets = list(resp_users.values())
                else:
                    targets = list(prof_users.values())
                for target in targets:
                    session.add(EventoDestinatario(
                        id=uuid.uuid4(), evento_id=evento.id,
                        tipo_destino=tipo_destino, destino_id=target.id,
                    ))
        print(f"  ✓ {len(EVENTOS_CONFIG)} eventos criados")

        # ── 19. PULSEIRAS ─────────────────────────────────────────
        pulseiras_count = 0
        for i, aluno in enumerate(alunos):
            _, created = await get_or_create(
                session, Bracelet, {"uid": f"RFID{i+1:04d}"},
                lambda a=aluno, ii=i: Bracelet(
                    id=uuid.uuid4(), uid=f"RFID{ii+1:04d}",
                    codigo=f"PLS-{ii+1:04d}", aluno_id=a.id,
                    status=StatusPulseira.ATIVA,
                ),
            )
            if created:
                pulseiras_count += 1
        print(f"  {'✓' if pulseiras_count > 0 else '→'} {pulseiras_count} pulseiras criadas")

        # ── COMMIT ───────────────────────────────────────────────
        await session.commit()

        # ═══════════════════════════════════════════════════════════
        # VALIDAÇÃO
        # ═══════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  ✅  SEED DE HOMOLOGAÇÃO CONCLUÍDO")
        print("=" * 60)
        print()

        async def count(model):
            return (await session.execute(select(func.count(model.id)))).scalar()

        c_alunos = await count(Aluno)
        c_admin = (await session.execute(select(func.count(Usuario.id)).where(Usuario.perfil == Perfil.ADMIN))).scalar()
        c_secr = (await session.execute(select(func.count(Usuario.id)).where(Usuario.perfil == Perfil.SECRETARIA))).scalar()
        c_prof = (await session.execute(select(func.count(Usuario.id)).where(Usuario.perfil == Perfil.PROFESSOR))).scalar()
        c_resp = (await session.execute(select(func.count(Usuario.id)).where(Usuario.perfil == Perfil.RESPONSAVEL))).scalar()
        c_mat = await count(Matricula)
        c_disc = await count(Disciplina)
        c_aval = await count(Avaliacao)
        c_notas = await count(Nota)
        c_cham = await count(Chamada)
        c_freq = await count(Frequencia)
        c_eventos = await count(Evento)
        c_wallet = await count(Wallet)
        c_mov = await count(Movimentacao)

        print("── RESUMO ──")
        print(f"  Admin:           {c_admin}")
        print(f"  Secretaria:      {c_secr}")
        print(f"  Professores:     {c_prof}")
        print(f"  Responsáveis:    {c_resp}")
        print(f"  Alunos:          {c_alunos}")
        print(f"  Matrículas:      {c_mat}")
        print(f"  Disciplinas:     {c_disc}")
        print(f"  Avaliações:      {c_aval}")
        print(f"  Notas:           {c_notas}")
        print(f"  Chamadas:        {c_cham}")
        print(f"  Frequências:     {c_freq}")
        print(f"  Eventos:         {c_eventos}")
        print(f"  Wallets:         {c_wallet}")
        print(f"  Movimentações:   {c_mov}")

        print("\n── VALIDAÇÕES ──")
        erros = []
        checks = [
            (c_admin >= 1, f"Admin ≥ 1: {c_admin}"),
            (c_secr >= 1, f"Secretaria ≥ 1: {c_secr}"),
            (c_prof >= 3, f"Professores ≥ 3: {c_prof}"),
            (c_resp >= 30, f"Responsáveis ≥ 30: {c_resp}"),
            (c_alunos >= 30, f"Alunos ≥ 30: {c_alunos}"),
            (c_mat >= 30, f"Matrículas ≥ 30: {c_mat}"),
            (c_disc >= 7, f"Disciplinas ≥ 7: {c_disc}"),
            (c_aval >= 72, f"Avaliações ≥ 72: {c_aval}"),
            (c_notas >= 700, f"Notas ≥ 700: {c_notas}"),
            (c_cham >= 100, f"Chamadas ≥ 100: {c_cham}"),
            (c_freq >= 1000, f"Frequências ≥ 1000: {c_freq}"),
            (c_eventos >= 10, f"Eventos ≥ 10: {c_eventos}"),
            (c_wallet >= 30, f"Wallets ≥ 30: {c_wallet}"),
            (c_mov >= 100, f"Movimentações ≥ 100: {c_mov}"),
        ]
        for ok, msg in checks:
            print(f"  {'✓' if ok else '✗'} {msg}")
            if not ok:
                erros.append(msg)

        if erros:
            print(f"\n❌ {len(erros)} falha(s):")
            for e in erros:
                print(f"   • {e}")
        else:
            print("\n✅ Todas as validações passaram!")

        print()
        print("── ACESSOS (senha: 123456) ──")
        print(f"  admin@epass.edu{'':34s} (ADMIN)")
        print(f"  secretaria@epass.edu{'':28s} (SECRETARIA)")
        for _, email, *_ in PROFESSORES:
            print(f"  {email:45s} (PROFESSOR)")
        print(f"  {RESPONSAVEIS[0].lower().replace(' ', '.')}@epass.edu{'':18s} (RESPONSAVEL — exemplo)")
        print()


if __name__ == "__main__":
    asyncio.run(seed())
