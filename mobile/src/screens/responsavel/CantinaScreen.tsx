import { useState, useCallback, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  RefreshControl,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useWallet } from "../../hooks/useWallet";
import { useTodayOrder, useProgramacaoSemana, useAutonomia, useToggleAutonomia } from "../../hooks/useCantina";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { Programacao } from "../../api/cantina.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Cantina">;

const DIA_LABELS: Record<string, string> = {
  seg: "Seg",
  ter: "Ter",
  qua: "Qua",
  qui: "Qui",
  sex: "Sex",
  sab: "Sab",
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function CantinaScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const { selectedChild } = useSelectedStudent();
  const { saldo, loading: saldoLoading } = useWallet();
  const { pedido: todayOrder, loading: todayLoading, refetch: refetchToday } = useTodayOrder();
  const {
    programacao,
    loading: progLoading,
    error: progError,
    refetch: refetchProg,
  } = useProgramacaoSemana();
  const { autonomia, loading: autonomiaLoading, refetch: refetchAutonomia } = useAutonomia();
  const { toggle: toggleAutonomia, loading: toggling } = useToggleAutonomia();

  const [refreshing, setRefreshing] = useState(false);

  const sortedProgramacoes = useMemo(() => {
    if (!programacao?.programacoes) return [];
    const order = ["seg", "ter", "qua", "qui", "sex", "sab"];
    return [...programacao.programacoes].sort(
      (a, b) => order.indexOf(a.dia_semana) - order.indexOf(b.dia_semana),
    );
  }, [programacao]);

  useFocusEffect(
    useCallback(() => {
      refetchToday();
      refetchProg();
      refetchAutonomia();
    }, [refetchToday, refetchProg, refetchAutonomia]),
  );

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchToday(), refetchProg(), refetchAutonomia()]);
    setRefreshing(false);
  }, [refetchToday, refetchProg, refetchAutonomia]);

  if (!selectedChild) {
    return (
      <View style={styles.container}>
        <ErrorState message="Nenhum aluno selecionado." />
      </View>
    );
  }

  if (todayLoading || saldoLoading || progLoading) {
    return (
      <View style={styles.container}>
        <LoadingState />
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
          <Text style={styles.headerTitle}>Cantina</Text>
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
            {selectedChild.turma_codigo && (
              <Text style={styles.studentTurma}>{selectedChild.turma_codigo}</Text>
            )}
            <View style={styles.saldoRow}>
              <Text style={styles.saldoLabel}>Saldo disponível</Text>
              <Text style={styles.saldoValue}>{formatCurrency(saldo || 0)}</Text>
            </View>
          </View>

          {/* Autonomia Toggle */}
          <View style={styles.autonomiaCard}>
            <View style={styles.autonomiaInfo}>
              <ThemedIcon name="school-outline" size={20} color="#FF5B8F" />
              <View style={styles.autonomiaTextContainer}>
                <Text style={styles.autonomiaTitle}>Autonomia na Cantina</Text>
                <Text style={styles.autonomiaSubtitle}>
                  Permitir que {selectedChild.aluno_nome} escolha o próprio lanche
                </Text>
              </View>
            </View>
            <TouchableOpacity
              style={[styles.autonomiaToggle, autonomia && styles.autonomiaToggleActive]}
              onPress={() => {
                if (selectedChild) {
                  toggleAutonomia(selectedChild.aluno_id, !autonomia).then(() => {
                    refetchAutonomia();
                  });
                }
              }}
              disabled={toggling || autonomiaLoading}
            >
              <View style={[styles.autonomiaKnob, autonomia && styles.autonomiaKnobActive]} />
            </TouchableOpacity>
          </View>

          {/* Montar lanche de hoje - CTA Principal */}
          <TouchableOpacity
            style={styles.ctaButton}
            onPress={() => navigation.navigate("MontarLanche")}
          >
            <View style={styles.ctaIcon}>
              <ThemedIcon name="restaurant-outline" size={28} color="#FFFFFF" />
            </View>
            <View style={styles.ctaContent}>
              <Text style={styles.ctaTitle}>Montar lanche de hoje</Text>
              <Text style={styles.ctaSubtitle}>
                {todayOrder
                  ? `Pedido #${String(todayOrder.id).slice(0, 8)} — ${todayOrder.status}`
                  : "Escolha seus itens e confirme o pedido"}
              </Text>
            </View>
            <ThemedIcon name="chevron-forward" size={24} color="#FFFFFF" />
          </TouchableOpacity>

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

          {/* Programação semanal */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Programação semanal</Text>
            <View style={styles.sectionActions}>
              <TouchableOpacity
                style={styles.sectionAction}
                onPress={() => navigation.navigate("PedidoHistorico")}
              >
                <ThemedIcon name="time-outline" size={18} color="#7A7A7A" />
                <Text style={styles.sectionActionTextGrey}>Histórico</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.sectionAction}
                onPress={() => navigation.navigate("PersonalizarSemana")}
              >
                <ThemedIcon name="create-outline" size={18} color="#FF5B8F" />
                <Text style={styles.sectionActionText}>Personalizar</Text>
              </TouchableOpacity>
            </View>
          </View>

          {progError ? (
            <View style={styles.emptyProgCard}>
              <ThemedIcon name="alert-circle-outline" size={32} color="#FF6B6B" />
              <Text style={[styles.emptyProgText, { color: "#FF6B6B" }]}>{progError}</Text>
            </View>
          ) : sortedProgramacoes.length === 0 ? (
            <View style={styles.emptyProgCard}>
              <ThemedIcon name="calendar-outline" size={32} color="#C7C7C7" />
              <Text style={styles.emptyProgText}>
                Nenhuma programação para esta semana.
              </Text>
              <TouchableOpacity
                style={styles.emptyProgButton}
                onPress={() => navigation.navigate("PersonalizarSemana")}
              >
                <Text style={styles.emptyProgButtonText}>Criar programação</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.progGrid}>
              {(["seg", "ter", "qua", "qui", "sex", "sab"] as const).map((dia) => {
                const prog = sortedProgramacoes.find((p) => p.dia_semana === dia);
                const hasItems = prog && prog.itens.length > 0;
                return (
                  <TouchableOpacity
                    key={dia}
                    style={[styles.progDayCard, hasItems && styles.progDayCardActive]}
                    onPress={() =>
                      navigation.navigate("PersonalizarSemana", { diaSemana: dia })
                    }
                  >
                    <Text
                      style={[styles.progDayLabel, hasItems && styles.progDayLabelActive]}
                    >
                      {DIA_LABELS[dia]}
                    </Text>
                    {hasItems ? (
                      <View style={styles.progDayItems}>
                        {prog!.itens.slice(0, 2).map((item) => (
                          <Text
                            key={item.id}
                            style={[styles.progDayItem, hasItems && styles.progDayItemActive]}
                            numberOfLines={1}
                          >
                            {item.quantidade}× {item.produto_nome || "Item"}
                          </Text>
                        ))}
                        {prog!.itens.length > 2 && (
                          <Text
                            style={[styles.progDayMore, hasItems && styles.progDayMoreActive]}
                          >
                            +{prog!.itens.length - 2} mais
                          </Text>
                        )}
                      </View>
                    ) : (
                      <View style={styles.progDayEmpty}>
                        <ThemedIcon name="add-circle-outline" size={18} color="#C7C7C7" />
                      </View>
                    )}
                  </TouchableOpacity>
                );
              })}
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
  studentTurma: { fontSize: 14, color: "#7A7A7A", marginTop: 2 },
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

  // Autonomia Toggle
  autonomiaCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  autonomiaInfo: { flexDirection: "row", alignItems: "center", gap: 12, flex: 1 },
  autonomiaTextContainer: { flex: 1 },
  autonomiaTitle: { fontSize: 15, fontWeight: "600", color: "#1F1F1F" },
  autonomiaSubtitle: { fontSize: 12, color: "#7A7A7A", marginTop: 2 },
  autonomiaToggle: {
    width: 52,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#E0E0E0",
    justifyContent: "center",
    paddingHorizontal: 3,
  },
  autonomiaToggleActive: { backgroundColor: "#FF5B8F" },
  autonomiaKnob: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: "#FFFFFF",
    alignSelf: "flex-start",
  },
  autonomiaKnobActive: { alignSelf: "flex-end" },

  // CTA Button
  ctaButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FF5B8F",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
    gap: 14,
  },
  ctaIcon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  ctaContent: { flex: 1 },
  ctaTitle: { fontSize: 17, fontWeight: "700", color: "#FFFFFF" },
  ctaSubtitle: { fontSize: 13, color: "rgba(255,255,255,0.8)", marginTop: 2 },

  // Today order
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

  // Section header
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
    marginBottom: 12,
  },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: "#1F1F1F" },
  sectionActions: { flexDirection: "row", alignItems: "center", gap: 12 },
  sectionAction: { flexDirection: "row", alignItems: "center", gap: 4 },
  sectionActionText: { fontSize: 14, fontWeight: "600", color: "#FF5B8F" },
  sectionActionTextGrey: { fontSize: 14, fontWeight: "600", color: "#7A7A7A" },

  // Empty programacao
  emptyProgCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 24,
    alignItems: "center",
  },
  emptyProgText: { fontSize: 14, color: "#7A7A7A", marginTop: 8, textAlign: "center" },
  emptyProgButton: {
    marginTop: 16,
    paddingVertical: 10,
    paddingHorizontal: 20,
    backgroundColor: "#FFF0F3",
    borderRadius: 12,
  },
  emptyProgButtonText: { fontSize: 14, fontWeight: "600", color: "#FF5B8F" },

  // Programacao grid
  progGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  progDayCard: {
    width: "31%",
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 12,
    minHeight: 80,
  },
  progDayCardActive: {
    backgroundColor: "#FFF0F3",
    borderWidth: 1,
    borderColor: "#FF5B8F",
  },
  progDayLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: "#7A7A7A",
    marginBottom: 6,
  },
  progDayLabelActive: { color: "#FF5B8F" },
  progDayItems: { gap: 2 },
  progDayItem: { fontSize: 11, color: "#7A7A7A" },
  progDayItemActive: { color: "#1F1F1F" },
  progDayMore: { fontSize: 10, color: "#C7C7C7", marginTop: 2 },
  progDayMoreActive: { color: "#FF5B8F" },
  progDayEmpty: { flex: 1, alignItems: "center", justifyContent: "center" },
});
