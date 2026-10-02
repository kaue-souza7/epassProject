import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  allocationsApi,
  classesApi,
  scheduleApi,
  subjectsApi,
  teachersApi,
  DIAS_SEMANA_LABEL,
  DIAS_SEMANA_ORDEM,
  type DiaSemana,
  type HorarioAula,
} from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ErrorState } from "../../components/ui/ErrorState";
import { Skeleton } from "../../components/ui/Skeleton";
import { CalendarClock, Info, Plus, Pencil, Trash2, RotateCcw } from "lucide-react";

const TURNO_LABEL: Record<string, string> = {
  manha: "Manhã",
  tarde: "Tarde",
  integral: "Integral",
};

/** "09:00" — o backend devolve `time` sem segundos, mas normalizar protege contra "09:00:00". */
const hhmm = (v: string) => v.slice(0, 5);

function AulaForm({
  open,
  onClose,
  turmaId,
  editando,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  turmaId: string;
  editando: HorarioAula | null;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [professorId, setProfessorId] = useState(editando?.professor_id ?? "");
  const [disciplinaId, setDisciplinaId] = useState(editando?.disciplina_id ?? "");
  const [dia, setDia] = useState<DiaSemana>(editando?.dia_semana ?? "seg");
  const [inicio, setInicio] = useState(editando ? hhmm(editando.hora_inicio) : "08:00");
  const [fim, setFim] = useState(editando ? hhmm(editando.hora_fim) : "08:50");

  // Só entram professores que têm alocação ativa nesta turma — é a mesma regra que o
  // backend valida, e oferecer os demais aqui só geraria um 400 inútil.
  const { data: alocacoes } = useQuery({
    queryKey: ["allocations", { turma_id: turmaId, only_active: true }],
    queryFn: () =>
      allocationsApi.list({ turma_id: turmaId, only_active: true, size: 100 }),
    enabled: open && !!turmaId,
  });

  // `allocationsApi` não devolve o nome do professor; a listagem de professores é quem
  // traz. Sem isto o select mostraria UUIDs, ilegíveis para a secretaria.
  const { data: professores } = useQuery({
    queryKey: ["teachers", "todos"],
    queryFn: () => teachersApi.list({ only_active: true, size: 100 }),
    enabled: open,
  });

  const { data: disciplinas } = useQuery({
    queryKey: ["subjects"],
    queryFn: () => subjectsApi.list(),
    enabled: open,
  });

  const nomeProfessor = useMemo(() => {
    const mapa = new Map<string, string>();
    for (const p of professores?.items ?? []) mapa.set(p.usuario_id, p.nome);
    return mapa;
  }, [professores]);

  const disciplinaNome = useMemo(() => {
    const mapa = new Map<string, string>();
    for (const d of disciplinas ?? []) mapa.set(d.id, d.nome);
    return mapa;
  }, [disciplinas]);

  const alocacoesDesteProfessor = useMemo(
    () => (alocacoes?.items ?? []).filter((a) => a.professor_id === professorId),
    [alocacoes, professorId],
  );

  const opcoesProfessor = useMemo(() => {
    const vistos = new Set<string>();
    const out: { value: string; label: string }[] = [];
    for (const a of alocacoes?.items ?? []) {
      if (vistos.has(a.professor_id)) continue;
      vistos.add(a.professor_id);
      out.push({
        value: a.professor_id,
        label: nomeProfessor.get(a.professor_id) ?? `Professor ${a.professor_id.slice(0, 8)}`,
      });
    }
    return out;
  }, [alocacoes, nomeProfessor]);

  const salvar = useMutation({
    mutationFn: () => {
      const payload = {
        professor_id: professorId,
        disciplina_id: disciplinaId || null,
        dia_semana: dia,
        hora_inicio: inicio,
        hora_fim: fim,
      };
      return editando
        ? scheduleApi.update(editando.id, payload)
        : scheduleApi.create({ turma_id: turmaId, ...payload });
    },
    onSuccess: () => {
      toast("success", editando ? "Aula atualizada" : "Aula adicionada à grade");
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
      onSaved();
      onClose();
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao salvar a aula");
    },
  });

  return (
    <Modal
      open={open}
      title={editando ? "Editar aula" : "Nova aula na grade"}
      onClose={onClose}
      size="md"
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          salvar.mutate();
        }}
      >
        <Select
          label="Professor"
          required
          value={professorId}
          onChange={(e) => {
            setProfessorId(e.target.value);
            setDisciplinaId("");
          }}
          options={opcoesProfessor}
          placeholder="Selecione o professor"
        />

        {alocacoesDesteProfessor.length > 0 && (
          <Select
            label="Disciplina (opcional)"
            value={disciplinaId}
            onChange={(e) => setDisciplinaId(e.target.value)}
            options={alocacoesDesteProfessor.map((a) => ({
              value: a.disciplina_id,
              label: disciplinaNome.get(a.disciplina_id) ?? a.disciplina_id.slice(0, 8),
            }))}
            placeholder="Sem disciplina definida"
          />
        )}

        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            Dia da semana
          </label>
          <div className="flex flex-wrap gap-1.5">
            {DIAS_SEMANA_ORDEM.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDia(d)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  dia === d
                    ? "bg-primary-500 text-white"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                {DIAS_SEMANA_LABEL[d]}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              Início
            </label>
            <input
              type="time"
              required
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              Término
            </label>
            <input
              type="time"
              required
              value={fim}
              onChange={(e) => setFim(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={salvar.isPending} disabled={!professorId}>
            {editando ? "Salvar" : "Adicionar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function GradeHorariaPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [turmaId, setTurmaId] = useState("");
  const [formAberto, setFormAberto] = useState(false);
  const [editando, setEditando] = useState<HorarioAula | null>(null);
  const podeEscrever = user?.perfil === "admin" || user?.perfil === "secretaria";

  const abrirNovo = () => {
    setEditando(null);
    setFormAberto(true);
  };
  const abrirEdicao = (a: HorarioAula) => {
    setEditando(a);
    setFormAberto(true);
  };

  const { data: turmas } = useQuery({
    queryKey: ["classes", { only_active: true }],
    queryFn: () => classesApi.list({ only_active: true, size: 100 }),
  });

  const turmaSelecionada = useMemo(
    () => (turmas?.items ?? []).find((t) => t.id === turmaId) ?? null,
    [turmas, turmaId],
  );

  const { data: aulas, isLoading, isError } = useQuery({
    queryKey: ["schedule", { turmaId }],
    queryFn: () => scheduleApi.grid(turmaId),
    enabled: !!turmaId,
  });

  const porDia = useMemo(() => {
    const mapa: Record<string, HorarioAula[]> = {};
    for (const d of DIAS_SEMANA_ORDEM) mapa[d] = [];
    for (const a of aulas ?? []) {
      (mapa[a.dia_semana] ??= []).push(a);
    }
    for (const d of Object.keys(mapa)) {
      mapa[d].sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
    }
    return mapa;
  }, [aulas]);

  const totalAulas = aulas?.length ?? 0;
  const diasComAula = Object.values(porDia).filter((l) => l.length > 0).length;

  const desativar = useMutation({
    mutationFn: (id: string) => scheduleApi.desativar(id),
    onSuccess: () => {
      toast("success", "Aula desativada");
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
    },
    onError: (err: any) =>
      toast("error", err?.response?.data?.message || "Erro ao desativar"),
  });

  const reativar = useMutation({
    mutationFn: (id: string) => scheduleApi.reativar(id),
    onSuccess: () => {
      toast("success", "Aula reativada");
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
    },
    onError: (err: any) =>
      toast("error", err?.response?.data?.message || "Erro ao reativar"),
  });

  return (
    <div>
      <Breadcrumb items={[{ label: "Grade Horária" }]} />
      <PageHeader
        title="Grade Horária"
        description={
          turmaId && turmaSelecionada
            ? `${turmaSelecionada.codigo} · ${TURNO_LABEL[turmaSelecionada.turno] ?? turmaSelecionada.turno} · ${totalAulas} aula(s) em ${diasComAula} dia(s)`
            : "Defina quando cada turma tem aula e com quem"
        }
        showNew={podeEscrever && !!turmaId}
        onNew={abrirNovo}
        newLabel="Nova aula"
      >
        <select
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={turmaId}
          onChange={(e) => setTurmaId(e.target.value)}
          aria-label="Selecionar turma"
        >
          <option value="">Selecione uma turma...</option>
          {(turmas?.items ?? []).map((t) => (
            <option key={t.id} value={t.id}>
              {t.codigo} {t.nome ? `· ${t.nome}` : ""}
            </option>
          ))}
        </select>
      </PageHeader>

      {!turmaId ? (
        <Card>
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <CalendarClock className="h-10 w-10 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
            <p className="text-lg">Escolha uma turma para ver a grade</p>
            <p className="text-sm mt-1">
              A grade é usada para avisar automaticamente os professores quando um
              responsável informa uma falta.
            </p>
          </div>
        </Card>
      ) : isError ? (
        <Card>
          <ErrorState
            title="Erro ao carregar a grade"
            message="Não foi possível carregar a grade horária desta turma."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["schedule"] })}
          />
        </Card>
      ) : isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
      ) : totalAulas === 0 ? (
        <Card>
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <CalendarClock className="h-10 w-10 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
            <p className="text-lg">Nenhuma aula cadastrada nesta turma</p>
            <p className="text-sm mt-1 max-w-md mx-auto">
              Sem grade, o aviso de ausência não sabe quem avisar. Adicione ao menos uma
              aula por dia letivo.
            </p>
            {podeEscrever && (
              <Button className="mt-4" onClick={abrirNovo}>
                <Plus className="h-4 w-4 mr-2" /> Cadastrar primeira aula
              </Button>
            )}
          </div>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-4">
            {DIAS_SEMANA_ORDEM.map((d) => (
              <Card key={d} className="p-3">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                  {DIAS_SEMANA_LABEL[d]}
                </p>
                {(porDia[d] ?? []).length === 0 ? (
                  <p className="text-xs text-gray-400 italic">sem aula</p>
                ) : (
                  <div className="space-y-1.5">
                    {(porDia[d] ?? []).map((a) => (
                      <div
                        key={a.id}
                        className="text-xs rounded-lg border border-gray-200 dark:border-gray-700 p-2"
                      >
                        <p className="font-semibold text-gray-800 dark:text-gray-200">
                          {hhmm(a.hora_inicio)}–{hhmm(a.hora_fim)}
                        </p>
                        <p className="text-gray-500 dark:text-gray-400 truncate">
                          {a.professor_nome ?? "—"}
                        </p>
                        {a.disciplina_nome && (
                          <p className="text-gray-400 truncate">{a.disciplina_nome}</p>
                        )}
                        {podeEscrever && (
                          <div className="flex gap-1 mt-1.5">
                            <button
                              onClick={() => abrirEdicao(a)}
                              className="text-gray-400 hover:text-primary-500"
                              title="Editar"
                            >
                              <Pencil className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => desativar.mutate(a.id)}
                              className="text-gray-400 hover:text-danger-500"
                              title="Desativar"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>

          {aulas?.some((a) => !a.ativo) && (
            <Card className="p-3 mb-4 flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-300">
                Há aulas desativadas nesta turma.
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  reativar.mutate(
                    aulas.find((a) => !a.ativo)!.id,
                  )
                }
                loading={reativar.isPending}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Reativar
              </Button>
            </Card>
          )}

          <p className="text-xs text-gray-400 flex items-start gap-1.5">
            <Info className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
            Só entram professores com alocação ativa nesta turma. No fundamental 1, o
            costume é ter um ou dois por turma — é o que a regra de conflito de horário
            pressupõe.
          </p>
        </>
      )}

      {formAberto && turmaId && (
        <AulaForm
          open={formAberto}
          onClose={() => {
            setFormAberto(false);
            setEditando(null);
          }}
          turmaId={turmaId}
          editando={editando}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ["schedule"] })}
        />
      )}
    </div>
  );
}
