import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allocationsApi, teachersApi, classesApi, subjectsApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { SkeletonDetail } from "../../components/ui/SkeletonDetail";
import { AlertCircle, ArrowLeft, UserCheck, School, BookOpen, Calendar } from "lucide-react";

export function AllocationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const prefix = `/${user?.perfil}`;
  const canEncerrar = user?.perfil === "admin";

  const [encerrarOpen, setEncerrarOpen] = useState(false);
  const [dataFim, setDataFim] = useState(new Date().toISOString().split("T")[0]);

  const { data: allocation, isLoading, isError } = useQuery({
    queryKey: ["allocation", id],
    queryFn: () => allocationsApi.getById(id!),
    enabled: !!id,
  });

  const { data: professorData } = useQuery({
    queryKey: ["teacher", allocation?.professor_id],
    queryFn: () => teachersApi.getById(allocation!.professor_id),
    enabled: !!allocation?.professor_id,
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

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
    enabled: !!turma,
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
    enabled: !!turma,
  });

  const serie = series?.find((s) => s.id === turma?.serie_id);
  const anoLetivo = anosLetivos?.find((a) => a.id === turma?.ano_letivo_id);

  const encerrarMutation = useMutation({
    mutationFn: () => allocationsApi.encerrar(id!, { data_fim: dataFim }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["allocation", id] });
      queryClient.invalidateQueries({ queryKey: ["allocations"] });
      toast("success", "Alocação encerrada com sucesso");
      setEncerrarOpen(false);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao encerrar alocação");
      setEncerrarOpen(false);
    },
  });

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Alocações", path: `${prefix}/alocacoes` }, { label: "Carregando..." }]} />
        <SkeletonDetail fields={4} />
      </div>
    );
  }

  if (isError || !allocation) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Alocações", path: `${prefix}/alocacoes` }, { label: "Erro" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Alocação não encontrada.</p>
            <Button variant="ghost" className="mt-4" onClick={() => navigate(`${prefix}/alocacoes`)}>
              Voltar para Alocações
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const professorNome = (professorData as any)?.nome || professorData?.usuario_id.slice(0, 8) || "—";

  return (
    <div>
      <Breadcrumb items={[{ label: "Alocações", path: `${prefix}/alocacoes` }, { label: professorNome }]} />

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate(`${prefix}/alocacoes`)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Detalhes da Alocação</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">{professorNome}</p>
          </div>
        </div>

        {canEncerrar && !allocation.data_fim && (
          <Button variant="danger" onClick={() => setEncerrarOpen(true)}>
            Encerrar Alocação
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-primary-500" />
            Professor
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Nome</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">{professorNome}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Formação</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{professorData?.formacao_principal ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Matrícula Funcional</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{professorData?.matricula_funcional ?? "—"}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <School className="h-5 w-5 text-primary-500" />
            Turma
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Código</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">{turma?.codigo ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Série</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{serie?.nome ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Ano Letivo</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{anoLetivo?.ano ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Turno</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{turma?.turno ?? "—"}</dd>
            </div>
          </dl>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary-500" />
            Disciplina
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Código</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">{disciplina?.codigo ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Nome</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{disciplina?.nome ?? "—"}</dd>
            </div>
          </dl>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary-500" />
            Período
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Status</dt>
              <dd>
                <Badge variant={allocation.data_fim ? "default" : "success"}>
                  {allocation.data_fim ? "Encerrada" : "Ativa"}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Data Início</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {new Date(allocation.data_inicio).toLocaleDateString("pt-BR")}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Data Fim</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">
                {allocation.data_fim ? new Date(allocation.data_fim).toLocaleDateString("pt-BR") : "—"}
              </dd>
            </div>
          </dl>
        </Card>
      </div>

      {encerrarOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setEncerrarOpen(false)} />
          <div className="relative bg-card dark:bg-card-dark rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Encerrar Alocação</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Selecione a data de encerramento e confirme a ação.
            </p>

            <div className="mt-4 space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Data de Encerramento
              </label>
              <input
                type="date"
                className="w-full px-3 py-2.5 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
              />
            </div>

            {encerrarMutation.isError && (
              <p className="mt-3 text-sm text-danger-500">
                {(encerrarMutation.error as any)?.response?.data?.message || "Erro ao encerrar alocação"}
              </p>
            )}

            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setEncerrarOpen(false)} disabled={encerrarMutation.isPending}>
                Cancelar
              </Button>
              <Button variant="danger" onClick={() => encerrarMutation.mutate()} loading={encerrarMutation.isPending}>
                Encerrar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
