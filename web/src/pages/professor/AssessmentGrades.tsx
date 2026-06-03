import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assessmentsApi, allocationsApi, classesApi, subjectsApi, type NotaLancar } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { Badge } from "../../components/ui/Badge";
import { Save, UserCheck, Weight, Target, AlertTriangle } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";

const tipoLabel: Record<string, string> = {
  prova: "Prova", trabalho: "Trabalho", atividade: "Atividade",
  recuperacao: "Recuperação", simulado: "Simulado", outro: "Outro",
};

const tipoColor: Record<string, "default" | "success" | "warning" | "danger" | "info"> = {
  prova: "default",
  trabalho: "info",
  atividade: "success",
  recuperacao: "danger",
  simulado: "warning",
  outro: "default",
};

type StudentGrade = Record<string, string>;

export function AssessmentGrades() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const prefix = `/${user?.perfil}`;

  const [grades, setGrades] = useState<StudentGrade>({});
  const [dirty, setDirty] = useState(false);

  const { data: gradesData, isLoading, isError } = useQuery({
    queryKey: ["assessment-grades", assessmentId],
    queryFn: () => assessmentsApi.getGrades(assessmentId!),
    enabled: !!assessmentId,
  });

  const { data: allocation } = useQuery({
    queryKey: ["allocation", gradesData?.avaliacao.alocacao_id],
    queryFn: () => allocationsApi.getById(gradesData!.avaliacao.alocacao_id),
    enabled: !!gradesData?.avaliacao.alocacao_id,
  });

  const { data: turma } = useQuery({
    queryKey: ["class", allocation?.turma_id],
    queryFn: () => classesApi.getById(allocation!.turma_id),
    enabled: !!allocation?.turma_id,
  });

  const { data: disciplina } = useQuery({
    queryKey: ["subject", allocation?.disciplina_id],
    queryFn: () => subjectsApi.getById(allocation!.disciplina_id),
    enabled: !!allocation?.disciplina_id,
  });

  useEffect(() => {
    if (gradesData?.notas) {
      const initial: StudentGrade = {};
      for (const n of gradesData.notas) {
        initial[n.matricula_id] = String(n.valor);
      }
      setGrades(initial);
    }
  }, [gradesData]);

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!assessmentId) throw new Error("ID da avaliação não informado");
      const notas: NotaLancar[] = Object.entries(grades).map(
        ([matricula_id, valor]) => ({ matricula_id, valor: parseFloat(valor) || 0 }),
      );
      return assessmentsApi.launchGrades(assessmentId, notas);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assessment-grades", assessmentId] });
      toast("success", "Notas lançadas com sucesso");
      setDirty(false);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao lançar notas");
    },
  });

  const setGrade = (matriculaId: string, valor: string) => {
    const numVal = parseFloat(valor);
    const maxNota = gradesData?.avaliacao.nota_maxima ?? 10;
    if (valor !== "" && (isNaN(numVal) || numVal < 0)) return;
    if (numVal > maxNota) return;
    setGrades((prev) => ({ ...prev, [matriculaId]: valor }));
    setDirty(true);
  };

  const hasChanges = dirty && Object.keys(grades).length > 0;

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas", path: `${prefix}/minhas-turmas` }, { label: "Carregando..." }]} />
        <div className="flex justify-center py-12"><Spinner /></div>
      </div>
    );
  }

  if (isError || !gradesData) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas", path: `${prefix}/minhas-turmas` }, { label: "Erro" }]} />
        <Card>
          <ErrorState
            title="Avaliação não encontrada"
            message="A avaliação que você está procurando não existe ou foi removida."
          />
        </Card>
      </div>
    );
  }

  const { avaliacao, notas } = gradesData;
  const notaMaxima = avaliacao.nota_maxima;
  const notaStep = notaMaxima <= 10 ? 0.5 : 0.1;
  const hasExisting = notas.length > 0;

  return (
    <div>
      <Breadcrumb items={[
        { label: "Minhas Turmas", path: `${prefix}/minhas-turmas` },
        { label: "Avaliações", path: `${prefix}/turma/${avaliacao.alocacao_id}/avaliacoes` },
        { label: "Lançar Notas" },
      ]} />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">
            {avaliacao.titulo}
          </h1>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-gray-500 dark:text-gray-400 mt-1">
            <span>{turma?.codigo ?? "..."} — {disciplina?.nome ?? "..."}</span>
            <Badge variant={tipoColor[avaliacao.tipo] ?? "default"}>{tipoLabel[avaliacao.tipo] ?? avaliacao.tipo}</Badge>
            <span>{avaliacao.bimestre}º Bimestre</span>
            <span>{new Date(avaliacao.data_aplicacao).toLocaleDateString("pt-BR")}</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Weight className="h-3 w-3" />
              Peso: {avaliacao.peso}
            </span>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Target className="h-3 w-3" />
              Nota máx.: {notaMaxima}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 self-start sm:self-auto">
          <span className="text-sm text-gray-400 whitespace-nowrap">
            {hasExisting ? `${notas.length} aluno${notas.length !== 1 ? "s" : ""}` : ""}
          </span>
          {hasChanges && (
            <Button
              onClick={() => saveMutation.mutate()}
              loading={saveMutation.isPending}
              size="sm"
            >
              <Save className="h-4 w-4 mr-2" />
              Salvar
            </Button>
          )}
        </div>
      </div>

      {avaliacao.tipo === "recuperacao" && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-warning-500 flex-shrink-0" />
          <span className="text-sm text-warning-600 dark:text-warning-400">
            Esta avaliação é de recuperação e pode alterar a situação final do aluno.
          </span>
        </div>
      )}

      <Card>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {notas.map((nota) => {
            const currentValor = grades[nota.matricula_id] ?? "";
            const originalValor = String(nota.valor);
            const isChanged = currentValor !== originalValor;

            return (
              <div key={nota.id} className={`py-3 px-1 ${isChanged ? "bg-primary-50/50 dark:bg-primary-900/10 -mx-1 px-3 rounded" : ""}`}>
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <UserCheck className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {nota.aluno_nome ?? "Aluno"}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 sm:ml-auto">
                    {isChanged && (
                      <span className="text-xs text-primary-500 font-medium">Alterado</span>
                    )}
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        step={notaStep}
                        min="0"
                        max={notaMaxima}
                        className={`w-24 px-3 py-1.5 text-sm text-right bg-transparent border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 tabular-nums ${
                          isChanged
                            ? "border-primary-400 dark:border-primary-500 bg-primary-50/50 dark:bg-primary-900/20"
                            : "border-gray-300 dark:border-gray-600"
                        }`}
                        value={currentValor}
                        onChange={(e) => setGrade(nota.matricula_id, e.target.value)}
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-400">/ {notaMaxima}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {notas.length === 0 && (
          <div className="text-center py-8 text-sm text-gray-400">
            Nenhum aluno matriculado nesta turma.
          </div>
        )}
      </Card>
    </div>
  );
}
