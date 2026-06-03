import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { assessmentsApi, allocationsApi, classesApi, subjectsApi, seriesApi, academicYearsApi, type AvaliacaoResponse } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { DataTable } from "../../components/ui/DataTable";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { Badge } from "../../components/ui/Badge";
import { Plus, FileText, Calendar, Weight, Layers, Filter } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";

const tipoLabel: Record<string, string> = {
  prova: "Prova",
  trabalho: "Trabalho",
  atividade: "Atividade",
  recuperacao: "Recuperação",
  simulado: "Simulado",
  outro: "Outro",
};

const tipoColor: Record<string, "default" | "success" | "warning" | "danger" | "info"> = {
  prova: "default",
  trabalho: "info",
  atividade: "success",
  recuperacao: "danger",
  simulado: "warning",
  outro: "default",
};

const bimestres = [1, 2, 3, 4];

export function AssessmentsList() {
  const { alocacaoId } = useParams<{ alocacaoId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;

  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [bimestreFilter, setBimestreFilter] = useState<number | "">("");
  const [tipoFilter, setTipoFilter] = useState<"" | "normal" | "recuperacao">("");

  const { data: allocation } = useQuery({
    queryKey: ["allocation", alocacaoId],
    queryFn: () => allocationsApi.getById(alocacaoId!),
    enabled: !!alocacaoId,
  });

  const { data: assessmentsData, isLoading, isError } = useQuery({
    queryKey: ["assessments", alocacaoId, page, bimestreFilter],
    queryFn: () => assessmentsApi.list({
      alocacao_id: alocacaoId!,
      bimestre: bimestreFilter || undefined,
      page,
      size: 20,
    }),
    enabled: !!alocacaoId,
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

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas", path: `${prefix}/minhas-turmas` }, { label: "Carregando..." }]} />
        <div className="flex justify-center py-12"><Spinner /></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Minhas Turmas", path: `${prefix}/minhas-turmas` }, { label: "Erro" }]} />
        <Card>
          <ErrorState
            title="Erro ao carregar avaliações"
            message="Não foi possível carregar as avaliações desta turma."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["assessments", alocacaoId] })}
          />
        </Card>
      </div>
    );
  }

  const turmaInfo = turma ? `${turma.codigo} — ${serie?.nome ?? "?"} (${anoLetivo?.ano ?? "?"})` : "Carregando...";

  const filteredItems = (assessmentsData?.items ?? []).filter((item) => {
    if (tipoFilter === "normal") return item.tipo !== "recuperacao";
    if (tipoFilter === "recuperacao") return item.tipo === "recuperacao";
    return true;
  });

  return (
    <div>
      <Breadcrumb items={[
        { label: "Minhas Turmas", path: `${prefix}/minhas-turmas` },
        { label: turma?.codigo ?? "Avaliações" },
      ]} />

      <PageHeader
        title={`Avaliações — ${turma?.codigo ?? "..."}`}
        description={disciplina ? `${disciplina.nome} • ${turmaInfo}` : turmaInfo}
      >
        <Button onClick={() => navigate(`${prefix}/turma/${alocacaoId}/avaliacao/nova`)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Avaliação
        </Button>
      </PageHeader>

      <div className="flex items-start sm:items-center gap-2 sm:gap-3 mb-2">
        <Layers className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5 sm:mt-0" />
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              bimestreFilter === "" ? "bg-primary-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-800"
            }`}
            onClick={() => { setBimestreFilter(""); setPage(1); }}
          >
            Todos
          </button>
          {bimestres.map((b) => (
            <button
              key={b}
              type="button"
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                bimestreFilter === b ? "bg-primary-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-800"
              }`}
              onClick={() => { setBimestreFilter(b); setPage(1); }}
            >
              {b}º Bim.
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-start sm:items-center gap-2 sm:gap-3 mb-4">
        <Filter className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5 sm:mt-0" />
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              tipoFilter === "" ? "bg-primary-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-800"
            }`}
            onClick={() => { setTipoFilter(""); setPage(1); }}
          >
            Todas
          </button>
          <button
            type="button"
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              tipoFilter === "normal" ? "bg-primary-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-800"
            }`}
            onClick={() => { setTipoFilter("normal"); setPage(1); }}
          >
            Avaliações Normais
          </button>
          <button
            type="button"
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              tipoFilter === "recuperacao" ? "bg-danger-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-800"
            }`}
            onClick={() => { setTipoFilter("recuperacao"); setPage(1); }}
          >
            Recuperações
          </button>
        </div>
      </div>

      <div className="hidden md:block">
        <DataTable
          columns={[
            {
              key: "titulo",
              header: "Título",
              render: (item: AvaliacaoResponse) => (
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-gray-400" />
                  <span className="font-medium">{item.titulo}</span>
                </div>
              ),
            },
            {
              key: "tipo",
              header: "Tipo",
              render: (item: AvaliacaoResponse) => (
                <Badge variant={tipoColor[item.tipo] ?? "default"}>{tipoLabel[item.tipo] ?? item.tipo}</Badge>
              ),
            },
            {
              key: "bimestre",
              header: "Bimestre",
              render: (item: AvaliacaoResponse) => (
                <span className="text-sm">{item.bimestre}º Bim.</span>
              ),
            },
            {
              key: "peso",
              header: "Peso",
              render: (item: AvaliacaoResponse) => (
                <div className="flex items-center gap-1">
                  <Weight className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-sm">{item.peso}</span>
                </div>
              ),
            },
            {
              key: "nota_maxima",
              header: "Nota Máx.",
              render: (item: AvaliacaoResponse) => (
                <span className="text-sm tabular-nums">{item.nota_maxima}</span>
              ),
            },
            {
              key: "data_aplicacao",
              header: "Data",
              render: (item: AvaliacaoResponse) => (
                <div className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-sm">{new Date(item.data_aplicacao).toLocaleDateString("pt-BR")}</span>
                </div>
              ),
            },
            {
              key: "acoes",
              header: "Notas",
              render: (item: AvaliacaoResponse) => (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`${prefix}/avaliacao/${item.id}/notas`);
                  }}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  Lançar Notas
                </Button>
              ),
            },
          ]}
          data={filteredItems}
          keyExtractor={(item) => item.id}
          loading={isLoading}
          emptyMessage="Nenhuma avaliação registrada para esta turma"
        />
      </div>
      <div className="md:hidden space-y-3">
        {filteredItems.length === 0 ? (
          <Card><div className="text-center py-8 text-sm text-gray-400">Nenhuma avaliação registrada para esta turma</div></Card>
        ) : (
          filteredItems.map((item) => (
            <Card key={item.id}>
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="h-4 w-4 text-primary-500 flex-shrink-0" />
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{item.titulo}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                    <Badge variant={tipoColor[item.tipo] ?? "default"}>{tipoLabel[item.tipo] ?? item.tipo}</Badge>
                    <span>{item.bimestre}º Bim.</span>
                    <span className="flex items-center gap-0.5"><Weight className="h-3 w-3" />{item.peso}</span>
                    <span>Máx: {item.nota_maxima}</span>
                    <span className="flex items-center gap-0.5"><Calendar className="h-3 w-3" />{new Date(item.data_aplicacao).toLocaleDateString("pt-BR")}</span>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-shrink-0"
                  onClick={() => navigate(`${prefix}/avaliacao/${item.id}/notas`)}
                >
                  <FileText className="h-3.5 w-3.5 mr-1" />
                  Notas
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>

      {assessmentsData && assessmentsData.pages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="text-center sm:text-left">Página {assessmentsData.page} de {assessmentsData.pages} ({assessmentsData.total} registros)</span>
          <div className="flex gap-2 justify-center sm:justify-end">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <Button variant="ghost" size="sm" disabled={page >= assessmentsData.pages} onClick={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
