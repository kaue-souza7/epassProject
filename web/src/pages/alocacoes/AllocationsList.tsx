import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { allocationsApi, teachersApi, classesApi, subjectsApi, seriesApi, academicYearsApi, type AllocationResponse } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { DataTable } from "../../components/ui/DataTable";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorState } from "../../components/ui/ErrorState";
import type { PaginatedResponse } from "../../types/api";

export function AllocationsList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;
  const canWrite = user?.perfil === "admin";

  const [filterProfessorId, setFilterProfessorId] = useState<string | undefined>();
  const [filterTurmaId, setFilterTurmaId] = useState<string | undefined>();
  const [filterDisciplinaId, setFilterDisciplinaId] = useState<string | undefined>();
  const [onlyActive, setOnlyActive] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["allocations", { professor_id: filterProfessorId, turma_id: filterTurmaId, only_active: onlyActive, page }],
    queryFn: () => allocationsApi.list({
      professor_id: filterProfessorId,
      turma_id: filterTurmaId,
      only_active: onlyActive,
      page,
      size: 20,
    }),
  });

  const pagination = data as PaginatedResponse<AllocationResponse> | undefined;
  const allocations = pagination?.items;
  const totalPages = pagination?.pages ?? 0;
  const currentPage = pagination?.page ?? 1;
  const total = pagination?.total ?? 0;

  const { data: teachersData } = useQuery({
    queryKey: ["teachers", "all"],
    queryFn: () => teachersApi.list({ size: 100, only_active: true }),
  });

  const { data: classes } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list(),
  });

  const { data: subjects } = useQuery({
    queryKey: ["subjects"],
    queryFn: () => subjectsApi.list(),
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
  });

  const professores = teachersData?.items ?? [];
  const professorMap = new Map(professores.map((p) => [p.usuario_id, p]));
  const turmaMap = new Map((classes?.items ?? []).map((t) => [t.id, t]));
  const disciplinaMap = new Map(subjects?.map((d) => [d.id, d]) ?? []);
  const serieMap = new Map(series?.map((s) => [s.id, s]) ?? []);
  const anoMap = new Map(anosLetivos?.map((a) => [a.id, a]) ?? []);

  const professorOptions = professores.map((p) => ({
    value: p.usuario_id,
    label: (p as any).nome || p.usuario_id.slice(0, 8),
  }));

  const turmaOptions = (classes?.items ?? []).map((t) => {
    const serie = serieMap.get(t.serie_id);
    return {
      value: t.id,
      label: `${t.codigo} — ${serie?.nome ?? "?"} (${anoMap.get(t.ano_letivo_id)?.ano ?? "?"})`,
    };
  });

  const disciplinaOptions = (subjects ?? []).map((d) => ({
    value: d.id,
    label: `${d.codigo} — ${d.nome}`,
  }));

  const filtered = (allocations ?? []).filter((a) => {
    if (filterDisciplinaId && a.disciplina_id !== filterDisciplinaId) return false;
    return true;
  });

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Alocações" }]} />
        <PageHeader title="Alocações" description="Gerencie as alocações de professores" />
        <Card>
          <ErrorState
            title="Erro ao carregar alocações"
            message="Não foi possível carregar a lista de alocações. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["allocations"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Alocações" }]} />
      <PageHeader
        title="Alocações"
        description={`${total} alocação${total !== 1 ? "ões" : ""}`}
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/alocacoes/novo`)}
        newLabel="Nova Alocação"
      >
        <select
          aria-label="Filtrar por professor"
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={filterProfessorId ?? ""}
          onChange={(e) => { setFilterProfessorId(e.target.value || undefined); setPage(1); }}
        >
          <option value="">Todos os professores</option>
          {professorOptions.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>

        <select
          aria-label="Filtrar por turma"
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={filterTurmaId ?? ""}
          onChange={(e) => { setFilterTurmaId(e.target.value || undefined); setPage(1); }}
        >
          <option value="">Todas as turmas</option>
          {turmaOptions.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        <select
          aria-label="Filtrar por disciplina"
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={filterDisciplinaId ?? ""}
          onChange={(e) => { setFilterDisciplinaId(e.target.value || undefined); setPage(1); }}
        >
          <option value="">Todas as disciplinas</option>
          {disciplinaOptions.map((d) => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer whitespace-nowrap">
          <input
            type="checkbox"
            checked={onlyActive}
            onChange={(e) => { setOnlyActive(e.target.checked); setPage(1); }}
            className="rounded border-gray-300 dark:border-gray-600 text-primary-500 focus:ring-primary-500"
          />
          Apenas ativas
        </label>
      </PageHeader>

      <DataTable
        columns={[
          {
            key: "professor",
            header: "Professor",
            render: (item: AllocationResponse) => {
              const prof = professorMap.get(item.professor_id);
              return (prof as any)?.nome || prof?.usuario_id.slice(0, 8) || "—";
            },
          },
          {
            key: "disciplina",
            header: "Disciplina",
            render: (item: AllocationResponse) => {
              const disc = disciplinaMap.get(item.disciplina_id);
              return disc?.nome ?? "—";
            },
          },
          {
            key: "turma",
            header: "Turma",
            render: (item: AllocationResponse) => {
              const turma = turmaMap.get(item.turma_id);
              return turma?.codigo ?? "—";
            },
          },
          {
            key: "serie",
            header: "Série",
            render: (item: AllocationResponse) => {
              const turma = turmaMap.get(item.turma_id);
              return turma ? serieMap.get(turma.serie_id)?.nome ?? "—" : "—";
            },
          },
          {
            key: "ano_letivo",
            header: "Ano Letivo",
            render: (item: AllocationResponse) => {
              const turma = turmaMap.get(item.turma_id);
              return turma ? String(anoMap.get(turma.ano_letivo_id)?.ano ?? "") : "—";
            },
          },
          {
            key: "data_inicio",
            header: "Data Início",
            render: (item: AllocationResponse) =>
              new Date(item.data_inicio).toLocaleDateString("pt-BR"),
          },
          {
            key: "data_fim",
            header: "Data Fim",
            render: (item: AllocationResponse) =>
              item.data_fim ? new Date(item.data_fim).toLocaleDateString("pt-BR") : "—",
          },
          {
            key: "status",
            header: "Status",
            render: (item: AllocationResponse) => (
              <Badge variant={item.data_fim ? "default" : "success"}>
                {item.data_fim ? "Encerrada" : "Ativa"}
              </Badge>
            ),
          },
        ]}
        data={filtered}
        keyExtractor={(item) => item.id}
        loading={isLoading}
        emptyMessage="Nenhuma alocação encontrada"
        onRowClick={(item) => navigate(`${prefix}/alocacoes/${item.id}`)}
      />

      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="text-center sm:text-left">Página {currentPage} de {totalPages} ({total} registros)</span>
          <div className="flex gap-2 justify-center sm:justify-end">
            <Button variant="ghost" size="sm" disabled={currentPage <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <Button variant="ghost" size="sm" disabled={currentPage >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
