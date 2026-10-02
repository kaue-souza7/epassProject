import { useState, useCallback, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useNavigation, useRoute, useFocusEffect } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { RouteProp } from "@react-navigation/native";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useMenu } from "../../hooks/useCantina";
import {
  useProgramacaoSemana,
  useSaveProgramacao,
  useDeleteProgramacao,
} from "../../hooks/useCantina";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../components/Toast";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { MenuItem } from "../../api/cantina.service";
import type { Programacao, DiaSemana, ProgramacaoItemCreate } from "../../api/cantina.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "PersonalizarSemana">;
type RouteProps = RouteProp<ResponsavelStackParamList, "PersonalizarSemana">;

const DIAS: { key: DiaSemana; label: string; short: string }[] = [
  { key: "seg", label: "Segunda-feira", short: "SEG" },
  { key: "ter", label: "Terça-feira", short: "TER" },
  { key: "qua", label: "Quarta-feira", short: "QUA" },
  { key: "qui", label: "Quinta-feira", short: "QUI" },
  { key: "sex", label: "Sexta-feira", short: "SEX" },
  { key: "sab", label: "Sábado", short: "SAB" },
];

interface DayItems {
  [key: string]: ProgramacaoItemCreate[];
}

export function PersonalizarSemanaScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const toast = useToast();
  const route = useRoute<RouteProps>();
  const { selectedChild } = useSelectedStudent();
  const { data: menu, loading: menuLoading, refetch: refetchMenu } = useMenu();
  const { programacao, loading: progLoading, refetch: refetchProg } = useProgramacaoSemana();
  const { salvar, loading: saving } = useSaveProgramacao();
  const { remover, loading: deleting } = useDeleteProgramacao();

  const [selectedDay, setSelectedDay] = useState<DiaSemana>(
    (route.params?.diaSemana as DiaSemana) || "seg",
  );
  const [dayItems, setDayItems] = useState<DayItems>({});
  const [generalItems, setGeneralItems] = useState<ProgramacaoItemCreate[]>([]);
  const [isGeneral, setIsGeneral] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const availableMenu = (menu || []).filter((m) => m.disponivel);

  // Load existing programacao into local state
  useFocusEffect(
    useCallback(() => {
      refetchProg();
      refetchMenu();
    }, [refetchProg, refetchMenu]),
  );

  useEffect(() => {
    if (!programacao?.programacoes) return;
    const items: DayItems = {};
    let geral: ProgramacaoItemCreate[] = [];
    let hasGeral = false;
    for (const prog of programacao.programacoes) {
      const mapped = prog.itens.map((i) => ({
        produto_id: i.produto_id,
        quantidade: i.quantidade,
      }));
      if (prog.tipo === "geral") {
        // A programação GERAL é única por aluno e vale para todos os dias.
        geral = mapped;
        hasGeral = true;
      } else {
        items[prog.dia_semana] = mapped;
      }
    }
    setDayItems(items);
    setGeneralItems(geral);
    setIsGeneral(hasGeral);
  }, [programacao]);

  const currentItems = isGeneral ? generalItems : dayItems[selectedDay] || [];
  const dayLabel = DIAS.find((d) => d.key === selectedDay)?.label || selectedDay;

  const getItemQuantity = useCallback(
    (produtoId: string): number => {
      const found = currentItems.find((i) => i.produto_id === produtoId);
      return found?.quantidade || 0;
    },
    [currentItems],
  );

  const updateItemQuantity = useCallback(
    (produtoId: string, delta: number) => {
      const applyDelta = (base: ProgramacaoItemCreate[]) => {
        const items = [...base];
        const idx = items.findIndex((i) => i.produto_id === produtoId);
        if (idx >= 0) {
          const newQty = items[idx].quantidade + delta;
          if (newQty <= 0) {
            items.splice(idx, 1);
          } else {
            items[idx] = { ...items[idx], quantidade: newQty };
          }
        } else if (delta > 0) {
          items.push({ produto_id: produtoId, quantidade: 1 });
        }
        return items;
      };

      setHasChanges(true);
      if (isGeneral) {
        setGeneralItems((prev) => applyDelta(prev));
      } else {
        setDayItems((prev) => ({
          ...prev,
          [selectedDay]: applyDelta(prev[selectedDay] || []),
        }));
      }
    },
    [selectedDay, isGeneral],
  );

  const handleSave = useCallback(async () => {
    if (!selectedChild) return;

    let allOk = true;

    if (isGeneral) {
      // Uma única programação GERAL por aluno (padrão para todos os dias).
      const geralExistente = programacao?.programacoes.find(
        (p) => p.tipo === "geral",
      );

      if (generalItems.length === 0) {
        if (geralExistente) {
          const ok = await remover(geralExistente.id);
          if (!ok) allOk = false;
        }
      } else {
        const ok = await salvar({
          aluno_id: selectedChild.aluno_id,
          dia_semana: geralExistente?.dia_semana ?? selectedDay,
          tipo: "geral",
          itens: generalItems,
        });
        if (!ok) allOk = false;
      }
    } else {
      const items = dayItems[selectedDay] || [];
      const diariaExistente = programacao?.programacoes.find(
        (p) => p.tipo === "diaria" && p.dia_semana === selectedDay,
      );

      if (items.length === 0) {
        if (diariaExistente) {
          const ok = await remover(diariaExistente.id);
          if (!ok) allOk = false;
        }
      } else {
        const ok = await salvar({
          aluno_id: selectedChild.aluno_id,
          dia_semana: selectedDay,
          tipo: "diaria",
          itens: items,
        });
        if (!ok) allOk = false;
      }
    }

    if (allOk) {
      setHasChanges(false);
      refetchProg();
      toast.success("Programação atualizada com sucesso.");
    } else {
      toast.error("A programação não pôde ser salva. Tente novamente.");
    }
  }, [
    selectedChild,
    selectedDay,
    dayItems,
    generalItems,
    isGeneral,
    programacao,
    salvar,
    remover,
    refetchProg,
    toast,
  ]);

  const handleClearDay = useCallback(() => {
    const alvo = isGeneral ? "todos os dias (GERAL)" : dayLabel;
    Alert.alert(
      "Limpar programação",
      `Remover todos os itens de ${alvo}?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Limpar",
          style: "destructive",
          onPress: () => {
            if (isGeneral) {
              setGeneralItems([]);
            } else {
              setDayItems((prev) => ({ ...prev, [selectedDay]: [] }));
            }
            setHasChanges(true);
          },
        },
      ],
    );
  }, [selectedDay, dayLabel, isGeneral]);

  if (!selectedChild) {
    return (
      <View style={styles.container}>
        <ErrorState message="Nenhum aluno selecionado." />
      </View>
    );
  }

  if (menuLoading || progLoading) {
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
          <Text style={styles.headerTitle}>Personalizar Semana</Text>
          <View style={{ width: 28 }} />
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
        >
          {/* Aluno */}
          <View style={styles.studentCard}>
            <Text style={styles.studentLabel}>Aluno:</Text>
            <Text style={styles.studentName}>{selectedChild.aluno_nome}</Text>
          </View>

          {/* Toggle Diaria/Geral */}
          <View style={styles.toggleCard}>
            <TouchableOpacity
              style={[styles.toggleButton, !isGeneral && styles.toggleActive]}
              onPress={() => {
                setIsGeneral(false);
                setHasChanges(true);
              }}
            >
              <ThemedIcon
                name="calendar-outline"
                size={18}
                color={!isGeneral ? "#FFFFFF" : "#7A7A7A"}
              />
              <Text style={[styles.toggleText, !isGeneral && styles.toggleTextActive]}>
                Diária
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.toggleButton, isGeneral && styles.toggleActive]}
              onPress={() => {
                setIsGeneral(true);
                setHasChanges(true);
              }}
            >
              <ThemedIcon
                name="repeat-outline"
                size={18}
                color={isGeneral ? "#FFFFFF" : "#7A7A7A"}
              />
              <Text style={[styles.toggleText, isGeneral && styles.toggleTextActive]}>
                Geral
              </Text>
            </TouchableOpacity>
          </View>

          {isGeneral && (
            <View style={styles.geralInfo}>
              <ThemedIcon name="information-circle-outline" size={16} color="#7A7A7A" />
              <Text style={styles.geralInfoText}>
                Modo Geral: os itens serão aplicados a todos os dias da semana.
              </Text>
            </View>
          )}

          {/* Day tabs */}
          {!isGeneral && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.dayTabs}
              contentContainerStyle={styles.dayTabsContent}
            >
              {DIAS.map((dia) => {
                const isActive = selectedDay === dia.key;
                const hasItems = (dayItems[dia.key] || []).length > 0;
                return (
                  <TouchableOpacity
                    key={dia.key}
                    style={[styles.dayTab, isActive && styles.dayTabActive]}
                    onPress={() => setSelectedDay(dia.key)}
                  >
                    <Text
                      style={[styles.dayTabText, isActive && styles.dayTabTextActive]}
                    >
                      {dia.short}
                    </Text>
                    {hasItems && <View style={styles.dayTabDot} />}
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          )}

          {/* Day header */}
          <View style={styles.dayHeader}>
            <Text style={styles.dayTitle}>
              {isGeneral ? "Todos os dias" : dayLabel}
            </Text>
            {currentItems.length > 0 && (
              <TouchableOpacity onPress={handleClearDay}>
                <Text style={styles.clearText}>Limpar</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Menu items */}
          {availableMenu.length === 0 ? (
            <Text style={styles.emptyText}>Nenhum produto disponível.</Text>
          ) : (
            availableMenu.map((item) => {
              const qty = getItemQuantity(item.id);
              return (
                <View key={item.id} style={styles.menuItem}>
                  <View style={styles.menuInfo}>
                    <Text style={styles.menuName}>{item.nome}</Text>
                    {item.descricao ? (
                      <Text style={styles.menuDesc}>{item.descricao}</Text>
                    ) : null}
                    <Text style={styles.menuPrice}>
                      {item.preco.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                    </Text>
                  </View>
                  <View style={styles.quantityControl}>
                    <TouchableOpacity
                      style={styles.qtyButton}
                      onPress={() => updateItemQuantity(item.id, -1)}
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
                      onPress={() => updateItemQuantity(item.id, 1)}
                    >
                      <ThemedIcon name="add" size={20} color="#FF5B8F" />
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          )}

          {/* Current items summary */}
          {currentItems.length > 0 && (
            <View style={styles.summaryCard}>
              <Text style={styles.summaryTitle}>
                {isGeneral ? "Itens para todos os dias" : `Itens de ${dayLabel}`}
              </Text>
              {currentItems.map((item) => {
                const produto = availableMenu.find((m) => m.id === item.produto_id);
                return (
                  <View key={item.produto_id} style={styles.summaryRow}>
                    <Text style={styles.summaryItem}>
                      {item.quantidade}× {produto?.nome || "Produto"}
                    </Text>
                  </View>
                );
              })}
            </View>
          )}
        </ScrollView>

        {/* Save button */}
        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.saveButton, (!hasChanges || saving) && styles.saveButtonDisabled]}
            onPress={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <ThemedIcon name="checkmark-circle-outline" size={20} color="#FFFFFF" />
            )}
            <Text style={styles.saveButtonText}>
              {saving ? "Salvando..." : "Salvar programação"}
            </Text>
          </TouchableOpacity>
        </View>
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
  scrollContent: { padding: 20, paddingBottom: 100 },

  studentCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  studentLabel: { fontSize: 13, color: "#7A7A7A" },
  studentName: { fontSize: 18, fontWeight: "700", color: "#1F1F1F", marginTop: 2 },

  toggleCard: {
    flexDirection: "row",
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 4,
    marginBottom: 16,
  },
  toggleButton: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 12,
    borderRadius: 12,
  },
  toggleActive: { backgroundColor: "#FF5B8F" },
  toggleText: { fontSize: 14, fontWeight: "600", color: "#7A7A7A" },
  toggleTextActive: { color: "#FFFFFF" },

  geralInfo: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#FFF8E1",
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  geralInfoText: { fontSize: 13, color: "#7A7A7A", flex: 1 },

  dayTabs: { marginBottom: 16 },
  dayTabsContent: { gap: 8 },
  dayTab: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: "#FFFFFF",
    alignItems: "center",
    minWidth: 56,
  },
  dayTabActive: { backgroundColor: "#FF5B8F" },
  dayTabText: { fontSize: 14, fontWeight: "600", color: "#7A7A7A" },
  dayTabTextActive: { color: "#FFFFFF" },
  dayTabDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#FF5B8F",
    marginTop: 4,
  },

  dayHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  dayTitle: { fontSize: 16, fontWeight: "700", color: "#1F1F1F" },
  clearText: { fontSize: 14, fontWeight: "600", color: "#E74C3C" },

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
    borderRadius: 16,
    padding: 16,
    marginTop: 16,
  },
  summaryTitle: { fontSize: 14, fontWeight: "600", color: "#1F1F1F", marginBottom: 8 },
  summaryRow: { paddingVertical: 4 },
  summaryItem: { fontSize: 14, color: "#333333" },

  footer: {
    padding: 20,
    paddingBottom: 32,
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#F0F0F0",
  },
  saveButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#FF5B8F",
    borderRadius: 16,
    paddingVertical: 14,
  },
  saveButtonDisabled: { opacity: 0.5 },
  saveButtonText: { fontSize: 16, fontWeight: "700", color: "#FFFFFF" },
});
