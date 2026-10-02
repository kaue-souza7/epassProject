import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allocationsApi, classesApi, subjectsApi, seriesApi, academicYearsApi, boletimLiberacaoApi, type AllocationResponse } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { DataTable } from "../../components/ui/DataTable";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { AlertCircle, School, ExternalLink, BookOpen, FileText, Search, Award, CheckCircle } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";

export function MyClasses() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const prefix = `/${user?.perfil}`;
  const [manualAlocacaoId, setManualAlocacaoId] = useState("");
  const [search, setSearch] = useState("");
  const [liberarModal, setLiberarModal] = useState<{ turmaId: string; turmaCodigo: string; bimestre: number } | null>(null);

  const { data: allocationsData, isLoading, isError, error } = useQuery({
    queryKey: ["my-allocations", user?.id],
    queryFn: () => allocationsApi.list({ professor_id: user!.id, size: 100, only_active: false }),
    enabled: !!user?.id,
    retry: false,
  });

  const allocations = allocationsData?.items ?? [];

  const { data: classes } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list(),
    enabled: !!allocations,
  });

  const { data: subjects } = useQuery({
    queryKey: ["subjects"],
    queryFn: () => subjectsApi.list(),
    enabled: !!allocations,
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
    enabled: !!allocations,
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
    enabled: !!allocations,
  });

  const liberarMutation = useMutation({
    mutationFn: ({ turmaId, bimestre }: { turmaId: string; bimestre: number }) =>
      boletimLiberacaoApi.liberar(turmaId, bimestre),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["liberacao-status"] });
      setLiberarModal(null);
    },
  });

  const isForbidden = isError && (error as any)?.response?.status === 403;

  const turmaMap = new Map((classes?.items ?? []).map((t) => [t.id, t]));
  const disciplinaMap = new Map(subjects?.map((d) => [d.id, d]) ?? []);
  const serieMap = new Map(series?.map((s) => [s.id, s]) ?? []);
  const anoMap = new Map(anosLetivos?.map((a) => [a.id, a]) ?? []);

  const activeAllocations = (allocations ?? []).filter((a) => !a.data_fim);

  const filteredAllocations = (allocations ?? []).filter((a) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const turma = turmaMap.get(a.turma_id);
    const disc = disciplinaMap.get(a.disciplina_id);
    return (
      (turma?.codigo?.toLowerCase() || "").includes(q) ||
      (disc?.nome?.toLowerCase() || "").includes(q) ||
      (turma ? (serieMap.get(turma.serie_id)?.nome?.toLowerCase() || "") : "").includes(q) ||
      (turma?.turno?.toLowerCase() || "").includes(q)
    );
  });

  const handleNavigateToCalls = (alocacaoId: string) => {
    navigate(`${prefix}/turma/${alocacaoId}/chamadas`);
  };

  const handleNavigateToAssessments = (alocacaoId: string) => {
    navigate(`${prefix}/turma/${alocacaoId}/avaliacoes`);
  };

  const handleNavigateToReportCards = (turmaId: string) => {
    navigate(`${prefix}/turma/${turmaId}/boletins`);
  };

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas" }]} />
        <PageHeader title="Minhas Turmas" description="Carregando turmas..." />
        <div className="flex justify-center py-12"><Spinner /></div>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Minhas Turmas" }]} />

      {isForbidden ? (
        <>
          <PageHeader
            title="Minhas Turmas"
            description="Visualize as turmas em que você leciona"
          />

          <Card>
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 text-warning-500 mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Acesso às turmas não disponível
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                O endpoint de alocações ainda não está disponível para o perfil professor no backend.
                Esta funcionalidade será ativada após a atualização do backend.
              </p>
            </div>
          </Card>

          <div className="mt-6">
            <Card>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                <ExternalLink className="h-4 w-4 text-primary-500" />
                Acesso direto por ID da alocação
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Enquanto o backend não é atualizado, informe o ID da alocação para acessar as chamadas.
              </p>
              <div className="flex gap-2">
                <input
                  className="flex-1 px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
                  placeholder="ID da alocação..."
                  value={manualAlocacaoId}
                  onChange={(e) => setManualAlocacaoId(e.target.value)}
                />
                <Button
                  disabled={!manualAlocacaoId}
                  onClick={() => handleNavigateToCalls(manualAlocacaoId.trim())}
                >
                  Acessar
                </Button>
              </div>
            </Card>
          </div>
        </>
      ) : isError ? (
        <>
          <PageHeader title="Minhas Turmas" description="Visualize as turmas em que você leciona" />
          <Card>
            <ErrorState
              title="Erro ao carregar turmas"
              message="Não foi possível carregar suas turmas. Tente novamente."
              onRetry={() => queryClient.invalidateQueries({ queryKey: ["my-allocations"] })}
            />
          </Card>
        </>
      ) : (
        <>
          <PageHeader
            title="Minhas Turmas"
            description={`${activeAllocations.length} turma${activeAllocations.length !== 1 ? "s" : ""} ativa${activeAllocations.length !== 1 ? "s" : ""}`}
          >
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
                placeholder="Buscar por turma, disciplina..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Badge variant="success">{`${activeAllocations.length} ativas`}</Badge>
              <Badge variant="default">{`${(allocations ?? []).length - activeAllocations.length} encerradas`}</Badge>
            </div>
          </PageHeader>

          <div className="hidden md:block">
            <DataTable
              columns={[
                {
                  key: "turma",
                  header: "Turma",
                  render: (item: AllocationResponse) => {
                    const turma = turmaMap.get(item.turma_id);
                    return (
                      <div className="flex items-center gap-2">
                        <School className="h-4 w-4 text-gray-400" />
                        <span>{turma?.codigo ?? "—"}</span>
                      </div>
                    );
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
                  key: "disciplina",
                  header: "Disciplina",
                  render: (item: AllocationResponse) => {
                    const disc = disciplinaMap.get(item.disciplina_id);
                    return (
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-gray-400" />
                        <span>{disc?.nome ?? "—"}</span>
                      </div>
                    );
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
                  key: "turno",
                  header: "Turno",
                  render: (item: AllocationResponse) => {
                    const turma = turmaMap.get(item.turma_id);
                    return turma?.turno ?? "—";
                  },
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
                {
                  key: "acoes",
                  header: "Ações",
                  render: (item: AllocationResponse) => (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigateToCalls(item.id);
                        }}
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        Chamadas
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigateToAssessments(item.id);
                        }}
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        Avaliações
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigateToReportCards(item.turma_id);
                        }}
                      >
                        <Award className="h-4 w-4 mr-1" />
                        Boletim
                      </Button>
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          const turma = turmaMap.get(item.turma_id);
                          setLiberarModal({
                            turmaId: item.turma_id,
                            turmaCodigo: turma?.codigo ?? item.turma_id,
                            bimestre: 1,
                          });
                        }}
                      >
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Liberar
                      </Button>
                    </div>
                  ),
                },
              ]}
              data={filteredAllocations}
              keyExtractor={(item) => item.id}
              emptyMessage="Nenhuma turma encontrada para este professor"
            />
          </div>
          <div className="md:hidden space-y-3">
            {filteredAllocations.length === 0 ? (
              <Card><div className="text-center py-8 text-sm text-gray-400">Nenhuma turma encontrada para este professor</div></Card>
            ) : (
              filteredAllocations.map((item) => {
                const turma = turmaMap.get(item.turma_id);
                const disc = disciplinaMap.get(item.disciplina_id);
                return (
                  <Card key={item.id}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <School className="h-4 w-4 text-primary-500 flex-shrink-0" />
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{turma?.codigo ?? "—"}</span>
                          <Badge variant={item.data_fim ? "default" : "success"}>
                            {item.data_fim ? "Encerrada" : "Ativa"}
                          </Badge>
                        </div>
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 dark:text-gray-400">
                          {turma && <span>{serieMap.get(turma.serie_id)?.nome ?? "—"}</span>}
                          <span className="flex items-center gap-1"><BookOpen className="h-3 w-3" />{disc?.nome ?? "—"}</span>
                          <span>Ano: {turma ? anoMap.get(turma.ano_letivo_id)?.ano ?? "" : "—"}</span>
                          <span>{turma?.turno ?? "—"}</span>
                        </div>
                      </div>
                      <div className="flex flex-col gap-1.5 flex-shrink-0">
                        <Button size="sm" variant="outline" onClick={() => handleNavigateToCalls(item.id)}>
                          <FileText className="h-3.5 w-3.5 mr-1" />
                          Chamadas
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleNavigateToAssessments(item.id)}>
                          <FileText className="h-3.5 w-3.5 mr-1" />
                          Avaliações
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleNavigateToReportCards(item.turma_id)}>
                          <Award className="h-3.5 w-3.5 mr-1" />
                          Boletim
                        </Button>
                        <Button size="sm" variant="primary" onClick={() => {
                          const turma = turmaMap.get(item.turma_id);
                          setLiberarModal({
                            turmaId: item.turma_id,
                            turmaCodigo: turma?.codigo ?? item.turma_id,
                            bimestre: 1,
                          });
                        }}>
                          <CheckCircle className="h-3.5 w-3.5 mr-1" />
                          Liberar
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })
            )}
          </div>
        </>
      )}

      {liberarModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Liberar Boletim — {liberarModal.turmaCodigo}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Selecione o bimestre para liberar todas as suas disciplinas nesta turma.
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Bimestre
              </label>
              <select
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-transparent dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={liberarModal.bimestre}
                onChange={(e) => setLiberarModal({ ...liberarModal, bimestre: Number(e.target.value) })}
              >
                <option value={1}>1º Bimestre</option>
                <option value={2}>2º Bimestre</option>
                <option value={3}>3º Bimestre</option>
                <option value={4}>4º Bimestre</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setLiberarModal(null)}>
                Cancelar
              </Button>
              <Button
                onClick={() => liberarMutation.mutate({ turmaId: liberarModal.turmaId, bimestre: liberarModal.bimestre })}
                disabled={liberarMutation.isPending}
              >
                {liberarMutation.isPending ? "Liberando..." : "Confirmar Liberação"}
              </Button>
            </div>
            {liberarMutation.isError && (
              <p className="text-sm text-red-500 mt-2">Erro ao liberar boletim. Tente novamente.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
