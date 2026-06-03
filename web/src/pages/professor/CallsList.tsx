import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { attendanceApi, allocationsApi, classesApi, subjectsApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { DataTable } from "../../components/ui/DataTable";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { Badge } from "../../components/ui/Badge";
import { Plus, ClipboardList, Calendar } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";
import type { ChamadaResponse } from "../../api/endpoints";

export function CallsList() {
  const { alocacaoId } = useParams<{ alocacaoId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;

  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const { data: allocation } = useQuery({
    queryKey: ["allocation", alocacaoId],
    queryFn: () => allocationsApi.getById(alocacaoId!),
    enabled: !!alocacaoId,
  });

  const { data: callsData, isLoading, isError } = useQuery({
    queryKey: ["calls", alocacaoId, page],
    queryFn: () => attendanceApi.listCalls(alocacaoId!, page, 20),
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
            title="Erro ao carregar chamadas"
            message="Não foi possível carregar as chamadas desta turma."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["calls", alocacaoId] })}
          />
        </Card>
      </div>
    );
  }

  const turmaInfo = turma ? `${turma.codigo} — ${serie?.nome ?? "?"} (${anoLetivo?.ano ?? "?"})` : "Carregando...";

  return (
    <div>
      <Breadcrumb items={[
        { label: "Minhas Turmas", path: `${prefix}/minhas-turmas` },
        { label: turma?.codigo ?? "Chamadas" },
      ]} />

      <PageHeader
        title={`Chamadas — ${turma?.codigo ?? "..."}`}
        description={disciplina ? `${disciplina.nome} • ${turmaInfo}` : turmaInfo}
      >
        <Button onClick={() => navigate(`${prefix}/turma/${alocacaoId}/chamada/nova`)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Chamada
        </Button>
      </PageHeader>

      <div className="hidden md:block">
        <DataTable
          columns={[
            {
              key: "data_hora_aula",
              header: "Data / Hora",
              render: (item: ChamadaResponse) => (
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <span>{new Date(item.data_hora_aula).toLocaleString("pt-BR")}</span>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: () => <Badge variant="success">Realizada</Badge>,
            },
            {
              key: "acoes",
              header: "Frequência",
              render: (item: ChamadaResponse) => (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`${prefix}/chamada/${item.id}`);
                  }}
                >
                  <ClipboardList className="h-4 w-4 mr-1" />
                  Registrar
                </Button>
              ),
            },
          ]}
          data={callsData?.items ?? []}
          keyExtractor={(item) => item.id}
          loading={isLoading}
          emptyMessage="Nenhuma chamada registrada para esta turma"
        />
      </div>
      <div className="md:hidden space-y-3">
        {(callsData?.items ?? []).length === 0 ? (
          <Card><div className="text-center py-8 text-sm text-gray-400">Nenhuma chamada registrada para esta turma</div></Card>
        ) : (
          (callsData?.items ?? []).map((item) => (
            <Card key={item.id}>
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Calendar className="h-4 w-4 text-primary-500 flex-shrink-0" />
                    <span className="text-sm text-gray-900 dark:text-gray-100">{new Date(item.data_hora_aula).toLocaleString("pt-BR")}</span>
                  </div>
                  <Badge variant="success">Realizada</Badge>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate(`${prefix}/chamada/${item.id}`)}
                >
                  <ClipboardList className="h-4 w-4 mr-1" />
                  Registrar
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>

      {callsData && callsData.pages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="text-center sm:text-left">Página {callsData.page} de {callsData.pages} ({callsData.total} registros)</span>
          <div className="flex gap-2 justify-center sm:justify-end">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <Button variant="ghost" size="sm" disabled={page >= callsData.pages} onClick={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
