import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { studentsApi, enrollmentsApi, classesApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Skeleton } from "../../components/ui/Skeleton";
import { School, FileText, ArrowLeft, Calendar, GraduationCap } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";

const statusBadge: Record<string, "success" | "info" | "warning" | "danger"> = {
  ativa: "success",
  transferida: "info",
  concluida: "info",
  cancelada: "danger",
};

const statusLabel: Record<string, string> = {
  ativa: "Ativa",
  transferida: "Transferida",
  concluida: "Concluída",
  cancelada: "Cancelada",
};

export function ChildDetails() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;

  const { data: allChildren } = useQuery({
    queryKey: ["my-children"],
    queryFn: studentsApi.myChildren,
  });
  const child = allChildren?.find((c) => c.id === childId);

  const { data: enrollmentsData, isLoading, isError } = useQuery({
    queryKey: ["enrollments", childId],
    queryFn: () => enrollmentsApi.list(),
  });

  // Catálogo acadêmico é restrito a admin/secretaria; responsável não pode
  // consultar /classes, /series e /academic-years (403). Os nomes de turma já
  // vêm na matrícula (turma_codigo), então as consultas são condicionadas ao perfil.
  const podeVerCatalogo = user?.perfil === "admin" || user?.perfil === "secretaria";

  const { data: classes } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list({ page: 1, size: 100 }),
    enabled: podeVerCatalogo,
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
    enabled: podeVerCatalogo,
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
    enabled: podeVerCatalogo,
  });

  const enrollments = (enrollmentsData?.items || [])
    .filter((e) => e.aluno_id === childId)
    .map((enr) => {
      const turma = (classes?.items ?? []).find((c) => c.id === enr.turma_id);
      const serie = series?.find((s) => s.id === turma?.serie_id);
      const anoLetivo = anosLetivos?.find((a) => a.id === turma?.ano_letivo_id);
      return { ...enr, turma_detail: turma, serie_detail: serie, ano_letivo_detail: anoLetivo };
    });

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[
          { label: "Meus Filhos", path: `${prefix}/meus-filhos` },
          { label: "Carregando..." },
        ]} />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Skeleton className="h-5 w-5 rounded-full" />
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <div className="flex gap-4">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-28" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const queryClient = useQueryClient();

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[
          { label: "Meus Filhos", path: `${prefix}/meus-filhos` },
          { label: "Erro" },
        ]} />
        <Card>
          <ErrorState
            title="Erro ao carregar matrículas"
            message="Não foi possível carregar as matrículas do aluno."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["enrollments", childId] })}
          />
        </Card>
      </div>
    );
  }

  if (enrollments.length === 0) {
    return (
      <div>
        <Breadcrumb items={[
          { label: "Meus Filhos", path: `${prefix}/meus-filhos` },
          { label: child?.nome ?? "Detalhes" },
        ]} />
        <Card>
          <div className="text-center py-12">
            <School className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">
              Nenhuma matrícula encontrada para este aluno.
            </p>
            <button
              className="mt-4 text-sm text-primary-500 hover:text-primary-600"
              onClick={() => navigate(`${prefix}/meus-filhos`)}
            >
              Voltar
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[
        { label: "Meus Filhos", path: `${prefix}/meus-filhos` },
        { label: child?.nome ?? "Detalhes" },
      ]} />

      <div className="flex items-center gap-4 mb-6">
        <button
          className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
          onClick={() => navigate(`${prefix}/meus-filhos`)}
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {child?.nome ?? "Detalhes do Aluno"}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Selecione uma matrícula para ver o boletim
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {enrollments.map((enr) => (
          <Card key={enr.id} className="hover:shadow-md transition-shadow">
            <div
              role="button"
              tabIndex={0}
              className="flex items-center justify-between gap-4 cursor-pointer"
              onClick={() => navigate(`${prefix}/meus-filhos/${childId}/boletim/${enr.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`${prefix}/meus-filhos/${childId}/boletim/${enr.id}`);
                }
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <School className="h-5 w-5 text-primary-500 flex-shrink-0" />
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {enr.turma_codigo}
                  </span>
                  <Badge variant={statusBadge[enr.status] ?? "default"}>
                    {statusLabel[enr.status] ?? enr.status}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-500 dark:text-gray-400">
                  {enr.serie_detail && (
                    <span className="flex items-center gap-1">
                      <GraduationCap className="h-4 w-4" />
                      {enr.serie_detail.nome}
                    </span>
                  )}
                  {enr.ano_letivo_detail && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {enr.ano_letivo_detail.ano}
                    </span>
                  )}
                  <span>
                    Matrícula: {new Date(enr.data_matricula).toLocaleDateString("pt-BR")}
                  </span>
                </div>
              </div>
              <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
