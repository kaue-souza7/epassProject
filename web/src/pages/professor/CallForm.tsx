import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { attendanceApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Calendar, AlertCircle } from "lucide-react";

const callSchema = z.object({
  data_hora_aula: z.string().min(1, "Data e hora são obrigatórias"),
});

type CallFormData = z.infer<typeof callSchema>;

export function CallForm() {
  const { alocacaoId } = useParams<{ alocacaoId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const prefix = `/${user?.perfil}`;

  const now = new Date();
  const localISO = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CallFormData>({
    resolver: zodResolver(callSchema),
    defaultValues: { data_hora_aula: localISO },
  });

  const createMutation = useMutation({
    mutationFn: (data: CallFormData) => attendanceApi.createCall({
      alocacao_id: alocacaoId!,
      data_hora_aula: new Date(data.data_hora_aula).toISOString(),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calls", alocacaoId] });
      toast("success", "Chamada aberta com sucesso");
      navigate(`${prefix}/turma/${alocacaoId}/chamadas`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao abrir chamada");
    },
  });

  const onSubmit = (data: CallFormData) => createMutation.mutate(data);

  return (
    <div className="max-w-lg mx-auto">
      <Breadcrumb items={[
        { label: "Minhas Turmas", path: `${prefix}/minhas-turmas` },
        { label: "Chamadas", path: `${prefix}/turma/${alocacaoId}/chamadas` },
        { label: "Nova Chamada" },
      ]} />

      <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Nova Chamada</h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <Calendar className="h-4 w-4 text-primary-500" />
                Data e Hora da Aula
              </label>
              <input
                type="datetime-local"
                className={`w-full px-3 py-2.5 text-sm bg-transparent border rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-0 dark:text-gray-100 ${
                  errors.data_hora_aula
                    ? "border-danger-500 focus:ring-danger-500"
                    : "border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500"
                }`}
                {...register("data_hora_aula")}
              />
              {errors.data_hora_aula && (
                <p className="text-xs text-danger-500">{errors.data_hora_aula.message}</p>
              )}
            </div>

            {createMutation.isError && (
              <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                <AlertCircle className="h-5 w-5 text-danger-500" />
                <span className="text-sm text-danger-600 dark:text-danger-400">
                  {(createMutation.error as any)?.response?.data?.message || "Erro ao abrir chamada"}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
            <Button variant="ghost" onClick={() => navigate(`${prefix}/turma/${alocacaoId}/chamadas`)}>
              Cancelar
            </Button>
            <Button type="submit" loading={isSubmitting || createMutation.isPending}>
              Abrir Chamada
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
