import { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  RefreshControl,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useOrderHistory } from "../../hooks/useCantina";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { StatusPedido, PedidoListItem } from "../../api/cantina.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "PedidoHistorico">;

const STATUS_LABELS: Record<StatusPedido, string> = {
  pendente: "Pendente",
  aprovado: "Aprovado",
  em_producao: "Em Produção",
  pronto: "Pronto",
  retirado: "Retirado",
  cancelado: "Cancelado",
};

const STATUS_COLORS: Record<StatusPedido, string> = {
  pendente: "#F0AD4E",
  aprovado: "#5BC0DE",
  em_producao: "#5CB85C",
  pronto: "#2ECC71",
  retirado: "#999999",
  cancelado: "#E74C3C",
};

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

export function PedidoHistoricoScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const [page, setPage] = useState(1);
  const [allItems, setAllItems] = useState<PedidoListItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const { data, loading, error, refetch } = useOrderHistory(page);

  useFocusEffect(
    useCallback(() => {
      setPage(1);
      setAllItems([]);
      refetch();
    }, [refetch]),
  );

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    setPage(1);
    setAllItems([]);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const handleLoadMore = useCallback(() => {
    if (data && allItems.length < data.total && !loading) {
      setPage((p) => p + 1);
    }
  }, [data, allItems.length, loading]);

  const items = data?.items ?? [];
  const displayItems = page === 1 ? items : allItems;

  // Accumulate items across pages
  useFocusEffect(
    useCallback(() => {
      if (data?.items) {
        setAllItems((prev) => {
          if (page === 1) return data.items;
          const existingIds = new Set(prev.map((i) => i.id));
          const newItems = data.items.filter((i) => !existingIds.has(i.id));
          return [...prev, ...newItems];
        });
      }
    }, [data, page]),
  );

  const renderItem = useCallback(
    ({ item }: { item: PedidoListItem }) => (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate("PedidoStatus", { pedidoId: item.id })}
      >
        <View style={styles.cardHeader}>
          <Text style={styles.cardId}>#{String(item.id).slice(0, 8)}</Text>
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: STATUS_COLORS[item.status] + "20" },
            ]}
          >
            <Text
              style={[styles.statusText, { color: STATUS_COLORS[item.status] }]}
            >
              {STATUS_LABELS[item.status]}
            </Text>
          </View>
        </View>
        <Text style={styles.cardAluno}>{item.aluno_nome}</Text>
        <View style={styles.cardFooter}>
          <Text style={styles.cardDate}>{formatDate(item.created_at)}</Text>
          <Text style={styles.cardPrice}>{formatCurrency(item.valor_total)}</Text>
        </View>
      </TouchableOpacity>
    ),
    [navigation],
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.container}>
        <LoadingState />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <ErrorState message={error} onRetry={refetch} />
      </View>
    );
  }

  const total = data?.total || 0;

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Histórico de Pedidos</Text>
          <View style={{ width: 28 }} />
        </View>

        {displayItems.length === 0 && !loading ? (
          <View style={styles.emptyContainer}>
            <ThemedIcon name="receipt-outline" size={64} color="#C7C7C7" />
            <Text style={styles.emptyText}>Nenhum pedido encontrado</Text>
          </View>
        ) : (
          <FlatList
            data={displayItems}
            keyExtractor={(item) => item.id}
            renderItem={renderItem}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
            }
            onEndReached={handleLoadMore}
            onEndReachedThreshold={0.5}
            ListFooterComponent={
              <View style={styles.footer}>
                <Text style={styles.footerText}>
                  {total} pedido{total !== 1 ? "s" : ""}
                </Text>
              </View>
            }
          />
        )}
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

  emptyContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  emptyText: { fontSize: 16, color: "#999999" },

  listContent: { padding: 20, paddingBottom: 40 },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  cardId: { fontSize: 14, fontWeight: "600", color: "#7A7A7A" },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: { fontSize: 12, fontWeight: "600" },
  cardAluno: { fontSize: 16, fontWeight: "600", color: "#1F1F1F", marginBottom: 8 },
  cardFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  cardDate: { fontSize: 13, color: "#999999" },
  cardPrice: { fontSize: 15, fontWeight: "700", color: "#FF5B8F" },

  footer: {
    paddingVertical: 16,
    alignItems: "center",
  },
  footerText: { fontSize: 13, color: "#999999" },
});
