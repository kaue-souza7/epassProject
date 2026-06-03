import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { classesApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle } from "lucide-react";

const WRITE_ROLES = ["admin", "secretaria"];

const schema = z.object({
  codigo: z.string().min(1, "Código é obrigatório"),
  nome: z.string().optional(),
  serie_id: z.string().min(1, "Série é obrigatória"),
  ano_letivo_id: z.string().min(1, "Ano letivo é obrigatório"),
  turno: z.string().min(1, "Turno é obrigatório"),
  vagas_total: z.string().min(1, "Vagas é obrigatório"),
});

type FormData = z.infer<typeof schema>;

const turnoOptions = [
  { value: "manha", label: "Manhã" },
  { value: "tarde", label: "Tarde" },
  { value: "noite", label: "Noite" },
];

export function TurmasForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const isEditing = !!id;

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: item, isLoading: isLoadingItem, isError } = useQuery({
    queryKey: ["classes", id],
    queryFn: () => classesApi.getById(id!),
    enabled: isEditing,
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (item) {
      reset({
        codigo: item.codigo,
        nome: item.nome ?? "",
        serie_id: item.serie_id,
        ano_letivo_id: item.ano_letivo_id,
        turno: item.turno,
        vagas_total: String(item.vagas_total),
      });
    }
  }, [item, reset]);

  const serieOptions = (series ?? []).map((s) => ({
    value: s.id,
    label: `${s.numero}º - ${s.nome}`,
  }));

  const anoOptions = (anosLetivos ?? []).map((a) => ({
    value: a.id,
    label: String(a.ano),
  }));

  const createMutation = useMutation({
    mutationFn: classesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      toast("success", "Turma criada com sucesso");
      navigate(`${prefix}/turmas`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar turma");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: {
      codigo: string;
      nome?: string | null;
      serie_id: string;
      ano_letivo_id: string;
      turno: string;
      vagas_total: number;
    }) => classesApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      toast("success", "Turma atualizada com sucesso");
      navigate(`${prefix}/turmas`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar turma");
    },
  });

  const onSubmit = async (data: FormData) => {
    const payload = {
      codigo: data.codigo,
      nome: data.nome || null,
      serie_id: data.serie_id,
      ano_letivo_id: data.ano_letivo_id,
      turno: data.turno,
      vagas_total: parseInt(data.vagas_total, 10),
    };

    if (isEditing) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  };

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
        <Breadcrumb items={[{ label: "Turmas", path: `${prefix}/turmas` }, { label: isEditing ? "Editar" : "Novo" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar turma. Tente novamente.</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <Breadcrumb items={[{ label: "Turmas", path: `${prefix}/turmas` }, { label: isEditing ? "Editar" : "Novo" }]} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isEditing ? "Editar Turma" : "Nova Turma"}
      </h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Código"
            disabled={!canWrite}
            error={errors.codigo?.message}
            {...register("codigo")}
          />

          <Input
            label="Nome"
            disabled={!canWrite}
            error={errors.nome?.message}
            {...register("nome")}
          />

          <Select
            label="Série"
            disabled={!canWrite}
            options={serieOptions}
            placeholder="Selecione uma série"
            error={errors.serie_id?.message}
            {...register("serie_id")}
          />

          <Select
            label="Ano Letivo"
            disabled={!canWrite}
            options={anoOptions}
            placeholder="Selecione um ano letivo"
            error={errors.ano_letivo_id?.message}
            {...register("ano_letivo_id")}
          />

          <Select
            label="Turno"
            disabled={!canWrite}
            options={turnoOptions}
            placeholder="Selecione o turno"
            error={errors.turno?.message}
            {...register("turno")}
          />

          <Input
            label="Vagas"
            type="number"
            disabled={!canWrite}
            error={errors.vagas_total?.message}
            {...register("vagas_total")}
          />

          {canWrite && (
            <div className="flex items-center gap-3 pt-4">
              <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                {isEditing ? "Salvar" : "Criar"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate(`${prefix}/turmas`)}
              >
                Cancelar
              </Button>
            </div>
          )}
        </form>
      </Card>
    </div>
  );
}
