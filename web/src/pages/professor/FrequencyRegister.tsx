import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { attendanceApi, allocationsApi, classesApi, subjectsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { Save, UserCheck, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";
import type { StatusFrequencia, FrequenciaRegistrar } from "../../api/endpoints";

type StudentStatus = Record<string, StatusFrequencia>;

const statusOptions: { value: StatusFrequencia; label: string; color: string; icon: typeof CheckCircle2 }[] = [
  { value: "presente", label: "Presente", color: "text-success-600 bg-success-50 dark:bg-success-900/20 border-success-200", icon: CheckCircle2 },
  { value: "falta", label: "Falta", color: "text-danger-600 bg-danger-50 dark:bg-danger-900/20 border-danger-200", icon: XCircle },
  { value: "falta_justificada", label: "Falta Justificada", color: "text-warning-600 bg-warning-50 dark:bg-warning-900/20 border-warning-200", icon: AlertCircle },
];

export function FrequencyRegister() {
  const { callId } = useParams<{ callId: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const prefix = `/${user?.perfil}`;

  const [studentStatus, setStudentStatus] = useState<StudentStatus>({});
  const [dirty, setDirty] = useState(false);

  const { data: call, isLoading, isError } = useQuery({
    queryKey: ["call", callId],
    queryFn: () => attendanceApi.getCall(callId!),
    enabled: !!callId,
  });

  const { data: allocation } = useQuery({
    queryKey: ["allocation", call?.alocacao_id],
    queryFn: () => allocationsApi.getById(call!.alocacao_id),
    enabled: !!call?.alocacao_id,
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
    if (call?.frequencias) {
      const initial: StudentStatus = {};
      for (const f of call.frequencias) {
        initial[f.matricula_id] = f.status;
      }
      setStudentStatus(initial);
    }
  }, [call]);

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!callId) throw new Error("ID da chamada não informado");
      const frequencias: FrequenciaRegistrar[] = Object.entries(studentStatus).map(
        ([matricula_id, status]) => ({ matricula_id, status }),
      );
      return attendanceApi.registerFrequencies(callId, frequencias);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["call", callId] });
      queryClient.invalidateQueries({ queryKey: ["calls"] });
      toast("success", "Frequências registradas com sucesso");
      setDirty(false);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao registrar frequências");
    },
  });

  const setStatus = (matriculaId: string, status: StatusFrequencia) => {
    setStudentStatus((prev) => ({ ...prev, [matriculaId]: status }));
    setDirty(true);
  };

  const hasChanges = dirty && Object.keys(studentStatus).length > 0;

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas", path: `${prefix}/minhas-turmas` }, { label: "Carregando..." }]} />
        <div className="flex justify-center py-12"><Spinner /></div>
      </div>
    );
  }

  if (isError || !call) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas", path: `${prefix}/minhas-turmas` }, { label: "Erro" }]} />
        <Card>
          <ErrorState
            title="Chamada não encontrada"
            message="A chamada que você está procurando não existe ou foi removida."
          />
        </Card>
      </div>
    );
  }

  const presentes = call.frequencias.filter((f) => f.status === "presente").length;
  const faltas = call.frequencias.filter((f) => f.status === "falta" || f.status === "falta_justificada").length;
  const total = call.frequencias.length;

  return (
    <div>
      <Breadcrumb items={[
        { label: "Minhas Turmas", path: `${prefix}/minhas-turmas` },
        { label: "Chamadas", path: `${prefix}/turma/${call.alocacao_id}/chamadas` },
        { label: "Registrar Frequência" },
      ]} />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">Registro de Frequência</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">
            {turma?.codigo ?? "..."} — {disciplina?.nome ?? "..."}
            <span className="mx-2">•</span>
            {new Date(call.data_hora_aula).toLocaleString("pt-BR")}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 self-stretch sm:self-auto">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-sm">
              <span className="text-success-600 font-medium">{presentes}</span>
              <span className="text-gray-400">/</span>
              <span className="text-gray-600 dark:text-gray-400">{total}</span>
              <span className="text-gray-400 ml-1">presentes</span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              <span className="text-danger-600 font-medium">{faltas}</span>
              <span className="text-gray-400">/</span>
              <span className="text-gray-600 dark:text-gray-400">{total}</span>
              <span className="text-gray-400 ml-1">faltas</span>
            </div>
          </div>

          {hasChanges && (
            <Button
              onClick={() => saveMutation.mutate()}
              loading={saveMutation.isPending}
              size="sm"
              className="w-full sm:w-auto"
            >
              <Save className="h-4 w-4 mr-2" />
              Salvar
            </Button>
          )}
        </div>
      </div>

      <Card>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {call.frequencias.map((freq) => {
            const currentStatus = studentStatus[freq.matricula_id] || freq.status;
            const isChanged = currentStatus !== freq.status;

            return (
              <div key={freq.id} className={`py-3 px-1 ${isChanged ? "bg-primary-50/50 dark:bg-primary-900/10 -mx-1 px-3 rounded" : ""}`}>
                <div className="flex items-center gap-3 mb-2 sm:mb-0">
                  <UserCheck className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {freq.aluno_nome ?? "Aluno"}
                    </p>
                    {freq.matricula_codigo && (
                      <p className="text-xs text-gray-400">{freq.matricula_codigo}</p>
                    )}
                  </div>
                  {isChanged && (
                    <span className="text-xs text-primary-500 font-medium flex-shrink-0">Alterado</span>
                  )}
                </div>

                <div className="flex items-center gap-2 sm:ml-8">
                  <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 w-full sm:w-auto">
                    {statusOptions.map((opt) => {
                      const Icon = opt.icon;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          aria-pressed={currentStatus === opt.value}
                          aria-label={`${freq.aluno_nome ?? "Aluno"}: ${opt.label}`}
                          className={`inline-flex items-center gap-1.5 flex-1 sm:flex-none px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                            currentStatus === opt.value
                              ? opt.color + " border"
                              : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                          }`}
                          onClick={() => setStatus(freq.matricula_id, opt.value)}
                        >
                          <Icon className="h-4 w-4" aria-hidden="true" />
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {call.frequencias.length === 0 && (
          <div className="text-center py-8 text-sm text-gray-400">
            Nenhum aluno matriculado nesta turma.
          </div>
        )}
      </Card>
    </div>
  );
}
