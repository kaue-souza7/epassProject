import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Calendar, MapPin, Clock, Trash2, Pencil, ArrowLeft, Users } from "lucide-react";
import { agendaApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Badge } from "../../components/ui/Badge";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorState } from "../../components/ui/ErrorState";

const CAN_EDIT = ["admin", "secretaria", "professor"];

export function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [showDelete, setShowDelete] = useState(false);

  const prefix = `/${user?.perfil}`;
  const canEdit = user?.perfil && CAN_EDIT.includes(user.perfil);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["agenda", id],
    queryFn: () => agendaApi.getById(id!),
    enabled: !!id,
  });

  const deleteMutation = useMutation({
    mutationFn: () => agendaApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      toast("success", "Evento excluído com sucesso");
      navigate(`${prefix}/agenda`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao excluir evento");
    },
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
      <div>
        <Breadcrumb items={[{ label: "Agenda", path: `${prefix}/agenda` }, { label: "Detalhes" }]} />
        <Card>
          <ErrorState
            title="Evento não encontrado"
            message="Este evento não existe ou você não tem permissão para visualizá-lo."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["agenda", id] })}
          />
        </Card>
      </div>
    );
  }

  const ev = data.evento;
  const destinos = data.destinatarios;

  const profileBadge: Record<string, string> = {
    admin: "Administrador",
    secretaria: "Secretaria",
    professor: "Professor",
    responsavel: "Responsável",
  };

  return (
    <div className="max-w-2xl mx-auto">
      <Breadcrumb items={[{ label: "Agenda", path: `${prefix}/agenda` }, { label: ev.titulo }]} />

      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => navigate(`${prefix}/agenda`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Voltar
        </Button>
        {canEdit && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate(`${prefix}/agenda/eventos/${id}/editar`)}>
              <Pencil className="h-4 w-4 mr-2" />
              Editar
            </Button>
            <Button variant="danger" onClick={() => setShowDelete(true)}>
              <Trash2 className="h-4 w-4 mr-2" />
              Excluir
            </Button>
          </div>
        )}
      </div>

      <Card>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{ev.titulo}</h1>
            <Badge variant="info">{profileBadge[ev.perfil_criador] || ev.perfil_criador}</Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-primary-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Data início</p>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {format(new Date(ev.data_inicio), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                </p>
              </div>
            </div>
            {ev.data_fim && (
              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-primary-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Data fim</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {format(new Date(ev.data_fim), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                  </p>
                </div>
              </div>
            )}
            <div className="flex items-start gap-3">
              <Clock className="h-5 w-5 text-primary-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Horário</p>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {format(new Date(ev.data_inicio), "HH:mm")}h
                  {ev.data_fim && <> — {format(new Date(ev.data_fim), "HH:mm")}h</>}
                </p>
              </div>
            </div>
            {ev.local && (
              <div className="flex items-start gap-3">
                <MapPin className="h-5 w-5 text-primary-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Local</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{ev.local}</p>
                </div>
              </div>
            )}
          </div>

          {ev.descricao && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Descrição</p>
              <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{ev.descricao}</p>
            </div>
          )}

          {destinos.length > 0 && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                <Users className="h-4 w-4 inline mr-1" />
                Destinatários ({destinos.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {destinos.map((d) => {
                  const label = d.tipo_destino === "turma" ? "Turma" : d.tipo_destino === "professor" ? "Professor" : "Responsável";
                  const idShort = d.destino_id.slice(0, 8);
                  const text = `${label}: ${idShort}...`;
                  return <Badge key={d.id} variant="default">{text}</Badge>;
                })}
              </div>
            </div>
          )}
        </div>
      </Card>

      <ConfirmDialog
        open={showDelete}
        title="Excluir Evento"
        message={`Tem certeza que deseja excluir "${ev.titulo}"?`}
        confirmLabel="Excluir"
        variant="danger"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
        onCancel={() => setShowDelete(false)}
      />
    </div>
  );
}
