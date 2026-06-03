import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { studentsApi, type HistoricoItem } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Spinner } from "../../components/ui/Spinner";
import { AlertCircle, ArrowLeft, Calendar, School, GraduationCap } from "lucide-react";

const situacaoBadge: Record<string, "success" | "danger" | "info" | "warning"> = {
  APROVADO: "success",
  APROVADO_POS_RECUPERACAO: "success",
  REPROVADO: "danger",
  REPROVADO_POS_RECUPERACAO: "danger",
  REPROVADO_FREQUENCIA: "danger",
  CURSANDO: "info",
};

const situacaoLabel: Record<string, string> = {
  APROVADO: "Aprovado",
  APROVADO_POS_RECUPERACAO: "Aprovado pós-recuperação",
  REPROVADO: "Reprovado",
  REPROVADO_POS_RECUPERACAO: "Reprovado pós-recuperação",
  REPROVADO_FREQUENCIA: "Reprovado por frequência",
  CURSANDO: "Cursando",
};

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

function HistoryItemCard({ item, index }: { item: HistoricoItem; index: number }) {
  return (
    <div className="relative flex gap-6 pb-8 last:pb-0">
      <div className="flex flex-col items-center">
        <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 text-sm font-bold z-10
          ${item.status === "cancelada"
            ? "border-gray-300 bg-gray-100 text-gray-400 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-500"
            : "border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"}`}>
          {item.ano_letivo.toString().slice(-2)}
        </div>
        {index > 0 && (
          <div className="w-0.5 flex-1 bg-gray-200 dark:bg-gray-700 -mt-2" />
        )}
      </div>
      <div className="flex-1 min-w-0 pt-1">
        <Card className="p-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {item.ano_letivo}
                </span>
                <span className="text-xs text-gray-500">—</span>
                <GraduationCap className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300">{item.serie_nome}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <School className="h-4 w-4" />
                <span>Turma {item.turma_codigo}</span>
              </div>
              <div className="text-xs text-gray-400 mt-1">
                Matrícula em {new Date(item.data_matricula).toLocaleDateString("pt-BR")}
                {item.data_saida && ` — Saída em ${new Date(item.data_saida).toLocaleDateString("pt-BR")}`}
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Badge variant={statusBadge[item.status] || "default"}>{statusLabel[item.status] || item.status}</Badge>
            </div>
          </div>
          {item.situacao_final && (
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Situação:</span>
                <Badge variant={situacaoBadge[item.situacao_final] || "info"}>
                  {situacaoLabel[item.situacao_final] || item.situacao_final}
                </Badge>
              </div>
              {item.media_final !== null && (
                <div className="flex items-center gap-1">
                  <span className="text-gray-500">Média:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{item.media_final.toFixed(1)}</span>
                </div>
              )}
              {item.frequencia_final !== null && (
                <div className="flex items-center gap-1">
                  <span className="text-gray-500">Frequência:</span>
                  <span className={`font-medium ${item.frequencia_final < 75 ? "text-danger-600" : "text-gray-900 dark:text-gray-100"}`}>
                    {item.frequencia_final.toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

export function StudentHistory() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["student-history", id],
    queryFn: () => studentsApi.getHistory(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="max-w-3xl mx-auto">
        <Breadcrumb items={[{ label: "Alunos", path: `${prefix}/alunos` }, { label: "Histórico Escolar" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar histórico escolar.</p>
          </div>
        </Card>
      </div>
    );
  }

  const sortedHistory = [...data.historico].sort((a, b) => b.ano_letivo - a.ano_letivo);

  return (
    <div className="max-w-3xl mx-auto">
      <Breadcrumb
        items={[
          { label: "Alunos", path: `${prefix}/alunos` },
          { label: data.aluno_nome, path: `${prefix}/alunos/${id}` },
          { label: "Histórico Escolar" },
        ]}
      />

      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate(`${prefix}/alunos/${id}`)}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-gray-500" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Histórico Escolar</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{data.aluno_nome}</p>
        </div>
      </div>

      {sortedHistory.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <GraduationCap className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Nenhum registro encontrado.</p>
          </div>
        </Card>
      ) : (
        <div className="pl-2">
          {sortedHistory.map((item, index) => (
            <HistoryItemCard key={item.matricula_id} item={item} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
