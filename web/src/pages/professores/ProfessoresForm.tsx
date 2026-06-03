import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { teachersApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle } from "lucide-react";

const WRITE_ROLES = ["admin", "secretaria"];

const schema = z.object({
  usuario_id: z.string().min(1, "Usuário é obrigatório"),
  matricula_funcional: z.string().optional(),
  formacao_principal: z.string().optional(),
  data_contratacao: z.string().optional(),
  observacoes: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function ProfessoresForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const isEditing = !!id;

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: item, isLoading: isLoadingItem, isError } = useQuery({
    queryKey: ["teachers", id],
    queryFn: () => teachersApi.getById(id!),
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
        usuario_id: item.usuario_id,
        matricula_funcional: item.matricula_funcional ?? "",
        formacao_principal: item.formacao_principal ?? "",
        data_contratacao: item.data_contratacao ?? "",
        observacoes: item.observacoes ?? "",
      });
    }
  }, [item, reset]);

  const createMutation = useMutation({
    mutationFn: teachersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teachers"] });
      toast("success", "Professor criado com sucesso");
      navigate(`${prefix}/professores`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar professor");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: {
      matricula_funcional?: string | null;
      formacao_principal?: string | null;
      data_contratacao?: string | null;
      observacoes?: string | null;
    }) => teachersApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teachers"] });
      toast("success", "Professor atualizado com sucesso");
      navigate(`${prefix}/professores`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar professor");
    },
  });

  const onSubmit = async (data: FormData) => {
    const payload = {
      usuario_id: data.usuario_id,
      matricula_funcional: data.matricula_funcional || null,
      formacao_principal: data.formacao_principal || null,
      data_contratacao: data.data_contratacao || null,
      observacoes: data.observacoes || null,
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
        <Breadcrumb items={[{ label: "Professores", path: `${prefix}/professores` }, { label: isEditing ? "Editar" : "Novo" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar professor. Tente novamente.</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <Breadcrumb items={[{ label: "Professores", path: `${prefix}/professores` }, { label: isEditing ? "Editar" : "Novo" }]} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isEditing ? "Editar Professor" : "Novo Professor"}
      </h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="ID do Usuário"
            disabled={isEditing || !canWrite}
            error={errors.usuario_id?.message}
            {...register("usuario_id")}
          />

          <Input
            label="Matrícula Funcional"
            disabled={!canWrite}
            error={errors.matricula_funcional?.message}
            {...register("matricula_funcional")}
          />

          <Input
            label="Formação Principal"
            disabled={!canWrite}
            error={errors.formacao_principal?.message}
            {...register("formacao_principal")}
          />

          <Input
            label="Data de Contratação"
            type="date"
            disabled={!canWrite}
            error={errors.data_contratacao?.message}
            {...register("data_contratacao")}
          />

          <Input
            label="Observações"
            disabled={!canWrite}
            error={errors.observacoes?.message}
            {...register("observacoes")}
          />

          {canWrite && (
            <div className="flex items-center gap-3 pt-4">
              <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                {isEditing ? "Salvar" : "Criar"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate(`${prefix}/professores`)}
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
