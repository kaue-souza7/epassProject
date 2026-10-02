"""Cria uma família de demonstração COMPLETA para o SGE.

Gera a cadeia toda de dados acadêmicos, de comunicação e financeiros de dois
filhos, para que qualquer tela (boletim, agenda, avisos, ocorrências, cantina,
carteira) e a Atena — que só responde o que o usuário tem autorização — tenham
o que exibir.

Cadeia criada, na ordem em que as chaves estrangeiras permitem::

    ano letivo ─ configuração ─┬─ série ─ turma ─┬─ alocação ─┬─ avaliação ─ nota
                       │                  │            └─ chamada ─ frequência
    secretaria/coordenação ─┐             ├─ matrícula ─┬─ wallet ─ movimentação
    professor × alocação ───┤             │             ├─ pulseira (bracelet)
                            │             │             ├─ ocorrência
    responsável ── responsável_aluno ── aluno ───────────┘
                            ├── aviso_destinatário ← aviso ← aviso_mensagem
                            ├── evento_destinatário ← evento
                            └── notificação
                        liberação de boletim ← alocação + professor + prazo

Uso::

    python seed_responsavel_demo.py            # não faz nada se já existir
    python seed_responsavel_demo.py --reset    # recria do zero
    python seed_responsavel_demo.py --limpar   # apaga só esta família

Todos os dados são fictícios. Senha de todos os usuários criados: ``SENHA``.

Cada linha criada recebe um UUID determinístico derivado de ``NAMESPACE`` e da
identidade do objeto. É isso que torna a limpeza segura: o ``--limpar`` apaga
exatamente os IDs que este seed possui, e nada mais — séries, turmas, disciplinas
e professores de terceiros nunca são tocados.
"""

import asyncio
import random
import sys
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database import SessionLocal
from app.modules.academic_config.models import ConfiguracaoAcademica
from app.modules.academic_years.models import AnoLetivo
from app.modules.agenda.models import Evento, EventoDestinatario
from app.modules.ai.history_models import Conversa, Mensagem
from app.modules.allocations.models import Alocacao
from app.modules.assessment.models import Avaliacao, Nota
from app.modules.attendance.models import Chamada, Frequencia
from app.modules.auth.models import Sessao
from app.modules.boletim.models import LiberacaoBoletim, PrazoLiberacao
from app.modules.bracelets.models import Bracelet
from app.modules.classes.models import Turma
from app.modules.communication.models import (
    Aviso,
    AvisoDestinatario,
    AvisoMensagem,
    Notificacao,
    Ocorrencia,
)
from app.modules.enrollments.models import Matricula
from app.modules.financial.models import Movimentacao, Wallet
from app.modules.series.models import Serie
from app.modules.students.models import Aluno, ResponsavelAluno
from app.modules.subjects.models import Disciplina
from app.modules.teachers.models import ProfessorProfile
from app.modules.users.models import Usuario
from app.shared.enums import (
    Parentesco,
    Perfil,
    PrioridadeAviso,
    SeveridadeOcorrencia,
    StatusAviso,
    StatusCarteira,
    StatusFrequencia,
    StatusMatricula,
    StatusOcorrencia,
    StatusPulseira,
    TipoAvaliacao,
    TipoDestinoEvento,
    TipoMovimentacao,
    TipoNotificacao,
    TipoOcorrencia,
    Turno,
)

# ---------------------------------------------------------------------------
# Identidade da família
# ---------------------------------------------------------------------------

# Fixo no tempo: trocar este valor invalida a limpeza dos seeds anteriores.
NAMESPACE = uuid.UUID("8f1c4a20-6b3d-5e7a-9c11-2d4f6a8b0c33")

EMAIL_RESPONSAVEL = "kauekaue960@gmail.com"
NOME_RESPONSAVEL = "Kauê Kauê"
SENHA = "123456"

EMAIL_SECRETARIA = "secretaria@sge.local"
ANO = 2026

# Fixa a semente: rodar duas vezes gera exatamente o mesmo banco.
random.seed(20260925)

HOJE = date(2026, 9, 25)
# O 1º bimestre vai até ~abril, o 2º até ~julho, o 3º vai até outubro.
DATAS_AVALIACAO = {1: date(2026, 4, 8), 2: date(2026, 7, 10), 3: date(2026, 9, 15)}
DATAS_PRAZO = {1: date(2026, 4, 10), 2: date(2026, 7, 12), 3: date(2026, 10, 8)}

DISCIPLINAS: list[tuple[str, str]] = [
    ("MAT", "Matemática"),
    ("PORT", "Língua Portuguesa"),
    ("CIE", "Ciências"),
    ("HIS", "História"),
    ("GEO", "Geografia"),
    ("ART", "Arte"),
    ("EF", "Educação Física"),
]

# Um professor por disciplina — é assim que a escola funciona de verdade.
PROFESSORES: dict[str, tuple[str, str]] = {
    "MAT": ("Carlos Menezes", "Licenciatura em Matemática"),
    "PORT": ("Rita Camargo", "Letras"),
    "CIE": ("Denise Rocha", "Biologia"),
    "HIS": ("Paulo Antunes", "Ciências Sociais"),
    "GEO": ("Sueli Prado", "Geografia"),
    "ART": ("Marina Furtado", "Artes Plásticas"),
    "EF": ("Jorge Bastos", "Educação Física"),
}

# (código, série, nome, turno)
TURMAS: list[tuple[str, int, str, Turno]] = [
    ("7A", 7, "7º Ano A", Turno.MANHA),
    ("5A", 5, "5º Ano A", Turno.MANHA),
]

FILHOS: list[dict] = [
    {
        "nome": "Miguel Kauê",
        "cpf": "11144477735",
        "nascimento": date(2012, 3, 14),
        "turma": "7A",
        "disciplinas": ["MAT", "PORT", "CIE", "HIS", "GEO", "ART", "EF"],
        # Faixa de nota por disciplina. O Miguel é propositalmente mais fraco
        # em Matemática: é o que dá sentido ao alerta do boletim.
        "faixa_notas": {
            "MAT": (5.5, 7.0),
            "PORT": (7.0, 9.0),
            "CIE": (7.5, 9.5),
            "HIS": (7.0, 9.0),
            "GEO": (7.0, 9.0),
            "ART": (8.5, 10.0),
            "EF": (8.5, 10.0),
        },
        "lancamentos": [
            (TipoMovimentacao.RECARGA, 200.00, "Recarga Family Card", 90),
            (TipoMovimentacao.CONSUMO, 12.50, "Lanche — cardápio do dia", 88),
            (TipoMovimentacao.CONSUMO, 11.30, "Lanche — cardápio do dia", 87),
            (TipoMovimentacao.RECARGA, 100.00, "Recarga Family Card", 45),
            (TipoMovimentacao.CONSUMO, 52.20, "Lanches do mês", 44),
            (TipoMovimentacao.CONSUMO, 5.30, "Suco natural", 20),
        ],
        "ocorrencias": [
            (
                "Chegada atrasada",
                "Chegou 20 minutos atrasado na aula de Matemática.",
                TipoOcorrencia.COMPORTAMENTO,
                SeveridadeOcorrencia.BAIXA,
                StatusOcorrencia.RESOLVIDA,
                12,
            ),
            (
                "Esquecimento do material",
                "Não trouxe o caderno de Ciências na aula de quinta-feira.",
                TipoOcorrencia.ACADEMICO,
                SeveridadeOcorrencia.MEDIA,
                StatusOcorrencia.ABERTA,
                4,
            ),
        ],
    },
    {
        "nome": "Helena Kauê",
        "cpf": "22255588846",
        "nascimento": date(2015, 8, 2),
        "turma": "5A",
        "disciplinas": ["MAT", "PORT", "CIE", "HIS", "GEO", "ART"],
        "faixa_notas": {
            "MAT": (7.5, 9.5),
            "PORT": (8.0, 10.0),
            "CIE": (8.0, 10.0),
            "HIS": (7.5, 9.5),
            "GEO": (7.5, 9.5),
            "ART": (9.0, 10.0),
        },
        "lancamentos": [
            (TipoMovimentacao.RECARGA, 200.00, "Recarga Family Card", 80),
            (TipoMovimentacao.CONSUMO, 18.40, "Lanche — cardápio do dia", 79),
            (TipoMovimentacao.CONSUMO, 9.80, "Suco natural", 78),
            (TipoMovimentacao.RECARGA, 50.00, "Recarga Family Card", 30),
            (TipoMovimentacao.CONSUMO, 22.90, "Lanches do mês", 29),
            (TipoMovimentacao.CONSUMO, 6.00, "Salgado", 10),
        ],
        "ocorrencias": [
            (
                "Participação exemplar",
                "Ajudou os colegas a entenderem a atividade de Geografia.",
                TipoOcorrencia.OUTRO,
                SeveridadeOcorrencia.BAIXA,
                StatusOcorrencia.RESOLVIDA,
                20,
            ),
        ],
    },
]

# (título, mensagem, tipo, prioridade, permite_respostas, dias_atras, com_notificação)
AVISOS: list[tuple[str, str, str, PrioridadeAviso, bool, int, bool]] = [
    (
        "Reunião de pais — 2º bimestre",
        "Boa tarde! Convocamos os responsáveis para a reunião de pais do 2º bimestre. "
        "Traga o boletim impresso e as dúvidas anotadas. A presença é muito importante.",
        "administrativo",
        PrioridadeAviso.MEDIA,
        True,
        3,
        False,
    ),
    (
        "Início das avaliações do 3º bimestre",
        "Informamos que as avaliações do 3º bimestre começam na próxima segunda-feira. "
        "O cronograma completo está disponível na secretaria.",
        "geral",
        PrioridadeAviso.ALTA,
        False,
        2,
        True,
    ),
    (
        "Dia da família",
        "No próximo sábado teremos o Dia da Família, com apresentações culturais, "
        "feira de ciências e praça de alimentação. Entrada gratuita.",
        "geral",
        PrioridadeAviso.BAIXA,
        False,
        1,
        True,
    ),
]

# (título, descrição, dias_relativos, local, quem recebe)
EVENTOS: list[tuple[str, str, int, str, str]] = [
    (
        "Conselho de classe — 2º bimestre",
        "Reunião do conselho com os professores.",
        -20,
        "Sala 12",
        "responsaveis",
    ),
    ("Feira de ciências", "Apresentações dos alunos do 7º ano.", -6, "Ginásio", "turmas"),
    (
        "Reunião de pais — 2º bimestre",
        "Encontro presencial com os responsáveis por turma.",
        9,
        "Auditório",
        "responsaveis",
    ),
    ("Dia da família", "Programação cultural e praça de alimentação.", 16, "Ginásio", "turmas"),
]

SENHA_HASH: str | None = None


def sid(*partes: object) -> uuid.UUID:
    """UUID5 determinístico: a identidade da linha é reproduzível."""
    return uuid.uuid5(NAMESPACE, "|".join(str(p) for p in partes))


def email_professor(codigo_disciplina: str) -> str:
    return f"{codigo_disciplina.lower()}.prof@sge.local"


def senha_hash() -> str:
    """Hasheia uma vez só: bcrypt é caro e todos os usuários compartilham a senha."""
    global SENHA_HASH
    if SENHA_HASH is None:
        SENHA_HASH = hash_password(SENHA)
    return SENHA_HASH


def ids_da_familia() -> dict[str, list[uuid.UUID]]:
    """Todos os IDs que este seed possui. Fonte única para criar e para limpar."""
    ids: dict[str, list[uuid.UUID]] = {
        chave: []
        for chave in (
            "usuario aluno responsavel_aluno serie turma disciplina professor_profiles "
            "alocacao avaliacao nota chamada frequencia wallet movimentacao bracelet "
            "ocorrencia aviso aviso_destinatario aviso_mensagem evento evento_destinatario "
            "notificacao liberacao_boletim prazo_liberacao"
        ).split()
    }

    def add(chave: str, *partes: object) -> uuid.UUID:
        ids[chave].append(sid(*partes))
        return ids[chave][-1]

    for email in (EMAIL_RESPONSAVEL, EMAIL_SECRETARIA):
        add("usuario", "email", email)

    for codigo, _ in DISCIPLINAS:
        add("disciplina", codigo)
        add("usuario", "email", f"{codigo.lower()}.prof@sge.local")
        add("professor_profiles", "email", f"{codigo.lower()}.prof@sge.local")

    for codigo, numero, _, _ in TURMAS:
        add("serie", numero)
        add("turma", codigo, ANO)

    for filho in FILHOS:
        cpf, turma = filho["cpf"], filho["turma"]
        add("aluno", cpf)
        add("responsavel_aluno", cpf, EMAIL_RESPONSAVEL)
        add("matricula", cpf, turma)
        add("wallet", cpf)
        add("bracelet", cpf)

        for i, (tipo, valor, descricao, dias_atras) in enumerate(filho["lancamentos"]):
            add("movimentacao", cpf, i)

        for i, _ in enumerate(filho["ocorrencias"]):
            add("ocorrencia", cpf, i)

        for codigo in filho["disciplinas"]:
            add("alocacao", turma, codigo)
            for bimestre in (1, 2, 3):
                add("avaliacao", cpf, codigo, bimestre)
                add("nota", cpf, codigo, bimestre)
                add("liberacao_boletim", turma, codigo, bimestre)
            for dia in dias_uteis():
                add("chamada", turma, codigo, dia)
                add("frequencia", cpf, codigo, dia)

    for i, aviso in enumerate(AVISOS):
        add("aviso", i)
        add("aviso_destinatario", i)
        if aviso[4]:  # permite_respostas
            add("aviso_mensagem", i)
        if aviso[6]:  # gera notificação
            add("notificacao", i)

    for i, evento in enumerate(EVENTOS):
        add("evento", i)
        destinatarios = (
            [EMAIL_RESPONSAVEL] if evento[4] == "responsaveis" else [t[0] for t in TURMAS]
        )
        for destino in destinatarios:
            add("evento_destinatario", i, destino)

    for bimestre in (1, 2, 3):
        add("prazo_liberacao", ANO, bimestre)

    return ids


def dias_uteis(quantidade: int = 6) -> list[date]:
    """Os `quantidade` dias úteis mais recentes até duas semanas atrás."""
    dias, cursor = [], HOJE - timedelta(days=14)
    while len(dias) < quantidade:
        if cursor.weekday() < 5:
            dias.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(dias))


def momento(dias_atras: int, hora: int = 8) -> datetime:
    return datetime.combine(HOJE - timedelta(days=dias_atras), time(hora), tzinfo=UTC)


# ---------------------------------------------------------------------------
# Criação
# ---------------------------------------------------------------------------


async def criar(session: AsyncSession) -> None:
    # 1. Ano letivo: reaproveita o de 2026 se já existir (não duplica anos).
    ano = (
        await session.execute(select(AnoLetivo).where(AnoLetivo.ano == ANO))
    ).scalar_one_or_none()
    if ano is None:
        ano = AnoLetivo(
            id=sid("ano_letivo", ANO),
            ano=ANO,
            data_inicio=date(2026, 2, 2),
            data_fim=date(2026, 12, 18),
            ativo=True,
        )
        session.add(ano)
    await session.flush()

    # A configuração é única por ano letivo: cria só se faltar.
    existe_config = await session.scalar(
        select(func.count())
        .select_from(ConfiguracaoAcademica)
        .where(ConfiguracaoAcademica.ano_letivo_id == ano.id)
    )
    if not existe_config:
        session.add(
            ConfiguracaoAcademica(
                id=sid("configuracao_academica", ANO),
                ano_letivo_id=ano.id,
                media_aprovacao=7.0,
                frequencia_minima=75.0,
                possui_recuperacao=True,
                media_minima_recuperacao=5.0,
                quantidade_periodos=4,
                ativo=True,
            )
        )

    # 2. Prazos de liberação de boletim.
    for bimestre in (1, 2, 3):
        session.add(
            PrazoLiberacao(
                id=sid("prazo_liberacao", ANO, bimestre),
                ano_letivo_id=ano.id,
                bimestre=bimestre,
                data_limite=DATAS_PRAZO[bimestre],
                hora_limite=time(23, 59, 59),
                notificado_em=momento(20 if bimestre < 3 else 0, 9),
                ativo=True,
            )
        )

    # 3. Séries, turmas e disciplinas.
    for codigo, numero, nome, turno in TURMAS:
        session.add(
            Serie(
                id=sid("serie", numero),
                numero=numero,
                nome=f"{numero}º Ano",
                ativo=True,
            )
        )
        session.add(
            Turma(
                id=sid("turma", codigo, ANO),
                codigo=codigo,
                nome=nome,
                turno=turno,
                vagas_total=30,
                serie_id=sid("serie", numero),
                ano_letivo_id=ano.id,
                ativo=True,
            )
        )

    for codigo, nome in DISCIPLINAS:
        session.add(Disciplina(id=sid("disciplina", codigo), codigo=codigo, nome=nome, ativo=True))

    # 4. Usuários: secretaria, coordenação, responsável e professores.
    def usuario(chave_id: uuid.UUID, nome: str, email: str, perfil: Perfil) -> Usuario:
        return Usuario(
            id=chave_id,
            nome=nome,
            email=email,
            senha_hash=senha_hash(),
            perfil=perfil,
            ativo=True,
        )

    secretaria = usuario(
        sid("usuario", "email", EMAIL_SECRETARIA),
        "Marina Duarte",
        EMAIL_SECRETARIA,
        Perfil.SECRETARIA,
    )
    responsavel = usuario(
        sid("usuario", "email", EMAIL_RESPONSAVEL),
        NOME_RESPONSAVEL,
        EMAIL_RESPONSAVEL,
        Perfil.RESPONSAVEL,
    )
    session.add_all([secretaria, responsavel])

    for indice, (codigo, (nome, formacao)) in enumerate(PROFESSORES.items()):
        email = f"{codigo.lower()}.prof@sge.local"
        uid = sid("usuario", "email", email)
        session.add(usuario(uid, nome, email, Perfil.PROFESSOR))
        session.add(
            ProfessorProfile(
                usuario_id=uid,
                formacao_principal=formacao,
                matricula_funcional=f"PROF-{codigo}",
                data_contratacao=date(2021, 2, 1),
                ativo=True,
            )
        )
    await session.flush()

    # 5. Alocações: professor × turma × disciplina (únicas por turma+disciplina).
    alocacoes: dict[tuple[str, str], Alocacao] = {}
    for filho in FILHOS:
        for codigo in filho["disciplinas"]:
            chave = (filho["turma"], codigo)
            if chave in alocacoes:
                continue
            alocacao = Alocacao(
                id=sid("alocacao", *chave),
                professor_id=sid("usuario", "email", f"{codigo.lower()}.prof@sge.local"),
                turma_id=sid("turma", filho["turma"], ANO),
                disciplina_id=sid("disciplina", codigo),
                data_inicio=date(2026, 2, 2),
            )
            session.add(alocacao)
            alocacoes[chave] = alocacao

    # 6. Filhos, vínculo de responsabilidade, matrícula, carteira e pulseira.
    for filho in FILHOS:
        cpf, turma = filho["cpf"], filho["turma"]
        session.add(
            Aluno(
                id=sid("aluno", cpf),
                nome=filho["nome"],
                data_nascimento=filho["nascimento"],
                cpf=cpf,
                rg=f"{random.randint(10_000_000, 99_999_999)}-{random.randint(100, 999)}",
                endereco="Rua das Acácias, 120 - Jardim Botânico",
                telefone=f"11 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                data_entrada=date(2026, 2, 2),
                ativo=True,
                autonomia_cantina=False,
            )
        )
        session.add(
            ResponsavelAluno(
                aluno_id=sid("aluno", cpf),
                responsavel_id=responsavel.id,
                parentesco=Parentesco.PAI,
                responsavel_financeiro=True,
            )
        )
        session.add(
            Matricula(
                id=sid("matricula", cpf, turma),
                aluno_id=sid("aluno", cpf),
                turma_id=sid("turma", turma, ANO),
                data_matricula=date(2026, 2, 2),
                status=StatusMatricula.ATIVA,
            )
        )
        session.add(
            Wallet(
                id=sid("wallet", cpf),
                aluno_id=sid("aluno", cpf),
                saldo=0,
                status=StatusCarteira.ATIVA,
            )
        )
        session.add(
            Bracelet(
                id=sid("bracelet", cpf),
                uid=f"BC-{sid('bracelet', cpf).hex[:12].upper()}",
                codigo=f"PU-{turma}-{sid('bracelet', cpf).hex[:6].upper()}",
                aluno_id=sid("aluno", cpf),
                status=StatusPulseira.ATIVA,
            )
        )
    await session.flush()

    # 7. Avaliações, notas, liberações e aulas/frequências.
    tipos = {1: TipoAvaliacao.PROVA, 2: TipoAvaliacao.TRABALHO, 3: TipoAvaliacao.ATIVIDADE}
    pesos = {1: 40, 2: 30, 3: 30}
    nomes = dict(DISCIPLINAS)
    for filho in FILHOS:
        cpf, turma = filho["cpf"], filho["turma"]
        for codigo in filho["disciplinas"]:
            alocacao = alocacoes[(turma, codigo)]
            for bimestre in (1, 2, 3):
                avaliacao = Avaliacao(
                    id=sid("avaliacao", cpf, codigo, bimestre),
                    alocacao_id=alocacao.id,
                    titulo=(
                        f"{nomes[codigo]} — {tipos[bimestre].value.capitalize()} "
                        f"({bimestre}º bimestre)"
                    ),
                    tipo=tipos[bimestre],
                    peso=pesos[bimestre],
                    nota_maxima=10.0,
                    bimestre=bimestre,
                    data_aplicacao=DATAS_AVALIACAO[bimestre],
                )
                session.add(avaliacao)
                minimo, maximo = filho["faixa_notas"][codigo]
                session.add(
                    Nota(
                        id=sid("nota", cpf, codigo, bimestre),
                        avaliacao_id=avaliacao.id,
                        matricula_id=sid("matricula", cpf, turma),
                        valor=round(random.uniform(minimo, maximo), 1),
                    )
                )
                session.add(
                    LiberacaoBoletim(
                        id=sid("liberacao_boletim", turma, codigo, bimestre),
                        professor_id=alocacao.professor_id,
                        turma_id=alocacao.turma_id,
                        disciplina_id=alocacao.disciplina_id,
                        alocacao_id=alocacao.id,
                        ano_letivo_id=ano.id,
                        bimestre=bimestre,
                        liberado_em=momento(6 if bimestre < 3 else 2, 11),
                        ativo=True,
                    )
                )

            for dia in dias_uteis():
                chamada = Chamada(
                    id=sid("chamada", turma, codigo, dia),
                    alocacao_id=alocacao.id,
                    data_hora_aula=datetime.combine(dia, time(8, 0)),
                )
                session.add(chamada)
                sorteio = random.random()
                if sorteio < 0.08:
                    status = StatusFrequencia.FALTA_JUSTIFICADA
                elif sorteio < 0.18:
                    status = StatusFrequencia.FALTA
                else:
                    status = StatusFrequencia.PRESENTE
                session.add(
                    Frequencia(
                        id=sid("frequencia", cpf, codigo, dia),
                        chamada_id=chamada.id,
                        matricula_id=sid("matricula", cpf, turma),
                        status=status,
                        observacoes=(
                            "Atestado médico entregue na secretaria."
                            if status == StatusFrequencia.FALTA_JUSTIFICADA
                            else None
                        ),
                    )
                )

    # 8. Movimentações: o saldo do cartão é o fechamento da própria cadeia.
    for filho in FILHOS:
        cpf = filho["cpf"]
        saldo = 0.0
        for i, (tipo, valor, descricao, dias_atras) in enumerate(filho["lancamentos"]):
            anterior = saldo
            saldo = round(saldo + (valor if tipo == TipoMovimentacao.RECARGA else -valor), 2)
            session.add(
                Movimentacao(
                    id=sid("movimentacao", cpf, i),
                    wallet_id=sid("wallet", cpf),
                    tipo=tipo,
                    valor=valor,
                    saldo_anterior=anterior,
                    saldo_posterior=saldo,
                    descricao=descricao,
                    criado_por=responsavel.id,
                    created_at=momento(dias_atras, 12),
                )
            )
        wallet = await session.get(Wallet, sid("wallet", cpf))
        wallet.saldo = saldo

    # 9. Ocorrências.
    for filho in FILHOS:
        cpf = filho["cpf"]
        for i, dados in enumerate(filho["ocorrencias"]):
            titulo, descricao, tipo, severidade, status, dias_atras = dados
            criada = momento(dias_atras, 10)
            resolvida = status == StatusOcorrencia.RESOLVIDA
            session.add(
                Ocorrencia(
                    id=sid("ocorrencia", cpf, i),
                    aluno_id=sid("aluno", cpf),
                    turma_id=sid("turma", filho["turma"], ANO),
                    titulo=titulo,
                    descricao=descricao,
                    tipo=tipo,
                    severidade=severidade,
                    status=status,
                    criado_por=sid("usuario", "email", email_professor(filho["disciplinas"][0])),
                    responsavel_id=responsavel.id if resolvida else None,
                    resolvida_em=criada + timedelta(days=1) if resolvida else None,
                    created_at=criada,
                )
            )

    # 10. Avisos, destinatários, uma resposta e notificações.
    for i, aviso_dados in enumerate(AVISOS):
        titulo, mensagem, tipo, prioridade, com_respostas, dias_atras, notificar = aviso_dados
        aviso = Aviso(
            id=sid("aviso", i),
            titulo=titulo,
            mensagem=mensagem,
            tipo=tipo,
            prioridade=prioridade,
            permite_respostas=com_respostas,
            status=StatusAviso.PUBLICADO,
            criado_por=secretaria.id,
            publicado_em=momento(dias_atras, 8),
        )
        session.add(aviso)
        session.add(
            AvisoDestinatario(
                id=sid("aviso_destinatario", i),
                aviso_id=aviso.id,
                usuario_id=responsavel.id,
            )
        )
        if com_respostas:
            session.add(
                AvisoMensagem(
                    id=sid("aviso_mensagem", i),
                    aviso_id=aviso.id,
                    autor_id=responsavel.id,
                    destinatario_id=secretaria.id,
                    conteudo="Confirmo presença. Poderiam enviar o horário exato, por favor?",
                    created_at=momento(dias_atras - 1, 20),
                )
            )
        if notificar:
            session.add(
                Notificacao(
                    id=sid("notificacao", i),
                    destinatario_id=responsavel.id,
                    tipo=TipoNotificacao.AVISO,
                    titulo=titulo,
                    mensagem=mensagem[:200],
                    canal="inapp",
                    entidade_tipo="aviso",
                    entidade_id=aviso.id,
                    evento_key=f"aviso:{i}",
                    dados={"turmas": ["7A", "5A"]},
                    lida=i == 0,
                )
            )

    # 11. Agenda: eventos passados e futuros.
    for i, (titulo, descricao, em_dias, local, destino) in enumerate(EVENTOS):
        dia = HOJE + timedelta(days=em_dias)
        evento = Evento(
            id=sid("evento", i),
            titulo=titulo,
            descricao=descricao,
            data_inicio=datetime.combine(dia, time(19), tzinfo=UTC),
            data_fim=datetime.combine(dia, time(21), tzinfo=UTC),
            local=local,
            criado_por=secretaria.id,
            perfil_criador=Perfil.SECRETARIA,
            ativo=True,
        )
        session.add(evento)
        if destino == "responsaveis":
            session.add(
                EventoDestinatario(
                    id=sid("evento_destinatario", i, EMAIL_RESPONSAVEL),
                    evento_id=evento.id,
                    tipo_destino=TipoDestinoEvento.RESPONSAVEL,
                    destino_id=responsavel.id,
                )
            )
        else:
            for codigo, _, _, _ in TURMAS:
                session.add(
                    EventoDestinatario(
                        id=sid("evento_destinatario", i, codigo),
                        evento_id=evento.id,
                        tipo_destino=TipoDestinoEvento.TURMA,
                        destino_id=sid("turma", codigo, ANO),
                    )
                )

    await session.commit()


# ---------------------------------------------------------------------------
# Limpeza
# ---------------------------------------------------------------------------


async def limpar(session: AsyncSession) -> bool:
    """Apaga a cadeia inteira DESTA família, sem tocar em nada de terceiros.

    Cada tabela é deletada pelos IDs determinísticos do próprio seed. Como os
    IDs são derivados de ``NAMESPACE`` + identidade do objeto, um ``--limpar``
    nunca alcança uma série, turma, disciplina, professor ou usuário que outra
    pessoa tenha criado.
    """
    existe = await session.scalar(select(Usuario.id).where(Usuario.email == EMAIL_RESPONSAVEL))
    if not existe:
        return False

    ids = ids_da_familia()
    resp = existe

    # A IA registra conversas do usuário: apaga antes de remover o usuário.
    conversas = list(
        (await session.execute(select(Conversa.id).where(Conversa.usuario_id == resp))).scalars()
    )
    if conversas:
        await session.execute(delete(Mensagem).where(Mensagem.conversa_id.in_(conversas)))
        await session.execute(delete(Conversa).where(Conversa.id.in_(conversas)))

    # Ordem inversa das dependências. `coluna` é a PK da tabela alvo.
    alvos: list[tuple[type, str, str]] = [
        (Sessao, "usuario_id", "usuario"),
        (Notificacao, "id", "notificacao"),
        (Movimentacao, "id", "movimentacao"),
        (Nota, "id", "nota"),
        (Frequencia, "id", "frequencia"),
        (Chamada, "id", "chamada"),
        (Avaliacao, "id", "avaliacao"),
        (LiberacaoBoletim, "id", "liberacao_boletim"),
        (PrazoLiberacao, "id", "prazo_liberacao"),
        (AvisoMensagem, "id", "aviso_mensagem"),
        (AvisoDestinatario, "id", "aviso_destinatario"),
        (Aviso, "id", "aviso"),
        (EventoDestinatario, "id", "evento_destinatario"),
        (Evento, "id", "evento"),
        (Ocorrencia, "id", "ocorrencia"),
        (Bracelet, "id", "bracelet"),
        (Wallet, "id", "wallet"),
        (Matricula, "id", "matricula"),
        (ResponsavelAluno, "aluno_id", "aluno"),
        (Aluno, "id", "aluno"),
        (Alocacao, "id", "alocacao"),
        (ProfessorProfile, "usuario_id", "professor_profiles"),
        (Turma, "id", "turma"),
        (Serie, "id", "serie"),
        (Disciplina, "id", "disciplina"),
        (Usuario, "id", "usuario"),
    ]
    for modelo, coluna, chave in alvos:
        alvos_id = ids[chave]
        if alvos_id:
            await session.execute(delete(modelo).where(getattr(modelo, coluna).in_(alvos_id)))

    # A configuração é única por ano letivo: recriamos do zero junto com o ano.
    await session.execute(
        delete(ConfiguracaoAcademica).where(
            ConfiguracaoAcademica.id == sid("configuracao_academica", ANO)
        )
    )

    await session.commit()
    return True


# ---------------------------------------------------------------------------


async def main() -> None:
    modo = next((a for a in sys.argv[1:] if a in ("--reset", "--limpar")), None)
    async with SessionLocal() as session:
        ja_existe = await session.scalar(
            select(Usuario.id).where(Usuario.email == EMAIL_RESPONSAVEL)
        )

        if modo == "--limpar":
            ok = await limpar(session)
            print(
                f"✔ Família {EMAIL_RESPONSAVEL} removida."
                if ok
                else f"Nada a remover: {EMAIL_RESPONSAVEL} não existe."
            )
            return

        if ja_existe and modo != "--reset":
            print(f"Seed ignorado: {EMAIL_RESPONSAVEL} já existe. Use --reset para recriar.")
            return

        if ja_existe:
            print(f"▶ --reset: removendo a família {EMAIL_RESPONSAVEL}...")
            await limpar(session)

        print(f"▶ Criando {NOME_RESPONSAVEL} <{EMAIL_RESPONSAVEL}> e a cadeia de dados...")
        await criar(session)
        print("✔ Commitado.")


if __name__ == "__main__":
    asyncio.run(main())
