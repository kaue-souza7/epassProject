import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Settings, Save, Clock, CalendarDays } from "lucide-react";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { cantinaConfigApi } from "../../api/endpoints";

const DIAS_SEMANA = [
  { value: "seg", label: "Seg" },
  { value: "ter", label: "Ter" },
  { value: "qua", label: "Qua" },
  { value: "qui", label: "Qui" },
  { value: "sex", label: "Sex" },
  { value: "sab", label: "Sáb" },
];

export function CantinaConfigPage() {
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["cantina-config"],
    queryFn: () => cantinaConfigApi.get(),
  });

  const [aberta, setAberta] = useState(true);
  const [horarioAbertura, setHorarioAbertura] = useState("");
  const [horarioFechamento, setHorarioFechamento] = useState("");
  const [diasFuncionamento, setDiasFuncionamento] = useState<string[]>([]);
  const [prazoPedido, setPrazoPedido] = useState("");
  const [prazoCancelamento, setPrazoCancelamento] = useState("");
  const [timezone, setTimezone] = useState("America/Sao_Paulo");
  const [observacoes, setObservacoes] = useState("");

  useEffect(() => {
    if (config) {
      setAberta(config.aberta);
      setHorarioAbertura(config.horario_abertura || "");
      setHorarioFechamento(config.horario_fechamento || "");
      setDiasFuncionamento(config.dias_funcionamento ? config.dias_funcionamento.split(",") : []);
      setPrazoPedido(config.prazo_pedido_minutos?.toString() || "");
      setPrazoCancelamento(config.prazo_cancelamento_minutos?.toString() || "");
      setTimezone(config.timezone || "America/Sao_Paulo");
      setObservacoes(config.observacoes || "");
    }
  }, [config]);

  const updateMutation = useMutation({
    mutationFn: () =>
      cantinaConfigApi.update({
        aberta,
        horario_abertura: horarioAbertura || undefined,
        horario_fechamento: horarioFechamento || undefined,
        dias_funcionamento: diasFuncionamento.length > 0 ? diasFuncionamento.join(",") : undefined,
        prazo_pedido_minutos: prazoPedido ? parseInt(prazoPedido) : undefined,
        prazo_cancelamento_minutos: prazoCancelamento ? parseInt(prazoCancelamento) : undefined,
        timezone: timezone || undefined,
        observacoes: observacoes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cantina-config"] });
    },
  });

  const toggleDia = (dia: string) => {
    setDiasFuncionamento((prev) =>
      prev.includes(dia) ? prev.filter((d) => d !== dia) : [...prev, dia],
    );
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: "Configurações da Cantina" }]} />

      <PageHeader
        title="Configurações da Cantina"
        description="Defina horários, prazos e estado de funcionamento"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Settings className="h-5 w-5 text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Status da Cantina</h3>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div>
                <p className="font-medium text-gray-900 dark:text-gray-100">Cantina Aberta</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {aberta ? "Pedidos sendo aceitos" : "Pedidos bloqueados"}
                </p>
              </div>
              <button
                onClick={() => setAberta(!aberta)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  aberta ? "bg-success-500" : "bg-gray-300 dark:bg-gray-600"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    aberta ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <Clock className="inline h-4 w-4 mr-1" />
                Horário de Funcionamento
              </label>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Abertura"
                  type="time"
                  value={horarioAbertura}
                  onChange={(e) => setHorarioAbertura(e.target.value)}
                />
                <Input
                  label="Fechamento"
                  type="time"
                  value={horarioFechamento}
                  onChange={(e) => setHorarioFechamento(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <CalendarDays className="inline h-4 w-4 mr-1" />
                Dias de Funcionamento
              </label>
              <div className="flex gap-2 flex-wrap">
                {DIAS_SEMANA.map((d) => (
                  <button
                    key={d.value}
                    onClick={() => toggleDia(d.value)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      diasFuncionamento.includes(d.value)
                        ? "bg-primary-500 text-white"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Prazos */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Prazos</h3>
          </div>

          <div className="space-y-4">
            <Input
              label="Prazo para pedir (minutos antes do fechamento)"
              type="number"
              value={prazoPedido}
              onChange={(e) => setPrazoPedido(e.target.value)}
              placeholder="Ex: 30"
            />

            <Input
              label="Prazo para cancelar (minutos após o pedido)"
              type="number"
              value={prazoCancelamento}
              onChange={(e) => setPrazoCancelamento(e.target.value)}
              placeholder="Ex: 15"
            />

            <Input
              label="Fuso horário da cantina"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="Ex: America/Sao_Paulo"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Observações
              </label>
              <textarea
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="Informações adicionais sobre o funcionamento..."
              />
            </div>
          </div>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button
          variant="primary"
          onClick={() => updateMutation.mutate()}
          loading={updateMutation.isPending}
        >
          <Save className="h-4 w-4 mr-1" />
          Salvar Configurações
        </Button>
      </div>

      {updateMutation.isSuccess && (
        <div className="p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
          <p className="text-sm text-success-600 dark:text-success-400">
            Configurações salvas com sucesso!
          </p>
        </div>
      )}
    </div>
  );
}
