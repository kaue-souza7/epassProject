import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";
import { agendaApi, classesApi, teachersApi, type EventoDestinatarioCreate } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle } from "lucide-react";

const WRITE_ROLES = ["admin", "secretaria", "professor"];

const schema = z.object({
  titulo: z.string().min(1, "Título é obrigatório"),
  descricao: z.string().optional(),
  local: z.string().optional(),
  data_inicio: z.string().min(1, "Data início é obrigatória"),
  data_fim: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function EventForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const isEditing = !!id;

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;
  const isResponsavel = user?.perfil === "responsavel";

  const [selectedTurmas, setSelectedTurmas] = useState<string[]>([]);
  const [selectedProfessores, setSelectedProfessores] = useState<string[]>([]);

  const { data: detalhe, isLoading: isLoadingItem, isError } = useQuery({
    queryKey: ["agenda", id],
    queryFn: () => agendaApi.getById(id!),
    enabled: isEditing,
  });

  const { data: turmasData } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list({ only_active: true, page: 1, size: 100 }),
    enabled: canWrite,
  });

  const { data: profData } = useQuery({
    queryKey: ["teachers"],
    queryFn: () => teachersApi.list({ only_active: true, page: 1, size: 100 }),
    enabled: canWrite && user?.perfil === "secretaria",
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { data_fim: "" },
  });

  useEffect(() => {
    if (detalhe) {
      const ev = detalhe.evento;
      reset({
        titulo: ev.titulo,
        descricao: ev.descricao ?? "",
        local: ev.local ?? "",
        data_inicio: format(new Date(ev.data_inicio), "yyyy-MM-dd'T'HH:mm"),
        data_fim: ev.data_fim ? format(new Date(ev.data_fim), "yyyy-MM-dd'T'HH:mm") : "",
      });
      const turmas = detalhe.destinatarios
        .filter((d) => d.tipo_destino === "turma")
        .map((d) => d.destino_id);
      const profs = detalhe.destinatarios
        .filter((d) => d.tipo_destino === "professor")
        .map((d) => d.destino_id);
      setSelectedTurmas(turmas);
      setSelectedProfessores(profs);
    }
  }, [detalhe, reset]);

  const turmas = turmasData?.items ?? [];
  const professores = profData?.items ?? [];

  const toggleArray = (arr: string[], val: string) =>
    arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];

  const createMutation = useMutation({
    mutationFn: agendaApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      toast("success", "Evento criado com sucesso");
      navigate(`${prefix}/agenda`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar evento");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof agendaApi.update>[1]) => agendaApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      toast("success", "Evento atualizado com sucesso");
      navigate(`${prefix}/agenda`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar evento");
    },
  });

  const onSubmit = async (data: FormData) => {
    const destinatarios: EventoDestinatarioCreate[] = [
      ...selectedTurmas.map((turma_id) => ({ tipo_destino: "turma" as const, destino_id: turma_id })),
      ...selectedProfessores.map((destino_id) => ({ tipo_destino: "professor" as const, destino_id })),
    ];

    const payload = {
      titulo: data.titulo,
      descricao: data.descricao || null,
      local: data.local || null,
      data_inicio: new Date(data.data_inicio).toISOString(),
      data_fim: data.data_fim ? new Date(data.data_fim).toISOString() : null,
      destinatarios,
    };

    if (isEditing) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  };

  if (isResponsavel) {
    navigate(`${prefix}/agenda`);
    return null;
  }

  if (isEditing && isLoadingItem) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (isEditing && isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Agenda", path: `${prefix}/agenda` }, { label: "Editar" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar evento.</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <Breadcrumb items={[{ label: "Agenda", path: `${prefix}/agenda` }, { label: isEditing ? "Editar Evento" : "Novo Evento" }]} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isEditing ? "Editar Evento" : "Novo Evento"}
      </h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input label="Título" disabled={!canWrite} error={errors.titulo?.message} {...register("titulo")} />
          <Input label="Descrição" disabled={!canWrite} error={errors.descricao?.message} {...register("descricao")} />
          <Input label="Local" disabled={!canWrite} error={errors.local?.message} {...register("local")} />
          <Input label="Data início" type="datetime-local" disabled={!canWrite} error={errors.data_inicio?.message} {...register("data_inicio")} />
          <Input label="Data fim" type="datetime-local" disabled={!canWrite} error={errors.data_fim?.message} {...register("data_fim")} />

          {canWrite && (
            <div className="space-y-3 pt-2 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Destinatários</p>

              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Turmas</p>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {turmas.length === 0 && (
                    <p className="text-xs text-gray-400">Nenhuma turma disponível</p>
                  )}
                  {turmas.map((t) => (
                    <label key={t.id} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedTurmas.includes(t.id)}
                        onChange={() => setSelectedTurmas(toggleArray(selectedTurmas, t.id))}
                        className="rounded border-gray-300 dark:border-gray-600"
                      />
                      {t.codigo} — {t.nome || ""}
                    </label>
                  ))}
                </div>
              </div>

              {user?.perfil === "secretaria" && (
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Professores</p>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {professores.length === 0 && (
                      <p className="text-xs text-gray-400">Nenhum professor disponível</p>
                    )}
                    {professores.map((p) => (
                      <label key={p.usuario_id} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedProfessores.includes(p.usuario_id)}
                          onChange={() => setSelectedProfessores(toggleArray(selectedProfessores, p.usuario_id))}
                          className="rounded border-gray-300 dark:border-gray-600"
                        />
                        {p.nome}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => navigate(`${prefix}/agenda`)}>Cancelar</Button>
            {canWrite && (
              <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                {isEditing ? "Salvar" : "Criar Evento"}
              </Button>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
}
