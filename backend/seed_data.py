import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import text

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal


def uid():
    return str(uuid.uuid4())


# Ordem FK-segura: filhos antes dos pais. Inclui as tabelas de comunicação.
_TABELAS_RESET = [
    # comunicação
    "push_tickets", "push_tokens", "avisos_mensagens", "avisos_destinatarios",
    "notificacoes", "ocorrencias_historico", "avisos", "ocorrencias",
    # cantina
    "itens_pedido", "pedidos", "movimentacoes_estoque",
    "programacao_itens", "programacao_cantina",
    # financeiro/acadêmico
    "movimentacoes", "notas", "frequencias", "chamadas", "avaliacoes",
    "liberacoes_boletim", "prazos_liberacao", "alocacoes",
    "wallets", "bracelets", "matriculas", "responsavel_aluno",
    "professor_profiles", "configuracoes_academicas",
    # agenda/auth
    "sessoes", "evento_destinatarios", "eventos",
    # base
    "alunos", "usuarios", "produtos", "cantina_config",
]


async def _limpar_tudo(session) -> None:
    print("▶ Limpando dados existentes...")
    total = 0
    for t in _TABELAS_RESET:
        r = await session.execute(text(f"SELECT COUNT(*) FROM {t}"))
        cnt = r.scalar()
        await session.execute(text(f"DELETE FROM {t}"))
        total += cnt
        if cnt > 0:
            print(f"  {t}: {cnt}")
    await session.flush()
    print(f"  Total removidos: {total}\n")


async def seed():
    reset = "--reset" in sys.argv or os.getenv("SEED_RESET") == "1"
    print(f"Conectando ao banco: {settings.DATABASE_URL}")
    async with SessionLocal() as session:
        # Sem --reset/SEED_RESET=1, o seed só popula banco vazio. Isso evita
        # apagar dados reais (avisos/ocorrências/carteira) a cada restart.
        existentes = (await session.execute(
            text("SELECT COUNT(*) FROM usuarios")
        )).scalar()
        if existentes and not reset:
            print(
                f"Seed ignorado: banco já possui {existentes} usuário(s). "
                "Use `python seed_data.py --reset` para recriar os dados de exemplo.\n"
            )
            return

        # ── 1. CLEAN ALL DATA (apenas com --reset) ──
        await _limpar_tudo(session)

        senha = hash_password("123456")
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # ── 2. BASE ENTITIES (cria mínimos se o banco for novo) ──
        r = await session.execute(text("SELECT id FROM anos_letivos WHERE ativo = true LIMIT 1"))
        row = r.fetchone()
        if row is None:
            ano_letivo_id = uid()
            await session.execute(text(
                "INSERT INTO anos_letivos (id,ano,data_inicio,data_fim,ativo,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),:ano,'2026-02-01','2026-12-15',true,:now,:now)"
            ), {"id": ano_letivo_id, "ano": date.today().year, "now": now})
            print(f"  ano letivo base criado ({date.today().year})")
        else:
            ano_letivo_id = row[0]

        r = await session.execute(text("SELECT id FROM series WHERE ativo = true LIMIT 1"))
        row = r.fetchone()
        if row is None:
            serie_id = uid()
            await session.execute(text(
                "INSERT INTO series (id,numero,nome,descricao,ativo,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),1,'1º Ano','Série inicial',true,:now,:now)"
            ), {"id": serie_id, "now": now})
        else:
            serie_id = row[0]

        r = await session.execute(text("SELECT id FROM turmas WHERE ativo = true LIMIT 1"))
        row = r.fetchone()
        if row is None:
            turma_id = uid()
            await session.execute(text(
                "INSERT INTO turmas (id,codigo,nome,serie_id,ano_letivo_id,turno,vagas_total,ativo,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),'1A','Turma 1A',CAST(:serie AS uuid),CAST(:ano AS uuid),"
                "CAST('MANHA' AS turno),30,true,:now,:now)"
            ), {"id": turma_id, "serie": serie_id, "ano": ano_letivo_id, "now": now})
            print("  turma base criada (1A)")
        else:
            turma_id = row[0]

        r = await session.execute(text("SELECT id FROM disciplinas WHERE ativo = true LIMIT 1"))
        row = r.fetchone()
        if row is None:
            disciplina_id = uid()
            await session.execute(text(
                "INSERT INTO disciplinas (id,codigo,nome,descricao,ativo,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),'MAT','Matemática',NULL,true,:now,:now)"
            ), {"id": disciplina_id, "now": now})
            print("  disciplina base criada (Matemática)")
        else:
            disciplina_id = row[0]
        await session.flush()

        kp = uid()  # kaue professor
        ka = uid()  # kaue coordenador/admin
        ri = uid()  # richard
        bi = uid()  # binio (responsavel)
        ci = uid()  # cantineiro
        a1 = uid()  # aluno binio 1
        a2 = uid()  # aluno binio 2

        # ── 3. CREATE USERS ──
        print("▶ Criando usuarios...")
        for n, e, p, i in [
            ("Kaue Professor", "kauekaue960@gmail.com", "PROFESSOR", kp),
            ("Kaue Coordenador", "kauec282@gmail.com", "ADMIN", ka),
            ("Richard", "elorichard95@gmail.com", "PROFESSOR", ri),
            ("Binio", "biniosoares@gmail.com", "RESPONSAVEL", bi),
            ("Maria Cantina", "maria.cantina@example.com", "CANTINEIRO", ci),
        ]:
            await session.execute(text(
                "INSERT INTO usuarios (id,nome,email,senha_hash,perfil,ativo,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),:nome,:email,:senha,CAST(:perfil AS perfil),true,:now,:now)"
            ), {"id": i, "nome": n, "email": e, "senha": senha, "perfil": p, "now": now})
            print(f"  {p}: {n} <{e}>")
        await session.flush()

        # ── 4. PROFESSOR PROFILES ──
        print("\n▶ Criando perfis de professor...")
        await session.execute(text(
            "INSERT INTO professor_profiles (usuario_id,formacao_principal,matricula_funcional,data_contratacao,ativo,created_at,updated_at) "
            "VALUES (CAST(:uid AS uuid),'Licenciatura','PROF-KAUE-001','2024-01-15',true,:now,:now)"
        ), {"uid": kp, "now": now})
        await session.execute(text(
            "INSERT INTO professor_profiles (usuario_id,formacao_principal,matricula_funcional,data_contratacao,ativo,created_at,updated_at) "
            "VALUES (CAST(:uid AS uuid),'Licenciatura','PROF-RICH-002','2024-01-15',true,:now,:now)"
        ), {"uid": ri, "now": now})
        print(f"  Kaue Professor (PROF-KAUE-001)")
        print(f"  Richard (PROF-RICH-002)")
        await session.flush()

        # ── 5. CREATE STUDENTS ──
        print("\n▶ Criando alunos...")
        await session.execute(text(
            "INSERT INTO alunos (id,nome,data_nascimento,data_entrada,ativo,autonomia_cantina,created_at,updated_at) "
            "VALUES (CAST(:id AS uuid),:nome,:nasc,'2026-02-01',true,false,:now,:now)"
        ), {"id": a1, "nome": "Aluno Binio 1", "nasc": date(2015, 3, 10), "now": now})
        await session.execute(text(
            "INSERT INTO alunos (id,nome,data_nascimento,data_entrada,ativo,autonomia_cantina,created_at,updated_at) "
            "VALUES (CAST(:id AS uuid),:nome,:nasc,'2026-02-01',true,false,:now,:now)"
        ), {"id": a2, "nome": "Aluno Binio 2", "nasc": date(2015, 7, 22), "now": now})
        print(f"  Aluno Binio 1")
        print(f"  Aluno Binio 2")
        await session.flush()

        # ── 6. LINK STUDENTS TO BINIO ──
        print("\n▶ Vinculando alunos ao Binio...")
        for aid in [a1, a2]:
            await session.execute(text(
                "INSERT INTO responsavel_aluno (aluno_id,responsavel_id,parentesco,responsavel_financeiro) "
                "VALUES (CAST(:aluno AS uuid),CAST(:resp AS uuid),'PAI',true)"
            ), {"aluno": aid, "resp": bi})
        print(f"  2 vinculos (pai)")
        await session.flush()

        # ── 7. CREATE WALLETS ──
        print("\n▶ Criando wallets...")
        for aid, nome in [(a1, "Aluno Binio 1"), (a2, "Aluno Binio 2")]:
            await session.execute(text(
                "INSERT INTO wallets (id,aluno_id,saldo,status,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),CAST(:aluno AS uuid),0.00,'ATIVA',:now,:now)"
            ), {"id": uid(), "aluno": aid, "now": now})
            print(f"  {nome} -> wallet (R$ 0,00)")
        await session.flush()

        # ── 8. CREATE ENROLLMENTS ──
        print("\n▶ Criando matriculas...")
        for aid, nome in [(a1, "Aluno Binio 1"), (a2, "Aluno Binio 2")]:
            await session.execute(text(
                "INSERT INTO matriculas (id,aluno_id,turma_id,data_matricula,status,created_at,updated_at) "
                "VALUES (CAST(:id AS uuid),CAST(:aluno AS uuid),CAST(:turma AS uuid),'2026-02-01','ATIVA',:now,:now)"
            ), {"id": uid(), "aluno": aid, "turma": turma_id, "now": now})
            print(f"  {nome} -> 1A (ATIVA)")
        await session.flush()

        # ── 9. CREATE ALLOCATION ──
        print("\n▶ Criando alocacao...")
        await session.execute(text(
            "INSERT INTO alocacoes (id,professor_id,turma_id,disciplina_id,data_inicio,created_at,updated_at) "
            "VALUES (CAST(:id AS uuid),CAST(:prof AS uuid),CAST(:turma AS uuid),CAST(:disc AS uuid),'2026-02-01',:now,:now)"
        ), {"id": uid(), "prof": kp, "turma": turma_id, "disc": disciplina_id, "now": now})
        print(f"  Kaue Professor -> 1A / Matematica")
        await session.flush()

        # ── 10. ACADEMIC CONFIG ──
        print("\n▶ Criando configuracao academica...")
        await session.execute(text(
            "INSERT INTO configuracoes_academicas "
            "(id,ano_letivo_id,media_aprovacao,frequencia_minima,possui_recuperacao,media_minima_recuperacao,quantidade_periodos,ativo,created_at,updated_at) "
            "VALUES (CAST(:id AS uuid),CAST(:ano AS uuid),6.0,75.0,true,4.0,4,true,:now,:now)"
        ), {"id": uid(), "ano": ano_letivo_id, "now": now})
        print(f"  Config academica criada")

        await session.commit()
        print()
        print("=" * 50)
        print("  SEED CONCLUIDO COM SUCESSO")
        print("=" * 50)
        print()
        print("Usuarios criados:")
        print(f"  kauekaue960@gmail.com / 123456  (PROFESSOR)")
        print(f"  kauec282@gmail.com    / 123456  (ADMIN)")
        print(f"  elorichard95@gmail.com/ 123456  (PROFESSOR)")
        print(f"  biniosoares@gmail.com / 123456  (RESPONSAVEL)")
        print(f"  maria.cantina@example.com / 123456  (CANTINEIRO)")
        print()
        print("Alunos criados:")
        print(f"  Aluno Binio 1 -> 1A (vinculado ao Binio)")
        print(f"  Aluno Binio 2 -> 1A (vinculado ao Binio)")
        print()


if __name__ == "__main__":
    asyncio.run(seed())
