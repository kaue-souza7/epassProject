import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Clock, MessageSquare, UtensilsCrossed } from "lucide-react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Spinner } from "../../components/ui/Spinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { useToast } from "../../components/ui/Toast";
import {
  cantinaOrdersApi,
  type PedidoListItem,
  type StatusPedido,
} from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { PedidoDetailModal } from "./PedidoDetailModal";

// Etapas oficiais do Kanban da Cantina (nesta ordem).
const KANBAN_COLUMNS: { status: StatusPedido; label: string; borderColor: string; headerBg: string }[] = [
  { status: "pendente", label: "SOLICITAÇÕES PENDENTES", borderColor: "border-warning-400", headerBg: "bg-warning-50 dark:bg-warning-900/20" },
  { status: "aprovado", label: "PEDIDO APROVADO", borderColor: "border-primary-400", headerBg: "bg-primary-50 dark:bg-primary-900/20" },
  { status: "em_producao", label: "PRODUÇÃO", borderColor: "border-blue-400", headerBg: "bg-blue-50 dark:bg-blue-900/20" },
  { status: "pronto", label: "PRONTO", borderColor: "border-success-400", headerBg: "bg-success-50 dark:bg-success-900/20" },
  { status: "retirado", label: "RETIRADO", borderColor: "border-gray-400", headerBg: "bg-gray-50 dark:bg-gray-800" },
];

const CANCELADO_COLUMN = {
  status: "cancelado" as StatusPedido,
  label: "CANCELADOS",
  borderColor: "border-danger-400",
  headerBg: "bg-danger-50 dark:bg-danger-900/20",
};

const STATUS_BADGE: Record<StatusPedido, { label: string; variant: "success" | "warning" | "danger" | "info" | "default" }> = {
  pendente: { label: "Pendente", variant: "warning" },
  aprovado: { label: "Aprovado", variant: "info" },
  em_producao: { label: "Em Produção", variant: "info" },
  pronto: { label: "Pronto", variant: "success" },
  retirado: { label: "Retirado", variant: "default" },
  cancelado: { label: "Cancelado", variant: "danger" },
};

const VALID_DRAG_TRANSITIONS: Record<string, string> = {
  "pendente->aprovado": "approve",
  "pendente->cancelado": "cancel",
  "aprovado->em_producao": "produce",
  "aprovado->cancelado": "cancel",
  "em_producao->pronto": "ready",
  "pronto->retirado": "delivered",
};

const VALID_DRAG_TARGETS: Record<StatusPedido, StatusPedido[]> = {
  pendente: ["aprovado", "cancelado"],
  aprovado: ["em_producao", "cancelado"],
  em_producao: ["pronto"],
  pronto: ["retirado"],
  retirado: [],
  cancelado: [],
};

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function getActionForTransition(from: StatusPedido, to: StatusPedido): string | null {
  return VALID_DRAG_TRANSITIONS[`${from}->${to}`] || null;
}

// ── Sortable Card ──────────────────────────────────────────────

interface SortableCardProps {
  pedido: PedidoListItem;
  onAction: (id: string, action: string) => void;
  onConfirmAction: (id: string, action: string, title: string, message: string) => void;
  actionLoading: string | null;
  onClick: () => void;
}

function SortableCard({ pedido, onAction, onConfirmAction, actionLoading, onClick }: SortableCardProps) {
  const isCancelled = pedido.status === "cancelado";
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: pedido.id,
    data: { status: pedido.status },
    disabled: isCancelled,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 50 : undefined,
  };

  const badge = STATUS_BADGE[pedido.status];
  const isActionLoading = actionLoading === pedido.id;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3.5 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow touch-none"
      onClick={() => {
        if (isActionLoading) return;
        onClick();
      }}
    >
      <div className="flex items-start justify-between mb-1.5">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm truncate">
            {pedido.aluno_nome || "Aluno"}
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            {pedido.aluno_turma && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-medium">
                {pedido.aluno_turma}
              </span>
            )}
            <div className="flex items-center gap-0.5 text-[10px] text-gray-500 dark:text-gray-400">
              <Clock className="h-2.5 w-2.5" />
              {formatTime(pedido.created_at)}
            </div>
          </div>
        </div>
        <Badge variant={badge.variant}>{badge.label}</Badge>
      </div>

      <p className="text-xs text-gray-600 dark:text-gray-300 mb-1">
        {formatCurrency(pedido.valor_total)}
      </p>

      {pedido.observacoes && (
        <div className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400 mb-2.5">
          <MessageSquare className="h-2.5 w-2.5 flex-shrink-0" />
          <span className="truncate">{pedido.observacoes}</span>
        </div>
      )}

      {pedido.itens && pedido.itens.length > 0 && (
        <div className="mb-2.5 space-y-0.5">
          {pedido.itens.map((item) => (
            <div key={item.id} className="flex justify-between text-[10px] text-gray-600 dark:text-gray-400">
              <span className="truncate">{item.quantidade}x {item.produto_nome}</span>
              <span className="flex-shrink-0 ml-1">{formatCurrency(item.preco_total)}</span>
            </div>
          ))}
        </div>
      )}

      {!pedido.observacoes && (!pedido.itens || pedido.itens.length === 0) && <div className="mb-2.5" />}

      <div className="flex items-center justify-between">
        <button
          onClick={(e) => { e.stopPropagation(); onClick(); }}
          className="text-[10px] text-primary-500 hover:text-primary-600 font-medium"
        >
          Detalhes
        </button>

        {!isCancelled && (
        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
          {pedido.status === "pendente" && (
            <>
              <Button size="sm" variant="danger" loading={isActionLoading} onClick={() => onConfirmAction(pedido.id, "reject", "Rejeitar Pedido", "Tem certeza que deseja rejeitar este pedido?")}>
                Rejeitar
              </Button>
              <Button size="sm" variant="primary" loading={isActionLoading} onClick={() => onAction(pedido.id, "approve")}>
                Aprovar
              </Button>
            </>
          )}
          {pedido.status === "aprovado" && (
            <>
              <Button size="sm" variant="danger" loading={isActionLoading} onClick={() => onConfirmAction(pedido.id, "cancel", "Cancelar Pedido", "Tem certeza que deseja cancelar este pedido? O estoque será devolvido e, se já houver débito, o valor será estornado.")}>
                Cancelar
              </Button>
              <Button size="sm" variant="primary" loading={isActionLoading} onClick={() => onAction(pedido.id, "produce")}>
                Produção
              </Button>
            </>
          )}
          {pedido.status === "em_producao" && (
            <Button size="sm" variant="primary" loading={isActionLoading} onClick={() => onAction(pedido.id, "ready")}>
              Pronto
            </Button>
          )}
          {pedido.status === "pronto" && (
            <Button size="sm" variant="primary" loading={isActionLoading} onClick={() => onAction(pedido.id, "delivered")}>
              Retirado
            </Button>
          )}
        </div>
        )}
      </div>
    </div>
  );
}

// ── Drag Overlay Card ──────────────────────────────────────────

function DragOverlayCard({ pedido }: { pedido: PedidoListItem }) {
  const badge = STATUS_BADGE[pedido.status];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-primary-400 p-3.5 shadow-2xl rotate-2 opacity-90 w-72">
      <div className="flex items-start justify-between mb-1.5">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm truncate">
            {pedido.aluno_nome || "Aluno"}
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            {pedido.aluno_turma && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-medium">
                {pedido.aluno_turma}
              </span>
            )}
          </div>
        </div>
        <Badge variant={badge.variant}>{badge.label}</Badge>
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-300 mb-1">
        {formatCurrency(pedido.valor_total)}
      </p>
      {pedido.itens && pedido.itens.length > 0 && (
        <div className="space-y-0.5">
          {pedido.itens.map((item) => (
            <div key={item.id} className="flex justify-between text-[10px] text-gray-500 dark:text-gray-400">
              <span>{item.quantidade}x {item.produto_nome}</span>
              <span>{formatCurrency(item.preco_total)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Kanban Column ──────────────────────────────────────────────

interface KanbanColumnProps {
  status: StatusPedido;
  label: string;
  borderColor: string;
  headerBg: string;
  count: number;
  children: React.ReactNode;
}

function KanbanColumn({ status, label, borderColor, headerBg, count, children }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col min-w-[280px] w-full flex-1 rounded-xl border-t-2 ${borderColor} bg-gray-50/50 dark:bg-gray-900/30 transition-colors ${
        isOver ? "bg-primary-50/50 dark:bg-primary-900/10 ring-2 ring-primary-300 dark:ring-primary-700" : ""
      }`}
    >
      <div className={`px-3 py-2.5 ${headerBg} rounded-t-lg flex items-center justify-between`}>
        <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          {label}
        </h3>
        <span className="text-[10px] font-bold bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full min-w-[20px] text-center">
          {count}
        </span>
      </div>
      <div className="flex-1 p-2 space-y-2 min-h-[120px] max-h-[calc(100vh-280px)] overflow-y-auto">
        {count === 0 ? (
          <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-6 italic">
            Nenhum pedido
          </p>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────

export function KanbanPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();
  const prefix = `/${user?.perfil ?? "admin"}`;
  const [selectedPedidoId, setSelectedPedidoId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activePedido, setActivePedido] = useState<PedidoListItem | null>(null);
  const [showCancelled, setShowCancelled] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({ open: false, title: "", message: "", onConfirm: () => {} });
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["cantina-kanban"],
    queryFn: () => cantinaOrdersApi.list({ size: 100 }),
    refetchInterval: 15000,
  });

  const allPedidos = data?.items || [];
  const pedidos = allPedidos;

  const columns = showCancelled
    ? [...KANBAN_COLUMNS, CANCELADO_COLUMN]
    : KANBAN_COLUMNS;

  const pedidosByStatus = columns.reduce(
    (acc, col) => {
      acc[col.status] = pedidos.filter((p) => p.status === col.status);
      return acc;
    },
    {} as Record<StatusPedido, PedidoListItem[]>
  );

  const pendingCount = pedidosByStatus.pendente?.length || 0;
  const cancelledCount = pedidos.filter((p) => p.status === "cancelado").length;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  const actionMutation = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: string }) => {
      switch (action) {
        case "approve": return cantinaOrdersApi.approve(id);
        case "reject": return cantinaOrdersApi.reject(id);
        case "produce": return cantinaOrdersApi.produce(id);
        case "ready": return cantinaOrdersApi.ready(id);
        case "delivered": return cantinaOrdersApi.delivered(id);
        case "cancel": return cantinaOrdersApi.cancel(id);
        default: return;
      }
    },
    onMutate: async ({ id }) => {
      setActionLoading(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cantina-kanban"] });
      toast("success", "Pedido atualizado com sucesso!");
    },
    onError: (err: Error) => {
      toast("error", err.message || "Erro ao executar ação");
    },
    onSettled: () => {
      setActionLoading(null);
    },
  });

  const handleAction = useCallback(
    (id: string, action: string) => {
      actionMutation.mutate({ id, action });
    },
    [actionMutation]
  );

  const handleConfirmAction = useCallback(
    (id: string, action: string, title: string, message: string) => {
      setConfirmDialog({
        open: true,
        title,
        message,
        onConfirm: () => {
          setConfirmDialog((prev) => ({ ...prev, open: false }));
          actionMutation.mutate({ id, action });
        },
      });
    },
    [actionMutation]
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const { active } = event;
      const pedido = pedidos.find((p) => p.id === active.id);
      if (pedido) setActivePedido(pedido);
    },
    [pedidos]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActivePedido(null);

      if (!over) return;

      const pedidoId = active.id as string;
      const fromStatus = active.data.current?.status as StatusPedido | undefined;
      const toStatus = over.id as StatusPedido;

      if (!fromStatus || fromStatus === toStatus) return;

      if (!VALID_DRAG_TARGETS[fromStatus]?.includes(toStatus)) return;

      const action = getActionForTransition(fromStatus, toStatus);
      if (!action) return;

      if (action === "cancel" || action === "reject") {
        setConfirmDialog({
          open: true,
          title: action === "cancel" ? "Cancelar Pedido" : "Rejeitar Pedido",
          message: action === "cancel"
            ? "Tem certeza que deseja cancelar este pedido? O estoque será devolvido e, se já houver débito, o valor será estornado."
            : "Tem certeza que deseja rejeitar este pedido?",
          onConfirm: () => {
            setConfirmDialog((prev) => ({ ...prev, open: false }));
            actionMutation.mutate({ id: pedidoId, action });
          },
        });
        return;
      }

      actionMutation.mutate({ id: pedidoId, action });
    },
    [actionMutation]
  );

  useEffect(() => {
    return () => {
      if (autoRefreshRef.current) clearInterval(autoRefreshRef.current);
    };
  }, []);

  return (
    <div className="space-y-4">
      <Breadcrumb items={[{ label: "Cantina", path: `${prefix}/cantina/gestao` }, { label: "Kanban" }]} />

      <PageHeader
        title="Kanban de Pedidos"
        description={pendingCount > 0 ? `${pendingCount} pedido(s) pendente(s)` : "Nenhum pedido pendente"}
      >
        <Button
          variant="ghost"
          onClick={() => setShowCancelled((prev) => !prev)}
          title={showCancelled ? "Ocultar cancelados" : "Mostrar cancelados"}
        >
          {showCancelled ? "Ocultar cancelados" : `Cancelados (${cancelledCount})`}
        </Button>
        <Button variant="ghost" onClick={() => refetch()} loading={isFetching}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </PageHeader>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : pedidos.length === 0 ? (
        <EmptyState
          icon={UtensilsCrossed}
          title="Nenhum pedido"
          description="Os pedidos aparecerão aqui quando forem criados."
        />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-3 w-full overflow-x-auto pb-4">
            {columns.map((col) => {
              const items = pedidosByStatus[col.status] || [];
              const itemIds = items.map((p) => p.id);

              return (
                <KanbanColumn
                  key={col.status}
                  status={col.status}
                  label={col.label}
                  borderColor={col.borderColor}
                  headerBg={col.headerBg}
                  count={items.length}
                >
                  <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
                    {items.map((pedido) => (
                      <SortableCard
                        key={pedido.id}
                        pedido={pedido}
                        onAction={handleAction}
                        onConfirmAction={handleConfirmAction}
                        actionLoading={actionLoading}
                        onClick={() => setSelectedPedidoId(pedido.id)}
                      />
                    ))}
                  </SortableContext>
                </KanbanColumn>
              );
            })}
          </div>

          <DragOverlay>
            {activePedido ? <DragOverlayCard pedido={activePedido} /> : null}
          </DragOverlay>
        </DndContext>
      )}

      <PedidoDetailModal
        open={!!selectedPedidoId}
        pedidoId={selectedPedidoId}
        onClose={() => setSelectedPedidoId(null)}
      />

      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.title}
        message={confirmDialog.message}
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog((prev) => ({ ...prev, open: false }))}
      />
    </div>
  );
}
