import { useQuery } from "@tanstack/react-query";
import { Modal } from "../../components/ui/Modal";
import { Badge } from "../../components/ui/Badge";
import { Spinner } from "../../components/ui/Spinner";
import { cantinaOrdersApi, type Pedido, type StatusPedido } from "../../api/endpoints";

interface PedidoDetailModalProps {
  open: boolean;
  pedidoId: string | null;
  onClose: () => void;
}

const STATUS_LABELS: Record<StatusPedido, string> = {
  pendente: "Pendente",
  aprovado: "Aprovado",
  em_producao: "Em Produção",
  pronto: "Pronto",
  retirado: "Retirado",
  cancelado: "Cancelado",
};

const STATUS_VARIANT: Record<StatusPedido, "success" | "warning" | "danger" | "info" | "default"> = {
  pendente: "warning",
  aprovado: "info",
  em_producao: "info",
  pronto: "success",
  retirado: "default",
  cancelado: "danger",
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function PedidoDetailModal({ open, pedidoId, onClose }: PedidoDetailModalProps) {
  const { data: pedido, isLoading } = useQuery<Pedido>({
    queryKey: ["cantina-order", pedidoId],
    queryFn: () => cantinaOrdersApi.getById(pedidoId!),
    enabled: open && !!pedidoId,
  });

  if (!open) return null;

  return (
    <Modal open={open} title="Detalhes do Pedido" onClose={onClose} size="lg">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : !pedido ? (
        <p className="text-center text-gray-500 py-8">Pedido não encontrado.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Aluno</p>
              <p className="font-medium text-gray-900 dark:text-gray-100">{pedido.aluno_nome}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Status</p>
              <Badge variant={STATUS_VARIANT[pedido.status]}>
                {STATUS_LABELS[pedido.status]}
              </Badge>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Data/Hora</p>
              <p className="font-medium text-gray-900 dark:text-gray-100">{formatDate(pedido.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Total</p>
              <p className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(pedido.valor_total)}</p>
            </div>
          </div>

          {pedido.observacoes && (
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Observações</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">{pedido.observacoes}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Itens</p>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-800">
                    <th className="text-left px-3 py-2 font-medium text-gray-600 dark:text-gray-300">Produto</th>
                    <th className="text-center px-3 py-2 font-medium text-gray-600 dark:text-gray-300">Qtd</th>
                    <th className="text-right px-3 py-2 font-medium text-gray-600 dark:text-gray-300">Preço</th>
                    <th className="text-right px-3 py-2 font-medium text-gray-600 dark:text-gray-300">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {pedido.itens.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2 text-gray-900 dark:text-gray-100">{item.produto_nome}</td>
                      <td className="px-3 py-2 text-center text-gray-700 dark:text-gray-300">{item.quantidade}</td>
                      <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">{formatCurrency(item.preco_unitario)}</td>
                      <td className="px-3 py-2 text-right font-medium text-gray-900 dark:text-gray-100">{formatCurrency(item.preco_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
