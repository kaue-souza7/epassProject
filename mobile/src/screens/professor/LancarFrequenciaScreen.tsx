import { getApiErrorMessage } from "../../api/errors";
import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { format, parseISO } from "date-fns";
import { getTurmaAlunos, saveFrequencia, type ProfessorAluno } from "../../api/teacher.service";
import { listCalls, getCall } from "../../api/attendance.service";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../components/Toast";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type ScreenRoute = RouteProp<ProfessorStackParamList, "LancarFrequencia">;

type AlunoEstado = ProfessorAluno & { presente: boolean };

export function LancarFrequenciaScreen() {
  useThemeVersion();

  const navigation = useNavigation();
  const route = useRoute<ScreenRoute>();
  const toast = useToast();
  const { turmaNome, disciplinaNome, turmaId, alocacaoId } = route.params;

  const today = format(new Date(), "yyyy-MM-dd");
  const [selectedDate, setSelectedDate] = useState(today);
  const [alunos, setAlunos] = useState<AlunoEstado[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlunos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [alunosData, callsData] = await Promise.all([
        getTurmaAlunos(turmaId),
        listCalls(alocacaoId),
      ]);

      const chamadaHoje = callsData.items.find((c) =>
        c.data_hora_aula.startsWith(selectedDate)
      );

      if (chamadaHoje) {
        const detalhe = await getCall(chamadaHoje.id);
        const statusMap: Record<string, boolean> = {};
        for (const f of detalhe.frequencias) {
          statusMap[f.matricula_id] = f.status === "presente";
        }
        setAlunos(
          alunosData.map((a) => ({
            ...a,
            presente: statusMap[a.matricula_id] ?? true,
          }))
        );
      } else {
        setAlunos(alunosData.map((a) => ({ ...a, presente: true })));
      }
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Erro ao carregar dados");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [turmaId, alocacaoId, selectedDate]);

  useEffect(() => {
    fetchAlunos();
  }, [fetchAlunos]);

  const togglePresenca = (matriculaId: string) => {
    setAlunos((prev) =>
      prev.map((a) =>
        a.matricula_id === matriculaId ? { ...a, presente: !a.presente } : a
      )
    );
  };

  const marcarTodosPresentes = () => {
    setAlunos((prev) => prev.map((a) => ({ ...a, presente: true })));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveFrequencia(
        turmaId,
        selectedDate,
        alunos.map((a) => ({
          matricula_id: a.matricula_id,
          presente: a.presente,
        }))
      );
      toast.success("Frequência salva com sucesso!");
      setTimeout(() => navigation.goBack(), 900);
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Erro ao salvar frequência");
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const changeDay = (delta: number) => {
    const current = parseISO(selectedDate);
    const next = new Date(current);
    next.setDate(next.getDate() + delta);
    setSelectedDate(format(next, "yyyy-MM-dd"));
  };

  const presencas = alunos.filter((a) => a.presente).length;
  const faltas = alunos.length - presencas;

  if (loading) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
          </View>
        </SafeAreaView>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              accessibilityLabel="Voltar"
              accessibilityRole="button"
            >
              <ThemedIcon name="arrow-back" size={24} color="#1F1F1F" />
            </TouchableOpacity>
            <View style={styles.headerInfo}>
              <Text style={styles.headerTitle}>Lançar Chamada</Text>
              <Text style={styles.headerSubtitle}>
                {turmaNome} · {disciplinaNome}
              </Text>
            </View>
          </View>
          <ErrorState message={error} onRetry={fetchAlunos} />
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            accessibilityLabel="Voltar"
            accessibilityRole="button"
          >
            <ThemedIcon name="arrow-back" size={24} color="#1F1F1F" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>Lançar Chamada</Text>
            <Text style={styles.headerSubtitle}>
              {turmaNome} · {disciplinaNome}
            </Text>
          </View>
        </View>

        <View style={styles.dateSelector}>
          <TouchableOpacity
            onPress={() => changeDay(-1)}
            accessibilityLabel="Dia anterior"
            accessibilityRole="button"
          >
            <ThemedIcon name="chevron-back" size={22} color="#FF5B8F" />
          </TouchableOpacity>

          <View style={styles.dateInfo}>
            <ThemedIcon name="calendar-outline" size={18} color="#FF5B8F" />
            <Text style={styles.dateText}>
              {format(parseISO(selectedDate), "dd/MM/yyyy")}
            </Text>
          </View>

          <TouchableOpacity
            onPress={() => changeDay(1)}
            accessibilityLabel="Próximo dia"
            accessibilityRole="button"
          >
            <ThemedIcon name="chevron-forward" size={22} color="#FF5B8F" />
          </TouchableOpacity>
        </View>

        <View style={styles.resumo}>
          <View style={styles.resumoItem}>
            <Text style={styles.resumoPresenca}>{presencas}</Text>
            <Text style={styles.resumoLabel}>Presentes</Text>
          </View>
          <View style={styles.resumoItem}>
            <Text style={styles.resumoFalta}>{faltas}</Text>
            <Text style={styles.resumoLabel}>Ausentes</Text>
          </View>
          <TouchableOpacity
            style={styles.marcarTodosBtn}
            onPress={marcarTodosPresentes}
            accessibilityLabel="Marcar todos como presente"
            accessibilityRole="button"
          >
            <ThemedIcon name="checkmark-done" size={18} color="#FF5B8F" />
            <Text style={styles.marcarTodosText}>Todos</Text>
          </TouchableOpacity>
        </View>

        <FlatList
          data={alunos}
          keyExtractor={(item) => item.matricula_id}
          contentContainerStyle={styles.listContent}
          renderItem={({ item, index }) => (
            <TouchableOpacity
              style={styles.alunoRow}
              onPress={() => togglePresenca(item.matricula_id)}
              activeOpacity={0.7}
              accessibilityLabel={`${item.aluno_nome}. Toque para alternar presença`}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: item.presente }}
            >
              <Text style={styles.alunoIndex}>{index + 1}.</Text>
              <View style={styles.alunoAvatar}>
                <Text style={styles.alunoAvatarText}>
                  {item.aluno_nome.charAt(0).toUpperCase()}
                </Text>
              </View>
              <Text style={styles.alunoNome} numberOfLines={1}>
                {item.aluno_nome}
              </Text>
              <View
                style={[
                  styles.statusBadge,
                  item.presente ? styles.statusPresente : styles.statusFalta,
                ]}
              >
                <ThemedIcon
                  name={item.presente ? "checkmark" : "close"}
                  size={16}
                  color={item.presente ? "#FFF" : "#FFF"}
                />
                <Text style={styles.statusText}>
                  {item.presente ? "Presente" : "Ausente"}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />

        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.saveButton, saving && styles.saveButtonDisabled]}
            onPress={handleSave}
            disabled={saving}
            activeOpacity={0.8}
            accessibilityLabel="Salvar frequência"
            accessibilityRole="button"
          >
            {saving ? (
              <ActivityIndicator color="#FFF" size="small" />
            ) : (
              <>
                <ThemedIcon name="save-outline" size={20} color="#FFF" />
                <Text style={styles.saveButtonText}>Salvar Frequência</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F7",
  },
  safeArea: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 8,
    gap: 16,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  headerSubtitle: {
    fontSize: 13,
    color: "#888",
    marginTop: 2,
  },
  dateSelector: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 20,
    paddingVertical: 16,
    marginHorizontal: 24,
    backgroundColor: "#FFF",
    borderRadius: 16,
    marginBottom: 12,
  },
  dateInfo: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  dateText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  resumo: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 24,
    gap: 16,
    marginBottom: 12,
  },
  resumoItem: {
    backgroundColor: "#FFF",
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 10,
    alignItems: "center",
    flex: 1,
  },
  resumoPresenca: {
    fontSize: 20,
    fontWeight: "700",
    color: "#4CAF50",
  },
  resumoFalta: {
    fontSize: 20,
    fontWeight: "700",
    color: "#F44336",
  },
  resumoLabel: {
    fontSize: 11,
    color: "#888",
    fontWeight: "500",
    marginTop: 2,
  },
  marcarTodosBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF0F3",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 4,
  },
  marcarTodosText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#FF5B8F",
  },
  listContent: {
    paddingHorizontal: 24,
    paddingBottom: 100,
  },
  alunoRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 12,
    marginBottom: 6,
  },
  alunoIndex: {
    fontSize: 12,
    fontWeight: "500",
    color: "#B0B0B0",
    width: 24,
  },
  alunoAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },
  alunoAvatarText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#FF5B8F",
  },
  alunoNome: {
    flex: 1,
    fontSize: 14,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 6,
    gap: 4,
  },
  statusPresente: {
    backgroundColor: "#4CAF50",
  },
  statusFalta: {
    backgroundColor: "#F44336",
  },
  statusText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#FFF",
  },
  footer: {
    position: "absolute",
    left: 24,
    right: 24,
    bottom: 32,
  },
  saveButton: {
    backgroundColor: "#FF5B8F",
    borderRadius: 28,
    paddingVertical: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    shadowColor: "#FF5B8F",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  saveButtonDisabled: {
    opacity: 0.7,
  },
  saveButtonText: {
    color: "#FFF",
    fontSize: 16,
    fontWeight: "700",
  },
});
