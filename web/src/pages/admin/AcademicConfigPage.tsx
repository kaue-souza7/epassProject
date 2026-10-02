import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { academicYearsApi, academicConfigApi, boletimLiberacaoApi, systemConfigApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { AlertCircle, AlertTriangle, Settings, Calendar, Mail, CheckCircle, XCircle } from "lucide-react";

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

const smtpSchema = z.object({
  smtp_host: z.string().min(1, "Servidor SMTP é obrigatório"),
  smtp_port: z.string().min(1, "Porta é obrigatória").refine((v) => {
    const n = parseInt(v, 10);
    return n >= 1 && n <= 65535;
  }, "Porta inválida"),
  smtp_user: z.string().min(1, "Usuário é obrigatório"),
  // Vazia = manter a senha já salva (ela nunca volta da API).
  smtp_password: z.string(),
  smtp_from: z.string().min(1, "Remetente é obrigatório").email("E-mail inválido"),
  smtp_crypto: z.enum(["starttls", "ssl", "none"]),
});

type SmtpFormData = z.infer<typeof smtpSchema>;

// A API expõe dois booleanos; o formulário expõe a escolha que o admin
// reconhece. TLS implícito ganha quando os dois vierem ligados.
function cryptoDoConfig(cfg: { smtp_use_ssl?: boolean | null; smtp_use_tls?: boolean | null }): SmtpFormData["smtp_crypto"] {
  if (cfg.smtp_use_ssl) return "ssl";
  return cfg.smtp_use_tls === false ? "none" : "starttls";
}

function SmtpConfigSection() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [testEmail, setTestEmail] = useState("");
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const {
    register: registerSmtp,
    handleSubmit: handleSubmitSmtp,
    reset: resetSmtp,
    formState: { errors: smtpErrors },
  } = useForm<SmtpFormData>({
    resolver: zodResolver(smtpSchema),
    defaultValues: {
      smtp_host: "",
      smtp_port: "587",
      smtp_user: "",
      smtp_password: "",
      smtp_from: "",
      smtp_crypto: "starttls",
    },
  });

  const { data: smtpConfig, isLoading: loadingSmtp } = useQuery({
    queryKey: ["smtp-config"],
    queryFn: () => systemConfigApi.getSmtp(),
  });

  useEffect(() => {
    if (smtpConfig) {
      resetSmtp({
        smtp_host: smtpConfig.smtp_host || "",
        smtp_port: String(smtpConfig.smtp_port || 587),
        smtp_user: smtpConfig.smtp_user || "",
        smtp_password: "",
        smtp_from: smtpConfig.smtp_from || "",
        smtp_crypto: cryptoDoConfig(smtpConfig),
      });
    }
  }, [smtpConfig, resetSmtp]);

  const saveMutation = useMutation({
    mutationFn: (data: SmtpFormData) =>
      systemConfigApi.saveSmtp({
        smtp_host: data.smtp_host,
        smtp_port: parseInt(data.smtp_port, 10),
        smtp_user: data.smtp_user,
        smtp_password: data.smtp_password || undefined,
        smtp_from: data.smtp_from,
        smtp_use_tls: data.smtp_crypto === "starttls",
        smtp_use_ssl: data.smtp_crypto === "ssl",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["smtp-config"] });
      toast("success", "Configuração SMTP salva com sucesso");
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao salvar configuração SMTP");
    },
  });

  const testMutation = useMutation({
    mutationFn: () => systemConfigApi.testSmtp(testEmail),
    onSuccess: (data) => {
      setTestResult(data);
      if (data.success) {
        toast("success", data.message);
      } else {
        toast("error", data.message);
      }
    },
    onError: (err: any) => {
      setTestResult({ success: false, message: err?.response?.data?.message || "Erro ao testar SMTP" });
      toast("error", "Erro ao testar envio de e-mail");
    },
  });

  const onSaveSmtp = (data: SmtpFormData) => {
    // Sem senha no formulário e sem senha salva, o save deixaria o SMTP
    // inutilizável — e o `configured` continuaria marcado como ativo.
    if (!data.smtp_password && !smtpConfig?.configured) {
      toast("error", "Informe a senha SMTP para concluir a configuração");
      return;
    }
    saveMutation.mutate(data);
  };

  return (
    <Card className="mt-6">
      <div className="flex items-center gap-2 mb-4">
        <Mail className="h-5 w-5 text-primary-500" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Configuração de E-mail (SMTP)
        </h2>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Configure o servidor de e-mail para envio automático de notificações de prazo de boletim.
      </p>

      {smtpConfig?.configured && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
          <CheckCircle className="h-4 w-4 text-success-500 flex-shrink-0" />
          <span className="text-sm text-success-600 dark:text-success-400">
            SMTP configurado e ativo
          </span>
        </div>
      )}

      {loadingSmtp ? (
        <Spinner />
      ) : (
        <form onSubmit={handleSubmitSmtp(onSaveSmtp)} noValidate>
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Servidor SMTP"
                placeholder="smtp.gmail.com"
                error={smtpErrors.smtp_host?.message}
                {...registerSmtp("smtp_host")}
              />
              <Input
                label="Porta"
                type="number"
                placeholder="587"
                error={smtpErrors.smtp_port?.message}
                {...registerSmtp("smtp_port")}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Usuário / E-mail"
                placeholder="seu-email@gmail.com"
                error={smtpErrors.smtp_user?.message}
                {...registerSmtp("smtp_user")}
              />
              <Input
                label="Senha (preencha para alterar)"
                type="password"
                placeholder={smtpConfig?.configured ? "••••••••" : "Senha de aplicativo SMTP"}
                error={smtpErrors.smtp_password?.message}
                {...registerSmtp("smtp_password")}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Remetente (e-mail)"
                placeholder="noreply@epass.edu.br"
                error={smtpErrors.smtp_from?.message}
                {...registerSmtp("smtp_from")}
              />
              <Select
                label="Criptografia"
                options={[
                  { value: "starttls", label: "TLS/STARTTLS — porta 587 (recomendado)" },
                  { value: "ssl", label: "SSL/TLS implícito — porta 465" },
                  { value: "none", label: "Sem criptografia" },
                ]}
                error={smtpErrors.smtp_crypto?.message}
                {...registerSmtp("smtp_crypto")}
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              A criptografia precisa bater com a porta: 465 só aceita TLS implícito e
              587 só aceita STARTTLS. No Gmail e no Outlook use uma{" "}
              <span className="font-medium">senha de aplicativo</span> (a senha da conta
              é recusada), gerada com a verificação em 2 etapas ativa e colada sem espaços.
            </p>
          </div>

          <div className="flex items-center justify-end pt-4 border-t border-gray-200 dark:border-gray-700 mt-4">
            <Button type="submit" loading={saveMutation.isPending}>
              Salvar Configuração SMTP
            </Button>
          </div>
        </form>
      )}

      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          Testar Envio de E-mail
        </h3>
        <div className="flex items-end gap-3">
          <Input
            label="E-mail de destino"
            placeholder="destinatario@exemplo.com"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
          />
          <Button
            onClick={() => testMutation.mutate()}
            disabled={!testEmail || testMutation.isPending}
            variant="secondary"
          >
            Enviar Teste
          </Button>
        </div>
        {testResult && (
          <div className={`flex items-center gap-2 mt-3 p-3 rounded-lg ${
            testResult.success
              ? "bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800"
              : "bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800"
          }`}>
            {testResult.success ? (
              <CheckCircle className="h-4 w-4 text-success-500 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-danger-500 flex-shrink-0" />
            )}
            <span className={`text-sm ${testResult.success ? "text-success-600 dark:text-success-400" : "text-danger-600 dark:text-danger-400"}`}>
              {testResult.message}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

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

  const [novoPrazoBimestre, setNovoPrazoBimestre] = useState(1);
  const [novoPrazoData, setNovoPrazoData] = useState("");
  const [novoPrazoHora, setNovoPrazoHora] = useState("23:59");

  const { data: prazos, isLoading: loadingPrazos } = useQuery({
    queryKey: ["prazos-liberacao", selectedAnoLetivo],
    queryFn: () => boletimLiberacaoApi.listarPrazos(selectedAnoLetivo),
    enabled: !!selectedAnoLetivo,
  });

  const criarPrazoMutation = useMutation({
    mutationFn: () => boletimLiberacaoApi.criarPrazo({
      ano_letivo_id: selectedAnoLetivo,
      bimestre: novoPrazoBimestre,
      data_limite: novoPrazoData,
      hora_limite: `${novoPrazoHora}:00`,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prazos-liberacao", selectedAnoLetivo] });
      setNovoPrazoData("");
      setNovoPrazoHora("23:59");
      toast("success", "Prazo de liberação criado com sucesso");
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar prazo");
    },
  });

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

      {selectedAnoLetivo && !loading && (
        <Card className="mt-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-5 w-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Prazos de Liberação de Boletim
            </h2>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Configure as datas e horários limite para liberação de boletim por bimestre (horário em UTC).
          </p>

          {loadingPrazos ? (
            <Spinner />
          ) : (
            <>
              {prazos && prazos.length > 0 && (
                <div className="space-y-2 mb-4">
                  {prazos.map((prazo) => (
                    <div key={prazo.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {prazo.bimestre}º Bimestre
                        </span>
                        <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                          — Prazo: {new Date(prazo.data_limite).toLocaleDateString("pt-BR")} às {prazo.hora_limite ? prazo.hora_limite.substring(0, 5) : "23:59"}
                        </span>
                        {prazo.notificado_em && (
                          <span className="text-xs text-warning-600 dark:text-warning-400 ml-2">
                            (Notificado)
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex items-end gap-3 p-3 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
                <Select
                  label="Bimestre"
                  options={[
                    { value: "1", label: "1º" },
                    { value: "2", label: "2º" },
                    { value: "3", label: "3º" },
                    { value: "4", label: "4º" },
                  ]}
                  value={String(novoPrazoBimestre)}
                  onChange={(e) => setNovoPrazoBimestre(Number(e.target.value))}
                />
                <Input
                  label="Data Limite"
                  type="date"
                  value={novoPrazoData}
                  onChange={(e) => setNovoPrazoData(e.target.value)}
                />
                <Input
                  label="Hora Limite (UTC)"
                  type="time"
                  value={novoPrazoHora}
                  onChange={(e) => setNovoPrazoHora(e.target.value)}
                />
                <Button
                  onClick={() => criarPrazoMutation.mutate()}
                  disabled={!novoPrazoData || criarPrazoMutation.isPending}
                >
                  Adicionar Prazo
                </Button>
              </div>
            </>
          )}
        </Card>
      )}

      <SmtpConfigSection />
    </div>
  );
}
