import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle } from "lucide-react";

const WRITE_ROLES = ["admin"];

const schema = z.object({
  ano: z
    .string()
    .min(1, "Ano é obrigatório")
    .regex(/^\d{4}$/, "Ano deve ter 4 dígitos"),
  data_inicio: z.string().min(1, "Data de início é obrigatória"),
  data_fim: z.string().min(1, "Data de fim é obrigatória"),
});

type FormData = z.infer<typeof schema>;

export function AnosLetivosForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const isEditing = !!id;

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: item, isLoading: isLoadingItem, isError } = useQuery({
    queryKey: ["academic-years", id],
    queryFn: () => academicYearsApi.getById(id!),
    enabled: isEditing,
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
        ano: String(item.ano),
        data_inicio: item.data_inicio,
        data_fim: item.data_fim,
      });
    }
  }, [item, reset]);

  const createMutation = useMutation({
    mutationFn: academicYearsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic-years"] });
      toast("success", "Ano letivo criado com sucesso");
      navigate(`${prefix}/anos-letivos`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar ano letivo");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { ano: number; data_inicio: string; data_fim: string }) =>
      academicYearsApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic-years"] });
      toast("success", "Ano letivo atualizado com sucesso");
      navigate(`${prefix}/anos-letivos`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar ano letivo");
    },
  });

  const onSubmit = async (data: FormData) => {
    const payload = {
      ano: parseInt(data.ano, 10),
      data_inicio: data.data_inicio,
      data_fim: data.data_fim,
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
        <Breadcrumb items={[{ label: "Anos Letivos", path: `${prefix}/anos-letivos` }, { label: isEditing ? "Editar" : "Novo" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar ano letivo. Tente novamente.</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <Breadcrumb items={[{ label: "Anos Letivos", path: `${prefix}/anos-letivos` }, { label: isEditing ? "Editar" : "Novo" }]} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isEditing ? "Editar Ano Letivo" : "Novo Ano Letivo"}
      </h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Ano"
            type="number"
            disabled={!canWrite}
            error={errors.ano?.message}
            {...register("ano")}
          />

          <Input
            label="Data Início"
            type="date"
            disabled={!canWrite}
            error={errors.data_inicio?.message}
            {...register("data_inicio")}
          />

          <Input
            label="Data Fim"
            type="date"
            disabled={!canWrite}
            error={errors.data_fim?.message}
            {...register("data_fim")}
          />

          {canWrite && (
            <div className="flex items-center gap-3 pt-4">
              <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                {isEditing ? "Salvar" : "Criar"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate(`${prefix}/anos-letivos`)}
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
