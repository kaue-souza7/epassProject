import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { allocationsApi, enrollmentsApi, classesApi, subjectsApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { DataTable } from "../../components/ui/DataTable";
import { Badge } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { School, BookOpen, FileText, Search, Users } from "lucide-react";

export function ProfessorReportCards() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;
  const [selectedTurmaId, setSelectedTurmaId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const { data: allocationsData, isLoading: loadingAllocations } = useQuery({
    queryKey: ["my-allocations", user?.id],
    queryFn: () => allocationsApi.list({ professor_id: user!.id, size: 100, only_active: false }),
    enabled: !!user?.id,
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

  const allocations = allocationsData?.items ?? [];
  const turmaMap = new Map((classes?.items ?? []).map((t) => [t.id, t]));
  const disciplinaMap = new Map(subjects?.map((d) => [d.id, d]) ?? []);
  const serieMap = new Map(series?.map((s) => [s.id, s]) ?? []);
  const anoMap = new Map(anosLetivos?.map((a) => [a.id, a]) ?? []);

  const uniqueTurmas = allocations
    .filter((a) => !a.data_fim)
    .filter((a, i, arr) => arr.findIndex((x) => x.turma_id === a.turma_id) === i);

  const { data: enrollmentsData, isLoading: loadingEnrollments, isError: errorEnrollments } = useQuery({
    queryKey: ["enrollments-by-turma", selectedTurmaId],
    queryFn: () => enrollmentsApi.list({ turma_id: selectedTurmaId!, size: 100 }),
    enabled: !!selectedTurmaId,
  });

  const students = (enrollmentsData?.items ?? [])
    .filter((e) => {
      if (!search) return true;
      return e.aluno_nome.toLowerCase().includes(search.toLowerCase());
    });

  const handleSelectStudent = (enrollmentId: string) => {
    navigate(`${prefix}/boletins/${enrollmentId}`);
  };

  if (loadingAllocations) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Boletins" }]} />
        <PageHeader title="Boletins" description="Carregando turmas..." />
        <div className="flex justify-center py-12"><Spinner /></div>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Boletins" }]} />

      {/* Step 1: Turma Selection */}
      {!selectedTurmaId && (
        <>
          <PageHeader
            title="Boletins"
            description="Selecione uma turma para visualizar os boletins dos alunos"
          />

          <div className="space-y-3">
            {uniqueTurmas.length === 0 ? (
              <Card>
                <EmptyState
                  icon={School}
                  title="Nenhuma turma ativa"
                  description="Você não possui turmas ativas no momento."
                />
              </Card>
            ) : (
              uniqueTurmas.map((aloc) => {
                const turma = turmaMap.get(aloc.turma_id);
                const disc = disciplinaMap.get(aloc.disciplina_id);
                const turmaSerie = turma ? serieMap.get(turma.serie_id) : undefined;
                const turmaAno = turma ? anoMap.get(turma.ano_letivo_id) : undefined;
                return (
                  <div
                    key={aloc.id}
                    role="button"
                    tabIndex={0}
                    className="cursor-pointer"
                    onClick={() => setSelectedTurmaId(aloc.turma_id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        setSelectedTurmaId(aloc.turma_id);
                      }
                    }}
                  >
                    <Card className="hover:shadow-md transition-shadow">
                      <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <School className="h-5 w-5 text-primary-500 flex-shrink-0" />
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {turma?.codigo ?? "—"}
                          </span>
                          <Badge variant="success">Ativa</Badge>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500 dark:text-gray-400">
                          {turmaSerie && <span>{turmaSerie.nome}</span>}
                          <span className="flex items-center gap-1">
                            <BookOpen className="h-3 w-3" />
                            {disc?.nome ?? "—"}
                          </span>
                          <span>Turno: {turma?.turno ?? "—"}</span>
                          {turmaAno && <span>Ano: {turmaAno.ano}</span>}
                        </div>
                      </div>
                      <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    </div>
                  </Card>
                    </div>
                );
              })
            )}
          </div>
        </>
      )}

      {/* Step 2: Student List */}
      {selectedTurmaId && (
        <>
          <PageHeader
            title="Boletins"
            description={`Alunos da turma ${turmaMap.get(selectedTurmaId)?.codigo ?? ""}`}
          >
            <Button variant="outline" onClick={() => { setSelectedTurmaId(null); setSearch(""); }}>
              Voltar para turmas
            </Button>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
                placeholder="Buscar por nome do aluno..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </PageHeader>

          {loadingEnrollments ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : errorEnrollments ? (
            <Card>
              <ErrorState
                title="Erro ao carregar alunos"
                message="Não foi possível carregar os alunos desta turma."
                onRetry={() => {}}
              />
            </Card>
          ) : students.length === 0 ? (
            <Card>
              <EmptyState
                  icon={Users}
                  title="Nenhum aluno encontrado"
                  description={search ? "Nenhum aluno corresponde à busca." : "Nenhum aluno matriculado nesta turma."}
                />
            </Card>
          ) : (
            <DataTable
              columns={[
                {
                  key: "nome",
                  header: "Aluno",
                  render: (item: typeof students[0]) => (
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-gray-400" />
                      <span className="font-medium text-gray-900 dark:text-gray-100">{item.aluno_nome}</span>
                    </div>
                  ),
                },
                {
                  key: "acoes",
                  header: "",
                  render: (item: typeof students[0]) => (
                    <Button size="sm" onClick={() => handleSelectStudent(item.id)}>
                      <FileText className="h-4 w-4 mr-1" />
                      Visualizar Boletim
                    </Button>
                  ),
                },
              ]}
              data={students}
              keyExtractor={(item) => item.id}
              emptyMessage="Nenhum aluno encontrado"
            />
          )}
        </>
      )}
    </div>
  );
}
