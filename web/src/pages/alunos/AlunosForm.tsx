import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { studentsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle, FileText } from "lucide-react";

const WRITE_ROLES = ["admin", "secretaria"];

const schema = z.object({
  nome: z.string().min(1, "Nome é obrigatório"),
  data_nascimento: z.string().min(1, "Data de nascimento é obrigatória"),
  cpf: z.string().optional(),
  rg: z.string().optional(),
  endereco: z.string().optional(),
  telefone: z.string().optional(),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
  data_entrada: z.string().min(1, "Data de entrada é obrigatória"),
});

type FormData = z.infer<typeof schema>;

export function AlunosForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const isEditing = !!id;

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: item, isLoading: isLoadingItem, isError } = useQuery({
    queryKey: ["students", id],
    queryFn: () => studentsApi.getById(id!),
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
        nome: item.nome,
        data_nascimento: item.data_nascimento,
        cpf: item.cpf ?? "",
        rg: item.rg ?? "",
        endereco: item.endereco ?? "",
        telefone: item.telefone ?? "",
        email: item.email ?? "",
        data_entrada: item.data_entrada,
      });
    }
  }, [item, reset]);

  const createMutation = useMutation({
    mutationFn: studentsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] });
      toast("success", "Aluno criado com sucesso");
      navigate(`${prefix}/alunos`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar aluno");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<{
      nome: string;
      data_nascimento: string;
      cpf: string | null;
      rg: string | null;
      endereco: string | null;
      telefone: string | null;
      email: string | null;
      data_entrada: string;
    }>) => studentsApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] });
      toast("success", "Aluno atualizado com sucesso");
      navigate(`${prefix}/alunos`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar aluno");
    },
  });

  const onSubmit = async (data: FormData) => {
    const payload = {
      nome: data.nome,
      data_nascimento: data.data_nascimento,
      cpf: data.cpf || null,
      rg: data.rg || null,
      endereco: data.endereco || null,
      telefone: data.telefone || null,
      email: data.email || null,
      data_entrada: data.data_entrada,
    };

    if (isEditing) {
      updateMutation.mutate(payload as any);
    } else {
      createMutation.mutate(payload as any);
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
        <Breadcrumb items={[{ label: "Alunos", path: `${prefix}/alunos` }, { label: isEditing ? "Editar" : "Novo" }]} />
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Erro ao carregar aluno. Tente novamente.</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Breadcrumb items={[{ label: "Alunos", path: `${prefix}/alunos` }, { label: isEditing ? "Editar" : "Novo" }]} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isEditing ? "Editar Aluno" : "Novo Aluno"}
      </h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Nome"
            disabled={!canWrite}
            error={errors.nome?.message}
            {...register("nome")}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Data de Nascimento"
              type="date"
              disabled={!canWrite}
              error={errors.data_nascimento?.message}
              {...register("data_nascimento")}
            />

            <Input
              label="Data de Entrada"
              type="date"
              disabled={!canWrite}
              error={errors.data_entrada?.message}
              {...register("data_entrada")}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="CPF"
              disabled={!canWrite}
              error={errors.cpf?.message}
              {...register("cpf")}
            />

            <Input
              label="RG"
              disabled={!canWrite}
              error={errors.rg?.message}
              {...register("rg")}
            />
          </div>

          <Input
            label="Endereço"
            disabled={!canWrite}
            error={errors.endereco?.message}
            {...register("endereco")}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Telefone"
              disabled={!canWrite}
              error={errors.telefone?.message}
              {...register("telefone")}
            />

            <Input
              label="Email"
              type="email"
              disabled={!canWrite}
              error={errors.email?.message}
              {...register("email")}
            />
          </div>

          <div className="flex items-center gap-3 pt-4">
            {isEditing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate(`${prefix}/alunos/${id}/historico`)}
              >
                <FileText className="h-4 w-4 mr-2" />
                Histórico Escolar
              </Button>
            )}
            {canWrite && (
              <>
                <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                  {isEditing ? "Salvar" : "Criar"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => navigate(`${prefix}/alunos`)}
                >
                  Cancelar
                </Button>
              </>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
}
