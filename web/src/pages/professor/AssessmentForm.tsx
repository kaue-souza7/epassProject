import { useParams, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { assessmentsApi, type TipoAvaliacao } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle, AlertTriangle } from "lucide-react";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

const assessmentSchema = z.object({
  titulo: z.string().min(1, "Título é obrigatório"),
  tipo: z.string().min(1, "Tipo é obrigatório"),
  peso: z.string().min(1, "Peso é obrigatório").refine((v) => parseInt(v, 10) > 0, "Peso deve ser maior que zero"),
  nota_maxima: z.string().min(1, "Nota máxima é obrigatória").refine((v) => parseFloat(v) > 0, "Nota máxima deve ser maior que zero"),
  bimestre: z.string().min(1, "Bimestre é obrigatório"),
  data_aplicacao: z.string().min(1, "Data de aplicação é obrigatória"),
  observacoes: z.string().optional(),
});

type AssessmentFormData = z.infer<typeof assessmentSchema>;

const tipoOptions: { value: TipoAvaliacao; label: string }[] = [
  { value: "prova", label: "Prova" },
  { value: "trabalho", label: "Trabalho" },
  { value: "atividade", label: "Atividade" },
  { value: "recuperacao", label: "Recuperação" },
  { value: "simulado", label: "Simulado" },
  { value: "outro", label: "Outro" },
];

const bimestreOptions = [
  { value: "1", label: "1º Bimestre" },
  { value: "2", label: "2º Bimestre" },
  { value: "3", label: "3º Bimestre" },
  { value: "4", label: "4º Bimestre" },
];

export function AssessmentForm() {
  const { alocacaoId } = useParams<{ alocacaoId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();
  const prefix = `/${user?.perfil}`;

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<AssessmentFormData>({
    resolver: zodResolver(assessmentSchema),
    defaultValues: {
      titulo: "",
      tipo: "prova",
      peso: "1",
      nota_maxima: "10",
      bimestre: "1",
      data_aplicacao: "",
      observacoes: "",
    },
  });

  const selectedTipo = watch("tipo");
  const isRecuperacao = selectedTipo === "recuperacao";

  const createMutation = useMutation({
    mutationFn: (data: AssessmentFormData) => assessmentsApi.create({
      alocacao_id: alocacaoId!,
      titulo: data.titulo,
      tipo: data.tipo as TipoAvaliacao,
      peso: parseInt(data.peso, 10),
      nota_maxima: parseFloat(data.nota_maxima),
      bimestre: parseInt(data.bimestre, 10),
      data_aplicacao: new Date(data.data_aplicacao).toISOString(),
      observacoes: data.observacoes || null,
    }),
    onSuccess: () => {
      toast("success", "Avaliação criada com sucesso");
      navigate(`${prefix}/turma/${alocacaoId}/avaliacoes`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar avaliação");
    },
  });

  const onSubmit = (data: AssessmentFormData) => createMutation.mutate(data);

  return (
    <div className="max-w-xl mx-auto">
      <Breadcrumb items={[
        { label: "Minhas Turmas", path: `${prefix}/minhas-turmas` },
        { label: "Avaliações", path: `${prefix}/turma/${alocacaoId}/avaliacoes` },
        { label: "Nova Avaliação" },
      ]} />

      <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Nova Avaliação</h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="space-y-5">
            <Input
              label="Título"
              placeholder="Ex: Prova Bimestral de Matemática"
              error={errors.titulo?.message}
              {...register("titulo")}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="Tipo"
                options={tipoOptions}
                error={errors.tipo?.message}
                {...register("tipo")}
              />

              <Select
                label="Bimestre"
                options={bimestreOptions}
                error={errors.bimestre?.message}
                {...register("bimestre")}
              />
            </div>

            {isRecuperacao && (
              <div className="flex items-center gap-2 p-3 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-warning-500 flex-shrink-0" />
                <span className="text-sm text-warning-600 dark:text-warning-400">
                  Esta avaliação é de recuperação e pode alterar a situação final do aluno.
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Peso"
                type="number"
                min="1"
                error={errors.peso?.message}
                {...register("peso")}
              />

              <Input
                label="Nota Máxima"
                type="number"
                step="0.01"
                min="0.01"
                error={errors.nota_maxima?.message}
                {...register("nota_maxima")}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Data de Aplicação
              </label>
              <input
                type="date"
                className={`w-full px-3 py-2.5 text-sm bg-transparent border rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-0 dark:text-gray-100 ${
                  errors.data_aplicacao
                    ? "border-danger-500 focus:ring-danger-500"
                    : "border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500"
                }`}
                {...register("data_aplicacao")}
              />
              {errors.data_aplicacao && (
                <p className="text-xs text-danger-500">{errors.data_aplicacao.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Observações <span className="text-gray-400">(opcional)</span>
              </label>
              <textarea
                className="w-full px-3 py-2.5 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 resize-none"
                rows={3}
                placeholder="Informações adicionais..."
                {...register("observacoes")}
              />
            </div>

            {createMutation.isError && (
              <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                <AlertCircle className="h-5 w-5 text-danger-500" />
                <span className="text-sm text-danger-600 dark:text-danger-400">
                  {(createMutation.error as any)?.response?.data?.message || "Erro ao criar avaliação"}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
            <Button variant="ghost" onClick={() => navigate(`${prefix}/turma/${alocacaoId}/avaliacoes`)}>
              Cancelar
            </Button>
            <Button type="submit" loading={isSubmitting || createMutation.isPending}>
              Criar Avaliação
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
