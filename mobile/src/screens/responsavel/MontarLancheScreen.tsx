import { useState, useCallback, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  TextInput,
  RefreshControl,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useWallet } from "../../hooks/useWallet";
import { useMenu, useTodayOrder, useCreateOrder } from "../../hooks/useCantina";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../components/Toast";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { MenuItem } from "../../api/cantina.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "MontarLanche">;

interface CartItem {
  produto: MenuItem;
  quantidade: number;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function MontarLancheScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const toast = useToast();
  const { selectedChild } = useSelectedStudent();
  const { saldo, loading: saldoLoading, refetch: refetchSaldo } = useWallet();
  const { data: menu, loading: menuLoading, error: menuError, refetch: refetchMenu } = useMenu();
  const { pedido: todayOrder, loading: todayLoading, refetch: refetchToday } = useTodayOrder();
  const { criarPedido, loading: criando, error: criarError } = useCreateOrder();

  const [cart, setCart] = useState<CartItem[]>([]);
  const [observacoes, setObservacoes] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const availableMenu = useMemo(
    () => (menu || []).filter((m) => m.disponivel),
    [menu],
  );

  const cartTotal = useMemo(
    () => cart.reduce((sum, item) => sum + item.produto.preco * item.quantidade, 0),
    [cart],
  );

  const saldoPosSaldo = (saldo || 0) - cartTotal;

  useFocusEffect(
    useCallback(() => {
      refetchMenu();
      refetchToday();
      refetchSaldo();
    }, [refetchMenu, refetchToday, refetchSaldo]),
  );

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchMenu(), refetchToday(), refetchSaldo()]);
    setRefreshing(false);
  }, [refetchMenu, refetchToday, refetchSaldo]);

  const updateQuantity = useCallback((produto: MenuItem, delta: number) => {
    setCart((prev) => {
      const existing = prev.find((c) => c.produto.id === produto.id);
      if (existing) {
        const newQty = existing.quantidade + delta;
        if (newQty <= 0) return prev.filter((c) => c.produto.id !== produto.id);
        return prev.map((c) =>
          c.produto.id === produto.id ? { ...c, quantidade: newQty } : c,
        );
      }
      if (delta > 0) return [...prev, { produto, quantidade: 1 }];
      return prev;
    });
  }, []);

  const handleConfirm = useCallback(async () => {
    if (!selectedChild) return;
    if (cart.length === 0) {
      toast.warning("Adicione pelo menos um item ao pedido.");
      return;
    }
    if (saldoPosSaldo < 0) {
      toast.error("O saldo da carteira não é suficiente para este pedido.");
      return;
    }

    const result = await criarPedido({
      aluno_id: selectedChild.aluno_id,
      itens: cart.map((c) => ({
        produto_id: c.produto.id,
        quantidade: c.quantidade,
      })),
      observacoes: observacoes || undefined,
    });

    if (result) {
      setCart([]);
      setObservacoes("");
      refetchToday();
      refetchSaldo();
      toast.success("Pedido enviado com sucesso!");
      setTimeout(() => navigation.goBack(), 900);
    } else if (criarError) {
      toast.error(criarError);
    }
  }, [selectedChild, cart, saldoPosSaldo, criarPedido, criarError, observacoes, refetchToday, refetchSaldo, navigation, toast]);

  if (!selectedChild) {
    return (
      <View style={styles.container}>
        <ErrorState message="Nenhum aluno selecionado." />
      </View>
    );
  }

  if (menuLoading || todayLoading || saldoLoading) {
    return (
      <View style={styles.container}>
        <LoadingState />
      </View>
    );
  }

  if (menuError) {
    return (
      <View style={styles.container}>
        <ErrorState message={menuError} onRetry={refetchMenu} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Montar Lanche</Text>
          <View style={{ width: 28 }} />
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#FF5B8F" />
          }
        >
          {/* Aluno + Saldo */}
          <View style={styles.studentCard}>
            <Text style={styles.studentLabel}>Para:</Text>
            <Text style={styles.studentName}>{selectedChild.aluno_nome}</Text>
            <View style={styles.saldoRow}>
              <Text style={styles.saldoLabel}>Saldo disponível</Text>
              <Text style={styles.saldoValue}>{formatCurrency(saldo || 0)}</Text>
            </View>
          </View>

          {/* Pedido de hoje */}
          {todayOrder && (
            <View style={styles.todayCard}>
              <View style={styles.todayHeader}>
                <ThemedIcon name="receipt-outline" size={20} color="#FF5B8F" />
                <Text style={styles.todayTitle}>Pedido de hoje</Text>
              </View>
              <View style={styles.todayInfo}>
                <Text style={styles.todayStatus}>
                  #{String(todayOrder.id).slice(0, 8)} — {todayOrder.status}
                </Text>
                <Text style={styles.todayTotal}>{formatCurrency(todayOrder.valor_total)}</Text>
              </View>
              <TouchableOpacity
                style={styles.todayButton}
                onPress={() => navigation.navigate("PedidoStatus", { pedidoId: todayOrder.id })}
              >
                <Text style={styles.todayButtonText}>Acompanhar pedido</Text>
              </TouchableOpacity>
            </View>
          )}

          {!todayOrder && (
            <View style={styles.emptyTodayCard}>
              <ThemedIcon name="cart-outline" size={32} color="#C7C7C7" />
              <Text style={styles.emptyTodayText}>
                Você ainda não montou o lanche de hoje.
              </Text>
            </View>
          )}

          {/* Cardápio */}
          <Text style={styles.sectionTitle}>Cardápio</Text>
          {availableMenu.length === 0 ? (
            <Text style={styles.emptyText}>Nenhum produto disponível.</Text>
          ) : (
            availableMenu.map((item) => {
              const cartItem = cart.find((c) => c.produto.id === item.id);
              const qty = cartItem?.quantidade || 0;

              return (
                <View key={item.id} style={styles.menuItem}>
                  <View style={styles.menuInfo}>
                    <Text style={styles.menuName}>{item.nome}</Text>
                    {item.descricao ? (
                      <Text style={styles.menuDesc}>{item.descricao}</Text>
                    ) : null}
                    <Text style={styles.menuPrice}>{formatCurrency(item.preco)}</Text>
                  </View>
                  <View style={styles.quantityControl}>
                    <TouchableOpacity
                      style={styles.qtyButton}
                      onPress={() => updateQuantity(item, -1)}
                      disabled={qty === 0}
                    >
                      <ThemedIcon
                        name="remove"
                        size={20}
                        color={qty === 0 ? "#C7C7C7" : "#FF5B8F"}
                      />
                    </TouchableOpacity>
                    <Text style={styles.qtyValue}>{qty}</Text>
                    <TouchableOpacity
                      style={styles.qtyButton}
                      onPress={() => updateQuantity(item, 1)}
                    >
                      <ThemedIcon name="add" size={20} color="#FF5B8F" />
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          )}

          {/* Resumo do pedido */}
          {cart.length > 0 && (
            <View style={styles.summaryCard}>
              <Text style={styles.summaryTitle}>Resumo do pedido</Text>
              {cart.map((c) => (
                <View key={c.produto.id} style={styles.summaryRow}>
                  <Text style={styles.summaryItem}>
                    {c.produto.nome} × {c.quantidade}
                  </Text>
                  <Text style={styles.summaryPrice}>
                    {formatCurrency(c.produto.preco * c.quantidade)}
                  </Text>
                </View>
              ))}
              <View style={styles.summaryDivider} />
              <View style={styles.summaryRow}>
                <Text style={styles.summaryTotalLabel}>Total</Text>
                <Text style={styles.summaryTotalValue}>{formatCurrency(cartTotal)}</Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summarySaldoLabel}>Saldo após aprovação</Text>
                <Text
                  style={[
                    styles.summarySaldoValue,
                    saldoPosSaldo < 0 && styles.saldoNegativo,
                  ]}
                >
                  {formatCurrency(saldoPosSaldo)}
                </Text>
              </View>

              <TextInput
                style={styles.obsInput}
                placeholder="Observações (opcional)"
                placeholderTextColor="#C7C7C7"
                value={observacoes}
                onChangeText={setObservacoes}
                multiline
              />

              <TouchableOpacity
                style={[styles.confirmButton, (criando || saldoPosSaldo < 0 || !!todayOrder) && styles.confirmButtonDisabled]}
                onPress={handleConfirm}
                disabled={criando || saldoPosSaldo < 0 || !!todayOrder}
              >
                <Text style={styles.confirmButtonText}>
                  {criando ? "Enviando..." : "Confirmar pedido"}
                </Text>
              </TouchableOpacity>

              {saldoPosSaldo < 0 && (
                <Text style={styles.saldoInsuficiente}>
                  Saldo insuficiente para este pedido.
                </Text>
              )}

              {!!todayOrder && (
                <Text style={styles.avisoHoje}>
                  Já existe um pedido para este aluno hoje. Para montar outro,
                  cancele o pedido atual em "Acompanhar pedido".
                </Text>
              )}
            </View>
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

  studentCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  studentLabel: { fontSize: 13, color: "#7A7A7A" },
  studentName: { fontSize: 18, fontWeight: "700", color: "#1F1F1F", marginTop: 2 },
  saldoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: "#F0F0F0",
  },
  saldoLabel: { fontSize: 14, color: "#7A7A7A" },
  saldoValue: { fontSize: 20, fontWeight: "700", color: "#2ECC71" },

  todayCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  todayHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 12 },
  todayTitle: { fontSize: 16, fontWeight: "600", color: "#1F1F1F" },
  todayInfo: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  todayStatus: { fontSize: 14, color: "#7A7A7A" },
  todayTotal: { fontSize: 16, fontWeight: "700", color: "#1F1F1F" },
  todayButton: {
    marginTop: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: "#FFF0F3",
    borderRadius: 12,
    alignItems: "center",
  },
  todayButtonText: { fontSize: 14, fontWeight: "600", color: "#FF5B8F" },

  emptyTodayCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 24,
    marginBottom: 16,
    alignItems: "center",
  },
  emptyTodayText: { fontSize: 14, color: "#7A7A7A", marginTop: 8, textAlign: "center" },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
    marginTop: 8,
    marginBottom: 12,
  },
  emptyText: { fontSize: 14, color: "#7A7A7A", textAlign: "center", marginBottom: 16 },

  menuItem: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  menuInfo: { flex: 1, marginRight: 12 },
  menuName: { fontSize: 16, fontWeight: "600", color: "#1F1F1F" },
  menuDesc: { fontSize: 13, color: "#7A7A7A", marginTop: 2 },
  menuPrice: { fontSize: 15, fontWeight: "600", color: "#FF5B8F", marginTop: 4 },
  quantityControl: { flexDirection: "row", alignItems: "center", gap: 12 },
  qtyButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#F5F5F7",
    alignItems: "center",
    justifyContent: "center",
  },
  qtyValue: { fontSize: 16, fontWeight: "600", color: "#1F1F1F", minWidth: 20, textAlign: "center" },

  summaryCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginTop: 16,
  },
  summaryTitle: { fontSize: 16, fontWeight: "700", color: "#1F1F1F", marginBottom: 12 },
  summaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 6,
  },
  summaryItem: { fontSize: 14, color: "#333333", flex: 1 },
  summaryPrice: { fontSize: 14, color: "#333333", marginLeft: 8 },
  summaryDivider: { height: 1, backgroundColor: "#F0F0F0", marginVertical: 8 },
  summaryTotalLabel: { fontSize: 16, fontWeight: "700", color: "#1F1F1F" },
  summaryTotalValue: { fontSize: 18, fontWeight: "700", color: "#1F1F1F" },
  summarySaldoLabel: { fontSize: 14, color: "#7A7A7A" },
  summarySaldoValue: { fontSize: 16, fontWeight: "600", color: "#2ECC71" },
  saldoNegativo: { color: "#E74C3C" },

  obsInput: {
    borderWidth: 1,
    borderColor: "#E0E0E0",
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    color: "#1F1F1F",
    marginTop: 12,
    minHeight: 60,
    textAlignVertical: "top",
  },

  confirmButton: {
    backgroundColor: "#FF5B8F",
    borderRadius: 16,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 16,
  },
  confirmButtonDisabled: { opacity: 0.5 },
  confirmButtonText: { fontSize: 16, fontWeight: "700", color: "#FFFFFF" },
  saldoInsuficiente: { fontSize: 13, color: "#E74C3C", textAlign: "center", marginTop: 8 },
  avisoHoje: { fontSize: 13, color: "#B7791F", textAlign: "center", marginTop: 8 },
});
