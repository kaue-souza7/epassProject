import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { enrollmentsApi, studentsApi, classesApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { SkeletonDetail } from "../../components/ui/SkeletonDetail";
import { AlertCircle, ArrowLeft, UserCheck, School, Calendar } from "lucide-react";

const statusBadge: Record<string, "success" | "info" | "danger"> = {
  ativa: "success",
  concluida: "info",
  cancelada: "danger",
};

const statusLabel: Record<string, string> = {
  ativa: "Ativa",
  concluida: "Concluída",
  cancelada: "Cancelada",
};

export function EnrollmentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;

  const { data: enrollment, isLoading, isError } = useQuery({
    queryKey: ["enrollment", id],
    queryFn: () => enrollmentsApi.getById(id!),
    enabled: !!id,
  });

  const { data: student } = useQuery({
    queryKey: ["student", enrollment?.aluno_id],
    queryFn: () => studentsApi.getById(enrollment!.aluno_id),
    enabled: !!enrollment?.aluno_id,
  });

  const { data: turma } = useQuery({
    queryKey: ["class", enrollment?.turma_id],
    queryFn: () => classesApi.getById(enrollment!.turma_id),
    enabled: !!enrollment?.turma_id,
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

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Matrículas", path: `${prefix}/matriculas` }, { label: "Carregando..." }]} />
        <SkeletonDetail fields={5} />
      </div>
    );
  }

  if (isError || !enrollment) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Matrículas", path: `${prefix}/matriculas` }, { label: "Erro" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Matrícula não encontrada.</p>
            <Button variant="ghost" className="mt-4" onClick={() => navigate(`${prefix}/matriculas`)}>
              Voltar para Matrículas
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Matrículas", path: `${prefix}/matriculas` }, { label: student?.nome ?? "Detalhes" }]} />

      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate(`${prefix}/matriculas`)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Detalhes da Matrícula</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{student?.nome ?? "—"}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-primary-500" />
            Aluno
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Nome</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">{student?.nome ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Data de Nascimento</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">
                {student?.data_nascimento ? new Date(student.data_nascimento).toLocaleDateString("pt-BR") : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">CPF</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{student?.cpf ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Telefone</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{student?.telefone ?? "—"}</dd>
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

        <Card className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary-500" />
            Informações da Matrícula
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Status</dt>
              <dd>
                <Badge variant={statusBadge[enrollment.status] ?? "default"}>
                  {statusLabel[enrollment.status] ?? enrollment.status}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Data da Matrícula</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {new Date(enrollment.data_matricula).toLocaleDateString("pt-BR")}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Data de Saída</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">
                {enrollment.data_saida ? new Date(enrollment.data_saida).toLocaleDateString("pt-BR") : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 dark:text-gray-400">Motivo de Saída</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{enrollment.motivo_saida ?? "—"}</dd>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <dt className="text-xs text-gray-500 dark:text-gray-400">Observações</dt>
              <dd className="text-sm text-gray-700 dark:text-gray-300">{enrollment.observacoes ?? "Nenhuma observação"}</dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}
