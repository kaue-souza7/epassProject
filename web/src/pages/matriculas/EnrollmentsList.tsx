import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import { enrollmentsApi, studentsApi, classesApi, seriesApi, academicYearsApi, type EnrollmentsListResponse } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { DataTable } from "../../components/ui/DataTable";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorState } from "../../components/ui/ErrorState";
import { BranchedMenu } from "../../components/ui/BranchedMenu";

const statusOptions = [
  { value: "", label: "Todos os status" },
  { value: "ativa", label: "Ativa" },
  { value: "concluida", label: "Concluída" },
  { value: "cancelada", label: "Cancelada" },
];

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

export function EnrollmentsList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;
  const canWrite = user?.perfil && ["admin", "secretaria"].includes(user.perfil);

  const [page, setPage] = useState(1);
  const [filterAlunoId, setFilterAlunoId] = useState<string | undefined>();
  const [filterTurmaId, setFilterTurmaId] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [searchAluno, setSearchAluno] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["enrollments", { aluno_id: filterAlunoId, turma_id: filterTurmaId, status: filterStatus || undefined, page }],
    queryFn: () => enrollmentsApi.list({
      aluno_id: filterAlunoId,
      turma_id: filterTurmaId,
      status: filterStatus || undefined,
      page,
      size: 20,
    }),
  });

  const { data: students } = useQuery({
    queryKey: ["students", { nome: searchAluno }],
    queryFn: () => studentsApi.list({ nome: searchAluno || undefined }),
    enabled: searchAluno.length > 0 || !!filterAlunoId,
  });

  const { data: classes } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list(),
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
  });

  const turmaMap = new Map((classes?.items ?? []).map((t) => [t.id, t]));
  const serieMap = new Map(series?.map((s) => [s.id, s]) ?? []);
  const anoMap = new Map(anosLetivos?.map((a) => [a.id, a]) ?? []);

  const studentOptions = (students?.items ?? []).map((s) => ({
    value: s.id,
    label: s.nome,
  }));

  const alunoMenuItems = studentOptions.map((s) => ({
    value: s.value,
    label: s.label,
    icon: UserRound,
  }));

  const turmaOptions = (classes?.items ?? []).map((t) => {
    const serie = serieMap.get(t.serie_id);
    return {
      value: t.id,
      label: `${t.codigo} — ${serie?.nome ?? "?"} (${anoMap.get(t.ano_letivo_id)?.ano ?? "?"})`,
    };
  });

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Matrículas" }]} />
        <PageHeader title="Matrículas" description="Gerencie as matrículas do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar matrículas"
            message="Não foi possível carregar a lista de matrículas. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["enrollments"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Matrículas" }]} />
      <PageHeader
        title="Matrículas"
        description="Gerencie as matrículas do sistema"
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/matriculas/novo`)}
        newLabel="Nova Matrícula"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative min-w-[200px]">
            <input
              aria-label="Buscar aluno"
              className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
              placeholder="Buscar aluno..."
              value={searchAluno}
              onChange={(e) => {
                setSearchAluno(e.target.value);
                setFilterAlunoId(undefined);
                setPage(1);
              }}
            />
            {studentOptions.length > 0 && searchAluno && !filterAlunoId && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card dark:bg-card-dark border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto p-2">
                <BranchedMenu
                  items={alunoMenuItems}
                  label="Alunos encontrados"
                  activeValue={filterAlunoId}
                  onSelect={(value) => {
                    const alvo = studentOptions.find((s) => s.value === value);
                    if (!alvo) return;
                    setFilterAlunoId(alvo.value);
                    setSearchAluno(alvo.label);
                    setPage(1);
                  }}
                  width={260}
                  rowHeight={38}
                  indent={30}
                  branchLeaves
                  className="epass-scrollbar"
                />
              </div>
            )}
          </div>

          <div className="min-w-[180px]">
            <select
              aria-label="Filtrar por turma"
              className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
              value={filterTurmaId ?? ""}
              onChange={(e) => { setFilterTurmaId(e.target.value || undefined); setPage(1); }}
            >
              <option value="">Todas as turmas</option>
              {turmaOptions.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <select
            aria-label="Filtrar por status"
            className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
          >
            {statusOptions.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </PageHeader>

      <DataTable
        columns={[
          { key: "aluno_nome", header: "Aluno" },
          { key: "turma_codigo", header: "Turma" },
          {
            key: "turma_id",
            header: "Série",
            render: (item: EnrollmentsListResponse) => {
              const turma = turmaMap.get(item.turma_id);
              return turma ? serieMap.get(turma.serie_id)?.nome ?? "—" : "—";
            },
          },
          {
            key: "ano_letivo",
            header: "Ano Letivo",
            render: (item: EnrollmentsListResponse) => {
              const turma = turmaMap.get(item.turma_id);
              return turma ? String(anoMap.get(turma.ano_letivo_id)?.ano ?? "") : "—";
            },
          },
          {
            key: "data_matricula",
            header: "Data Matrícula",
            render: (item: EnrollmentsListResponse) =>
              new Date(item.data_matricula).toLocaleDateString("pt-BR"),
          },
          {
            key: "status",
            header: "Status",
            render: (item: EnrollmentsListResponse) => (
              <Badge variant={statusBadge[item.status] ?? "default"}>
                {statusLabel[item.status] ?? item.status}
              </Badge>
            ),
          },
        ]}
        data={data?.items ?? []}
        keyExtractor={(item) => item.id}
        loading={isLoading}
        emptyMessage="Nenhuma matrícula encontrada"
        onRowClick={(item) => navigate(`${prefix}/matriculas/${item.id}`)}
      />

      {data && data.pages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="text-center sm:text-left">Página {data.page} de {data.pages} ({data.total} registros)</span>
          <div className="flex gap-2 justify-center sm:justify-end">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <Button variant="ghost" size="sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
