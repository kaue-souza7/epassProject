import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { academicYearsApi, academicConfigApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle, AlertTriangle, Settings } from "lucide-react";

const schema = z.object({
  media_aprovacao: z.string().min(1, "Média de aprovação é obrigatória")
    .refine((v) => parseFloat(v) > 0, "Deve ser maior que zero"),
  frequencia_minima: z.string().min(1, "Frequência mínima é obrigatória")
    .refine((v) => {
      const n = parseFloat(v);
      return n > 0 && n <= 100;
    }, "Deve estar entre 1 e 100"),
  possui_recuperacao: z.string(),
  media_minima_recuperacao: z.string().optional(),
  quantidade_periodos: z.string().min(1, "Quantidade de períodos é obrigatória")
    .refine((v) => parseInt(v, 10) >= 1, "Deve ser maior ou igual a 1"),
});

type FormData = z.infer<typeof schema>;

export function AcademicConfigPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const prefix = `/${user?.perfil}`;

  const [selectedAnoLetivo, setSelectedAnoLetivo] = useState("");

  const { data: anosLetivos, isLoading: loadingAnos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
  });

  const { data: config, isLoading: loadingConfig, isError: errorConfig } = useQuery({
    queryKey: ["academic-config", selectedAnoLetivo],
    queryFn: () => academicConfigApi.get(selectedAnoLetivo),
    enabled: !!selectedAnoLetivo,
  });

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      media_aprovacao: "6.0",
      frequencia_minima: "75",
      possui_recuperacao: "true",
      media_minima_recuperacao: "4.0",
      quantidade_periodos: "4",
    },
  });

  const possuiRecuperacao = watch("possui_recuperacao");

  useEffect(() => {
    if (config) {
      reset({
        media_aprovacao: String(config.media_aprovacao),
        frequencia_minima: String(config.frequencia_minima),
        possui_recuperacao: String(config.possui_recuperacao),
        media_minima_recuperacao: config.media_minima_recuperacao != null ? String(config.media_minima_recuperacao) : "4.0",
        quantidade_periodos: String(config.quantidade_periodos),
      });
    }
  }, [config, reset]);

  const updateMutation = useMutation({
    mutationFn: (data: FormData) =>
      academicConfigApi.update(selectedAnoLetivo, {
        media_aprovacao: parseFloat(data.media_aprovacao),
        frequencia_minima: parseFloat(data.frequencia_minima),
        possui_recuperacao: data.possui_recuperacao === "true",
        media_minima_recuperacao: data.possui_recuperacao === "true" && data.media_minima_recuperacao
          ? parseFloat(data.media_minima_recuperacao) : null,
        quantidade_periodos: parseInt(data.quantidade_periodos, 10),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic-config", selectedAnoLetivo] });
      toast("success", "Configuração acadêmica salva com sucesso");
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao salvar configuração");
    },
  });

  const onSubmit = (data: FormData) => updateMutation.mutate(data);

  const anoLetivoOptions = (anosLetivos ?? []).map((a) => ({
    value: a.id,
    label: `${a.ano}${a.ativo ? "" : " (inativo)"}`,
  }));

  const loading = loadingAnos || (selectedAnoLetivo && loadingConfig);

  return (
    <div className="max-w-2xl mx-auto">
      <Breadcrumb items={[
        { label: "Dashboard", path: `${prefix}/dashboard` },
        { label: "Configurações Acadêmicas" },
      ]} />

      <div className="flex items-center gap-3 mb-6">
        <Settings className="h-6 w-6 text-primary-500" />
        <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100">
          Configurações Acadêmicas
        </h1>
      </div>

      <Card className="mb-6">
        <div className="max-w-xs">
          <Select
            label="Ano Letivo"
            options={anoLetivoOptions}
            placeholder="Selecione um ano letivo"
            value={selectedAnoLetivo}
            onChange={(e) => setSelectedAnoLetivo(e.target.value)}
          />
        </div>
      </Card>

      {!selectedAnoLetivo && (
        <Card>
          <div className="flex items-center gap-2 p-4 text-sm text-gray-500 dark:text-gray-400">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            Selecione um ano letivo para visualizar ou editar as configurações acadêmicas.
          </div>
        </Card>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {errorConfig && (
        <Card>
          <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
            <AlertCircle className="h-5 w-5 text-danger-500 flex-shrink-0" />
            <span className="text-sm text-danger-600 dark:text-danger-400">
              Erro ao carregar configuração.
            </span>
          </div>
        </Card>
      )}

      {selectedAnoLetivo && config && !loading && (
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <Card>
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Média para Aprovação"
                  type="number"
                  step="0.1"
                  min="0.1"
                  placeholder="Ex: 6.0"
                  error={errors.media_aprovacao?.message}
                  {...register("media_aprovacao")}
                />
                <Input
                  label="Frequência Mínima (%)"
                  type="number"
                  step="0.1"
                  min="1"
                  max="100"
                  placeholder="Ex: 75"
                  error={errors.frequencia_minima?.message}
                  {...register("frequencia_minima")}
                />
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500"
                    value="true"
                    checked={possuiRecuperacao === "true"}
                    onChange={(e) => {
                      const syntheticEvent = {
                        target: { value: e.target.checked ? "true" : "false", name: "possui_recuperacao" },
                      } as React.ChangeEvent<HTMLInputElement>;
                      (register("possui_recuperacao").onChange as (e: React.ChangeEvent<HTMLInputElement>) => void)(syntheticEvent);
                    }}
                  />
                  <div>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Possui Recuperação
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Ativar sistema de recuperação para este ano letivo
                    </p>
                  </div>
                </label>

                {possuiRecuperacao === "true" && (
                  <div className="ml-6 p-3 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="h-4 w-4 text-warning-500 flex-shrink-0" />
                      <span className="text-xs text-warning-600 dark:text-warning-400">
                        Alunos com média abaixo da aprovação e acima da mínima poderão fazer recuperação.
                      </span>
                    </div>
                    <Input
                      label="Média Mínima para Recuperação"
                      type="number"
                      step="0.1"
                      min="0"
                      placeholder="Ex: 4.0"
                      error={errors.media_minima_recuperacao?.message}
                      {...register("media_minima_recuperacao")}
                    />
                  </div>
                )}
              </div>

              <Select
                label="Quantidade de Períodos"
                options={[
                  { value: "2", label: "2 (Semestres)" },
                  { value: "3", label: "3 (Trimestres)" },
                  { value: "4", label: "4 (Bimestres)" },
                  { value: "6", label: "6 (Bimestres)" },
                ]}
                error={errors.quantidade_periodos?.message}
                {...register("quantidade_periodos")}
              />

              {updateMutation.isError && (
                <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-danger-500" />
                  <span className="text-sm text-danger-600 dark:text-danger-400">
                    {(updateMutation.error as any)?.response?.data?.message || "Erro ao salvar configuração"}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
              <Button type="submit" loading={isSubmitting || updateMutation.isPending}>
                Salvar Configuração
              </Button>
            </div>
          </Card>
        </form>
      )}
    </div>
  );
}
