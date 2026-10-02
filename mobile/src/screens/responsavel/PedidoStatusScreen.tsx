import { KeepAwake } from "../../components/KeepAwake";
import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  RefreshControl,
} from "react-native";
import { useNavigation, useRoute, useFocusEffect } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { RouteProp } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { useOrderDetail, useCancelOrder } from "../../hooks/useCantina";
import { useWallet } from "../../hooks/useWallet";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../components/Toast";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { StatusPedido } from "../../api/cantina.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "PedidoStatus">;
type RouteProps = RouteProp<ResponsavelStackParamList, "PedidoStatus">;

const STATUS_LABELS: Record<StatusPedido, string> = {
  pendente: "Pendente",
  aprovado: "Aprovado",
  em_producao: "Em Produção",
  pronto: "Pronto",
  retirado: "Retirado",
  cancelado: "Cancelado",
};

const STATUS_ICONS: Record<StatusPedido, keyof typeof Ionicons.glyphMap> = {
  pendente: "hourglass-outline",
  aprovado: "checkmark-circle-outline",
  em_producao: "nutrition-outline",
  pronto: "sparkles-outline",
  retirado: "bag-check-outline",
  cancelado: "close-circle-outline",
};

const TIMELINE_ORDER: StatusPedido[] = [
  "pendente",
  "aprovado",
  "em_producao",
  "pronto",
  "retirado",
];

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
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

function getStatusIndex(status: StatusPedido): number {
  if (status === "cancelado") return -1;
  return TIMELINE_ORDER.indexOf(status);
}

export function PedidoStatusScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<RouteProps>();
  const toast = useToast();
  const { pedidoId } = route.params;
  const [refreshing, setRefreshing] = useState(false);

  const { data: pedido, loading, error, refetch } = useOrderDetail(pedidoId);
  const { cancelar, loading: cancelLoading, error: cancelError } = useCancelOrder();
  const { refetch: refetchSaldo } = useWallet();

  useFocusEffect(
    useCallback(() => {
      refetch();
    }, [refetch]),
  );

  // Atualiza automaticamente enquanto o pedido está em andamento no Kanban.
  useEffect(() => {
    if (!pedido) return;
    if (pedido.status === "retirado" || pedido.status === "cancelado") return;
    const interval = setInterval(() => {
      refetch();
    }, 15000);
    return () => clearInterval(interval);
  }, [pedido?.status, refetch]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const handleCancel = useCallback(() => {
    Alert.alert(
      "Cancelar Pedido",
      "Tem certeza que deseja cancelar este pedido? O estoque será devolvido e, se já houver débito, o valor será estornado.",
      [
        { text: "Não", style: "cancel" },
        {
          text: "Sim, cancelar",
          style: "destructive",
          onPress: async () => {
            const result = await cancelar(pedidoId);
            if (result) {
              refetch();
              refetchSaldo();
              toast.success("Pedido cancelado");
            } else if (cancelError) {
              toast.error(cancelError);
            }
          },
        },
      ],
    );
  }, [cancelar, pedidoId, refetch, refetchSaldo, cancelError, toast]);

  if (loading && !refreshing) {
    return (
      <View style={styles.container}>
        <LoadingState />
      </View>
    );
  }

  if (error || !pedido) {
    return (
      <View style={styles.container}>
        <ErrorState message={error || "Pedido não encontrado"} onRetry={refetch} />
      </View>
    );
  }

  const currentIdx = getStatusIndex(pedido.status);
  const isCancelled = pedido.status === "cancelado";
  const canCancel = pedido.status === "pendente" || pedido.status === "aprovado";

  return (
    <View style={styles.container}>
      {/* Evita a tela apagar durante a leitura. */}
      <KeepAwake />
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Pedido #{String(pedido.id).slice(0, 8)}</Text>
          <View style={{ width: 28 }} />
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
        >
          {/* Status card */}
          <View style={[styles.statusCard, isCancelled && styles.statusCardCancelled]}>
            <ThemedIcon
              name={STATUS_ICONS[pedido.status]}
              size={48}
              color={isCancelled ? "#E74C3C" : "#FF5B8F"}
            />
            <Text style={[styles.statusTitle, isCancelled && styles.statusTitleCancelled]}>
              {STATUS_LABELS[pedido.status]}
            </Text>
            {isCancelled && (
              <Text style={styles.cancelledText}>Este pedido foi cancelado.</Text>
            )}
          </View>

          {/* Error message */}
          {cancelLoading && (
            <View style={styles.infoBanner}>
              <Text style={styles.infoBannerText}>Cancelando pedido...</Text>
            </View>
          )}

          {/* Timeline */}
          {!isCancelled && (
            <View style={styles.timelineCard}>
              <Text style={styles.timelineTitle}>Acompanhamento</Text>
              {TIMELINE_ORDER.map((status, idx) => {
                const isCompleted = currentIdx > idx;
                const isCurrent = currentIdx === idx;
                const isFuture = currentIdx < idx;

                return (
                  <View key={status} style={styles.timelineRow}>
                    <View style={styles.timelineLeft}>
                      <View
                        style={[
                          styles.timelineDot,
                          isCompleted && styles.timelineDotCompleted,
                          isCurrent && styles.timelineDotCurrent,
                        ]}
                      >
                        {isCompleted && (
                          <ThemedIcon name="checkmark" size={12} color="#FFFFFF" />
                        )}
                      </View>
                      {idx < TIMELINE_ORDER.length - 1 && (
                        <View
                          style={[
                            styles.timelineLine,
                            isCompleted && styles.timelineLineCompleted,
                          ]}
                        />
                      )}
                    </View>
                    <View style={styles.timelineContent}>
                      <Text
                        style={[
                          styles.timelineLabel,
                          isFuture && styles.timelineLabelFuture,
                          isCurrent && styles.timelineLabelCurrent,
                        ]}
                      >
                        {STATUS_LABELS[status]}
                      </Text>
                      {isCurrent && (
                        <Text style={styles.timelineCurrentBadge}>Etapa atual</Text>
                      )}
                    </View>
                  </View>
                );
              })}
            </View>
          )}

          {/* Detalhes */}
          <View style={styles.detailsCard}>
            <Text style={styles.detailsTitle}>Detalhes</Text>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Aluno</Text>
              <Text style={styles.detailValue}>{pedido.aluno_nome}</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Data/Hora</Text>
              <Text style={styles.detailValue}>{formatDate(pedido.created_at)}</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Total</Text>
              <Text style={styles.detailValueBold}>{formatCurrency(pedido.valor_total)}</Text>
            </View>
            {pedido.saldo_debitado > 0 && (
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Saldo debitado</Text>
                <Text style={styles.detailValue}>{formatCurrency(pedido.saldo_debitado)}</Text>
              </View>
            )}
            {pedido.observacoes && (
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Obs</Text>
                <Text style={[styles.detailValue, { flex: 1, textAlign: "right" }]}>
                  {pedido.observacoes}
                </Text>
              </View>
            )}
          </View>

          {/* Itens */}
          <View style={styles.itensCard}>
            <Text style={styles.itensTitle}>Itens</Text>
            {pedido.itens.map((item) => (
              <View key={item.id} style={styles.itemRow}>
                <Text style={styles.itemName}>
                  {item.produto_nome} × {item.quantidade}
                </Text>
                <Text style={styles.itemPrice}>{formatCurrency(item.preco_total)}</Text>
              </View>
            ))}
          </View>

          {/* Cancel button */}
          {canCancel && (
            <TouchableOpacity
              style={[styles.cancelButton, cancelLoading && styles.cancelButtonDisabled]}
              onPress={handleCancel}
              disabled={cancelLoading}
            >
              <ThemedIcon name="close-circle-outline" size={20} color="#E74C3C" />
              <Text style={styles.cancelButtonText}>
                {cancelLoading ? "Cancelando..." : "Cancelar Pedido"}
              </Text>
            </TouchableOpacity>
          )}
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = createThemedStyles({
  container: { flex: 1, backgroundColor: "#F5F5F7" },
  safeArea: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  headerTitle: { fontSize: 18, fontWeight: "700", color: "#1F1F1F" },
  scrollView: { flex: 1 },
  scrollContent: { padding: 20, paddingBottom: 40 },

  statusCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 24,
    alignItems: "center",
    marginBottom: 16,
  },
  statusCardCancelled: { backgroundColor: "#FFF5F5" },
  statusTitle: { fontSize: 20, fontWeight: "700", color: "#1F1F1F", marginTop: 12 },
  statusTitleCancelled: { color: "#E74C3C" },
  cancelledText: { fontSize: 14, color: "#E74C3C", marginTop: 4 },

  infoBanner: {
    backgroundColor: "#FFF3CD",
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  infoBannerText: { fontSize: 13, color: "#856404", textAlign: "center" },

  timelineCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  timelineTitle: { fontSize: 16, fontWeight: "700", color: "#1F1F1F", marginBottom: 16 },
  timelineRow: { flexDirection: "row", minHeight: 40 },
  timelineLeft: { width: 24, alignItems: "center" },
  timelineDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: "#E0E0E0",
    alignItems: "center",
    justifyContent: "center",
  },
  timelineDotCompleted: { backgroundColor: "#2ECC71" },
  timelineDotCurrent: { backgroundColor: "#FF5B8F" },
  timelineLine: { width: 2, flex: 1, backgroundColor: "#E0E0E0", marginVertical: 4 },
  timelineLineCompleted: { backgroundColor: "#2ECC71" },
  timelineContent: { flex: 1, marginLeft: 12, paddingBottom: 8 },
  timelineLabel: { fontSize: 15, color: "#7A7A7A" },
  timelineLabelFuture: { color: "#C7C7C7" },
  timelineLabelCurrent: { color: "#1F1F1F", fontWeight: "600" },
  timelineCurrentBadge: {
    fontSize: 11,
    color: "#FF5B8F",
    fontWeight: "600",
    marginTop: 2,
  },

  detailsCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  detailsTitle: { fontSize: 16, fontWeight: "700", color: "#1F1F1F", marginBottom: 12 },
  detailRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
  },
  detailLabel: { fontSize: 14, color: "#7A7A7A" },
  detailValue: { fontSize: 14, color: "#1F1F1F" },
  detailValueBold: { fontSize: 16, fontWeight: "700", color: "#1F1F1F" },

  itensCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  itensTitle: { fontSize: 16, fontWeight: "700", color: "#1F1F1F", marginBottom: 12 },
  itemRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#F0F0F0",
  },
  itemName: { fontSize: 14, color: "#333333", flex: 1 },
  itemPrice: { fontSize: 14, fontWeight: "600", color: "#1F1F1F", marginLeft: 8 },

  cancelButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#FFF5F5",
    borderWidth: 1,
    borderColor: "#E74C3C",
    borderRadius: 12,
    padding: 14,
  },
  cancelButtonDisabled: { opacity: 0.5 },
  cancelButtonText: { fontSize: 15, fontWeight: "600", color: "#E74C3C" },
});
