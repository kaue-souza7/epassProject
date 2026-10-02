"""Grade horária: quando cada turma tem aula e com quem.

Por que este módulo existe
-------------------------
Até aqui o sistema só sabia *quem* é professor de uma turma (a `Alocacao`), e não
*quando*. Isso não basta para duas perguntas que o dia a dia do ensino fundamental
exige: "o professor da Maria tem aula com ela hoje?" e "que aula vem agora?".

No ensino fundamental 1 a resposta prática é curta: a turma tem um turno, e no mesmo
turno costuma haver um ou dois professores. A grade registra o par (dia da semana,
janela de horário) e resolve o resto.

A grade NÃO substitui a `Alocacao`. A `Alocacao` é quem legitimiza o professor a ver
os alunos da turma — é dela que sai a autorização. A grade é a agenda: mesmo professor,
mesma turma, mesmo dia, em dois horários diferentes, é a mesma alocação em dois
momentos. Por isso `disciplina_id` aqui é opcional: no fundamental 1 o mesmo professor
costuma ensinar mais de uma disciplina e a agenda não precisa escolher uma.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Time,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.shared.enums import DiaSemana

# Brasil não observa horário de verão desde 2019, então -03:00 é constante. Fixo em
# vez de `zoneinfo` de propósito: o SGE roda em contêiner com tzdata mínimo, e um offset
# explícito é mais previsível do que uma dependência de tzdata que pode faltar.
TZ_ESCOLA = timezone(timedelta(hours=-3))


class HorarioAula(Base):
    """Uma janela de aula: uma turma, um professor, num dia e intervalo fixos.

    Invariantes impostas no banco:

    - `hora_fim > hora_inicio` — janela invertida é sempre erro de digitação.
    - `(turma_id, dia_semana, hora_inicio)` é único entre as ativas — duas aulas não
      começam no mesmo minuto na mesma turma.
    - um mesmo professor não pode ter duas janelas sobrepostas no mesmo dia; isso é
      validado no service (o banco não tem índice para interseção de intervalos), mas o
      índice por `(professor_id, dia_semana)` deixa a consulta barata.
    """

    __tablename__ = "horarios_aula"

    __table_args__ = (
        CheckConstraint("hora_fim > hora_inicio", name="ck_horario_hora_fim"),
        CheckConstraint(
            "hora_inicio >= '06:00' AND hora_inicio <= '22:00'",
            name="ck_horario_hora_inicio_plausivel",
        ),
        Index(
            "uq_horarios_turma_dia_hora",
            "turma_id",
            "dia_semana",
            "hora_inicio",
            unique=True,
            postgresql_where=text("ativo"),
            sqlite_where=text("ativo"),
        ),
        Index("ix_horarios_turma_dia", "turma_id", "dia_semana"),
        Index("ix_horarios_professor_dia", "professor_id", "dia_semana"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    turma_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("turmas.id"), nullable=False, index=True,
    )
    professor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("professor_profiles.usuario_id"),
        nullable=False,
        index=True,
    )
    # Opcional de propósito: no fundamental 1 o mesmo professor costuma lecionar mais de
    # uma disciplina, e a agenda não precisa (e não deve) escolher uma delas.
    disciplina_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("disciplinas.id"), nullable=True,
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(SAEnum(DiaSemana), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fim: Mapped[time] = mapped_column(Time, nullable=False)
    # Desativar é preferível a apagar: trocar o turno de uma turma mexe em todas as
    # janelas dela, e o registro de qual professor esteve com qual turma em que dia
    # continua valendo para auditoria de frequência.
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    turma: Mapped["Turma"] = relationship("Turma", lazy="selectin")
    professor: Mapped["ProfessorProfile"] = relationship(
        "ProfessorProfile", lazy="selectin", foreign_keys=[professor_id],
    )
    disciplina: Mapped["Disciplina | None"] = relationship(
        "Disciplina", lazy="selectin",
    )


# `date.weekday()` é segunda=0 ... domingo=6. Domingo não existe no enum porque a escola
# não dá aula nele, e `dia_semana_de` devolve None para ele — que é a resposta correta.
_WEEKDAY_TO_DIA: dict[int, DiaSemana] = {
    0: DiaSemana.SEG,
    1: DiaSemana.TER,
    2: DiaSemana.QUA,
    3: DiaSemana.QUI,
    4: DiaSemana.SEX,
    5: DiaSemana.SAB,
}

DIA_TO_WEEKDAY: dict[DiaSemana, int] = {dia: idx for idx, dia in _WEEKDAY_TO_DIA.items()}


def dia_semana_de(dia: date) -> DiaSemana | None:
    """Dia da semana de uma data, ou `None` se for domingo (sem aula)."""
    return _WEEKDAY_TO_DIA.get(dia.weekday())


def horarios_sobrepostos(
    inicio_a: time, fim_a: time, inicio_b: time, fim_b: time,
) -> bool:
    """Duas janelas `[inicio, fim)` se sobrepõem.

    Encostar não é sobrepor: uma aula que termina 09:00 e outra que começa 09:00 são
    perfeitamente compatíveis, e no fundamental 1 isso acontece o dia inteiro. Por isso
    a comparação é meio-aberta — daí o `<` estrito em vez de `<=`.
    """
    return inicio_a < fim_b and inicio_b < fim_a


def agora_hora_escuela() -> time:
    """Hora local da escola como `time` puro, para comparar com `hora_inicio`."""
    return datetime.now(TZ_ESCOLA).time()
