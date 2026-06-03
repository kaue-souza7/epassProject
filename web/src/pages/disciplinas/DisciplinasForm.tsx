import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { subjectsApi } from "../../api/endpoints";
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
  codigo: z.string().min(1, "Código é obrigatório"),
  nome: z.string().min(1, "Nome é obrigatório"),
  descricao: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function DisciplinasForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const isEditing = !!id;

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = canWrite ? "/admin" : `/${user?.perfil}`;

  const { data: item, isLoading: isLoadingItem, isError } = useQuery({
    queryKey: ["subjects", id],
    queryFn: () => subjectsApi.getById(id!),
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
        codigo: item.codigo,
        nome: item.nome,
        descricao: item.descricao ?? "",
      });
    }
  }, [item, reset]);

  const createMutation = useMutation({
    mutationFn: subjectsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subjects"] });
      toast("success", "Disciplina criada com sucesso");
      navigate(`${prefix}/disciplinas`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar disciplina");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { codigo: string; nome: string; descricao?: string | null }) =>
      subjectsApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subjects"] });
      toast("success", "Disciplina atualizada com sucesso");
      navigate(`${prefix}/disciplinas`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar disciplina");
    },
  });

  const onSubmit = async (data: FormData) => {
    const payload = {
      codigo: data.codigo,
      nome: data.nome,
      descricao: data.descricao || null,
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
        <Breadcrumb items={[{ label: "Disciplinas", path: `${prefix}/disciplinas` }, { label: isEditing ? "Editar" : "Novo" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar disciplina. Tente novamente.</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <Breadcrumb items={[{ label: "Disciplinas", path: `${prefix}/disciplinas` }, { label: isEditing ? "Editar" : "Novo" }]} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isEditing ? "Editar Disciplina" : "Nova Disciplina"}
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

          <Input
            label="Descrição"
            disabled={!canWrite}
            error={errors.descricao?.message}
            {...register("descricao")}
          />

          {canWrite && (
            <div className="flex items-center gap-3 pt-4">
              <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                {isEditing ? "Salvar" : "Criar"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate(`${prefix}/disciplinas`)}
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
