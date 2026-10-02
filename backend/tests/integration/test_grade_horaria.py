"""Grade horária: criação, conflitos e a consulta do dia.

O que este arquivo trava, além do CRUD:

1. A janela invertida e o professor não alocado são recusados — os dois são
   silenciosamente aceitos pelo banco se o service não olhar.
2. A sobreposição é recusada nos DOIS lados (turma e professor), e as duas mensagens
   são diferentes porque são problemas diferentes.
3. Encostar horários NÃO é sobrepor: 09:00-10:00 e 10:00-11:00 convivem, e no
   fundamental 1 isso acontece o dia inteiro.
4. `aulas-do-dia` é a base do aviso de ausência: ela precisa devolver o professor
   certo, deduplicado, e dizer que domingo não tem aula.
"""
import uuid
from datetime import UTC, date, datetime, time as _time, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.schedule.models import HorarioAula, dia_semana_de, horarios_sobrepostos
from app.shared.enums import Perfil, StatusMatricula
from tests.factories import (
    create_alocacao,
    create_aluno,
    create_horario_aula,
    create_matricula,
    create_professor,
    create_responsavel_aluno,
    create_turma,
    create_usuario,
)


def _auth(user) -> dict:
    token = create_access_token(
        subject=str(user.id), extra_claims={"perfil": user.perfil.value},
    )
    return {"Authorization": f"Bearer {token}"}


async def _cenario(session: AsyncSession):
    """Turma, aluno matriculado, dois professores alocados e um responsável."""
    admin = await create_usuario(session, perfil=Perfil.ADMIN, nome="Admin")
    secretaria = await create_usuario(session, perfil=Perfil.SECRETARIA, nome="Secretaria")
    responsavel = await create_usuario(session, perfil=Perfil.RESPONSAVEL, nome="Mãe")

    turma = await create_turma(session, codigo=f"G{uuid.uuid4().hex[:4]}")
    aluno = await create_aluno(session, nome="Maria Silva")
    await create_responsavel_aluno(session, aluno_id=aluno.id, responsavel_id=responsavel.id)
    await create_matricula(
        session, aluno_id=aluno.id, turma_id=turma.id, status=StatusMatricula.ATIVA,
    )

    prof1 = await create_professor(session)
    prof2 = await create_professor(session)
    await create_alocacao(session, professor_id=prof1.usuario_id, turma_id=turma.id)
    await create_alocacao(session, professor_id=prof2.usuario_id, turma_id=turma.id)

    await session.commit()
    return {
        "admin": admin, "secretaria": secretaria, "responsavel": responsavel,
        "turma": turma, "aluno": aluno,
        "prof1": prof1.usuario_id, "prof2": prof2.usuario_id,
    }


# ── Utilitários puros ───────────────────────────────────────────


def test_horarios_que_encostam_nao_sobrepoem():
    from datetime import time as t

    assert horarios_sobrepostos(t(9), t(10), t(10), t(11)) is False
    assert horarios_sobrepostos(t(10), t(11), t(9), t(10)) is False
    assert horarios_sobrepostos(t(9), t(10), t(9, 30), t(11)) is True
    assert horarios_sobrepostos(t(9), t(11), t(10), t(12)) is True


def test_dia_semana_de_ignora_domingo():
    # 2026-06-07 é um domingo.
    assert dia_semana_de(date(2026, 6, 7)) is None
    assert dia_semana_de(date(2026, 6, 1)) == "seg"


# ── Criação ─────────────────────────────────────────────────────


async def test_cria_janela_de_aula(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    client.headers = _auth(c["admin"])

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof1"]),
        "dia_semana": "seg",
        "hora_inicio": "08:00",
        "hora_fim": "08:50",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["dia_semana"] == "seg"
    assert data["hora_inicio"].startswith("08:00")
    assert data["turma_codigo"] == c["turma"].codigo
    assert data["ativo"] is True


async def test_recusa_janela_invertida(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    client.headers = _auth(c["admin"])

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof1"]),
        "dia_semana": "seg",
        "hora_inicio": "09:00",
        "hora_fim": "08:00",
    })
    assert resp.status_code == 422, resp.text


async def test_recusa_professor_nao_alocado(client: AsyncClient, session: AsyncSession):
    """A janela amarra a agenda à autorização.

    Sem isto, um professor sem alocação entraria na grade e o aviso de ausência
    notificaria alguém que nunca dá aula na turma.
    """
    c = await _cenario(session)
    outro = await create_professor(session)
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(outro.usuario_id),
        "dia_semana": "seg",
        "hora_inicio": "08:00",
        "hora_fim": "08:50",
    })
    assert resp.status_code == 400, resp.text
    assert "alocado" in resp.json()["message"].lower()


async def test_professor_nao_pode_escrever_a_grade(client: AsyncClient, session: AsyncSession):
    from app.shared.enums import Perfil

    c = await _cenario(session)
    prof_usuario = await session.get(type(c["admin"]), c["prof1"])
    assert prof_usuario.perfil == Perfil.PROFESSOR
    client.headers = _auth(prof_usuario)

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof1"]),
        "dia_semana": "seg",
        "hora_inicio": "08:00",
        "hora_fim": "08:50",
    })
    assert resp.status_code == 403, resp.text


# ── Conflitos ───────────────────────────────────────────────────


async def test_recusa_sobreposicao_na_turma(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="09:00",
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    # Outro professor, mesma turma, horário sobreposto.
    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof2"]),
        "dia_semana": "seg",
        "hora_inicio": "08:30",
        "hora_fim": "09:30",
    })
    assert resp.status_code == 409, resp.text
    assert "turma" in resp.json()["message"].lower()


async def test_recusa_professor_em_duas_turmas(client: AsyncClient, session: AsyncSession):
    """Professor escalado em dois lugares no mesmo horário.

    A mensagem é diferente da de conflito de turma de propósito: aqui o problema é o
    professor, e é o que o ele precisa entender para se corrigir.
    """
    c = await _cenario(session)
    outra = await create_turma(session, codigo=f"H{uuid.uuid4().hex[:4]}")
    await create_alocacao(session, professor_id=c["prof1"], turma_id=outra.id)
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="09:00",
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.post("/schedule", json={
        "turma_id": str(outra.id),
        "professor_id": str(c["prof1"]),
        "dia_semana": "seg",
        "hora_inicio": "08:30",
        "hora_fim": "09:30",
    })
    assert resp.status_code == 409, resp.text
    msg = resp.json()["message"].lower()
    assert "professor" in msg and "outra turma" in msg


async def test_permite_horarios_que_encostam(client: AsyncClient, session: AsyncSession):
    """09:00-10:00 e 10:00-11:00 na mesma turma convivem."""
    c = await _cenario(session)
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="09:00", hora_fim="10:00",
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof2"]),
        "dia_semana": "seg",
        "hora_inicio": "10:00",
        "hora_fim": "11:00",
    })
    assert resp.status_code == 201, resp.text


async def test_dias_diferentes_nao_conflitam(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="09:00",
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof2"]),
        "dia_semana": "ter",
        "hora_inicio": "08:00",
        "hora_fim": "09:00",
    })
    assert resp.status_code == 201, resp.text


async def test_desativar_libera_o_horario(client: AsyncClient, session: AsyncSession):
    """Professor substituto ocupa o horário depois que o titular sai da grade."""
    c = await _cenario(session)
    original = await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="09:00",
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.patch(f"/schedule/{original.id}/desativar")
    assert resp.status_code == 200, resp.text
    assert resp.json()["ativo"] is False

    resp = await client.post("/schedule", json={
        "turma_id": str(c["turma"].id),
        "professor_id": str(c["prof2"]),
        "dia_semana": "seg",
        "hora_inicio": "08:00",
        "hora_fim": "09:00",
    })
    assert resp.status_code == 201, resp.text


async def test_editar_nao_colide_com_si_mesmo(client: AsyncClient, session: AsyncSession):
    """Mudar a hora de fim não pode colidir com a própria janela."""
    c = await _cenario(session)
    h = await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="09:00",
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.put(f"/schedule/{h.id}", json={"hora_fim": "10:00"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["hora_fim"].startswith("10:00")


# ── Consulta do dia ─────────────────────────────────────────────


async def test_aulas_do_dia_traz_o_professor_certo(
    client: AsyncClient, session: AsyncSession,
):
    c = await _cenario(session)
    hoje = date.today()
    dia = dia_semana_de(hoje)
    if dia is None:
        pytest.skip("Teste rodou num domingo; a escola não dá aula")

    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana=dia,
        hora_inicio="08:00", hora_fim="08:50",
    )
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana=dia,
        hora_inicio="10:00", hora_fim="10:50",
    )
    # Professor que dá aula só na quinta — não entra no resolving de hoje.
    outra_dia = "qui" if dia != "qui" else "sex"
    await create_horario_aula(
        session, c["turma"].id, c["prof2"], dia_semana=outra_dia,
        hora_inicio="08:00", hora_fim="08:50",
    )
    await session.commit()

    client.headers = _auth(c["admin"])
    resp = await client.get(f"/schedule/aulas-do-dia?aluno_id={c['aluno'].id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["sem_aula"] is False
    assert data["turma_codigo"] == c["turma"].codigo
    assert len(data["aulas"]) == 2
    # Duas janelas do MESMO professor viram um destinatário só — notificar duas
    # vezes seria ruído para a professora.
    assert data["professores_ids"] == [str(c["prof1"])]
    assert c["prof2"] not in data["professores_ids"]


async def test_aulas_do_dia_sem_grade(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    client.headers = _auth(c["admin"])

    resp = await client.get(f"/schedule/aulas-do-dia?aluno_id={c['aluno'].id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["sem_aula"] is True
    assert data["motivo_sem_aula"]
    assert data["professores_ids"] == []


async def test_responsavel_so_consulta_o_proprio_filho(
    client: AsyncClient, session: AsyncSession,
):
    """A rota não pode virar oráculo de qual turma e professor um aluno tem hoje."""
    c = await _cenario(session)
    outro_aluno = await create_aluno(session, nome="Aluno de outra família")
    await create_matricula(session, aluno_id=outro_aluno.id, turma_id=c["turma"].id)
    await session.commit()

    client.headers = _auth(c["responsavel"])
    resp = await client.get(f"/schedule/aulas-do-dia?aluno_id={outro_aluno.id}")
    assert resp.status_code == 403, resp.text


async def test_responsavel_consulta_o_proprio_filho(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    client.headers = _auth(c["responsavel"])

    resp = await client.get(f"/schedule/aulas-do-dia?aluno_id={c['aluno'].id}")
    assert resp.status_code == 200, resp.text


async def test_grid_da_turma(client: AsyncClient, session: AsyncSession):
    c = await _cenario(session)
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="08:50",
    )
    await create_horario_aula(
        session, c["turma"].id, c["prof1"], dia_semana="seg",
        hora_inicio="08:00", hora_fim="08:50", ativo=False,
    )
    await session.commit()
    client.headers = _auth(c["admin"])

    resp = await client.get(f"/schedule/grid/{c['turma'].id}")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1, "A janela desativada não vem por padrão"

    resp = await client.get(f"/schedule/grid/{c['turma'].id}?incluir_inativos=true")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


async def test_database_rejeita_prioridade_fora_do_dominio(session: AsyncSession):
    """A CHECK constraint é a garantia real; o service só evita o erro mais comum.

    Sem ela, um `prioridade="urgente"` (que o schema Pydantic rejeita, mas um INSERT
    manual passaria) viraria um cartão sem cor nenhuma na tela de avisos.
    """
    from sqlalchemy.exc import IntegrityError

    from app.modules.communication.models import Aviso
    from app.shared.enums import PrioridadeAviso

    admin = await create_usuario(session, perfil="admin")
    await session.commit()

    session.add(Aviso(
        titulo="Prioridade inválida",
        mensagem="Teste",
        tipo="geral",
        prioridade="urgente",          # fora de {BAIXA, MEDIA, ALTA}
        permite_respostas=False,
        status="publicado",
        criado_por=admin.id,
        publicado_em=datetime.now(UTC),
    ))
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_database_rejeita_hora_fim_antes_do_inicio(session: AsyncSession):
    from datetime import time as t

    from sqlalchemy.exc import IntegrityError

    c = await _cenario(session)
    session.add(HorarioAula(
        turma_id=c["turma"].id, professor_id=c["prof1"], dia_semana="seg",
        hora_inicio=t(10, 0), hora_fim=t(9, 0),   # invertida
        ativo=True,
    ))
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()
