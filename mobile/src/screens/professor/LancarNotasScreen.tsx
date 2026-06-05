import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  SafeAreaView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  getTurmaAlunos,
  getProfessorAvaliacoes,
  getAssessmentGrades,
  saveNotas,
  type ProfessorAluno,
  type ProfessorAvaliacao,
} from "../../api/teacher.service";
import { ErrorState } from "../../components/ErrorState";
import type { ProfessorStackParamList } from "../../types/navigation";

type ScreenRoute = RouteProp<ProfessorStackParamList, "LancarNotas">;

type AlunoNota = ProfessorAluno & { valor: string };

export function LancarNotasScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<ProfessorStackParamList>>();
  const route = useRoute<ScreenRoute>();
  const { turmaNome, disciplinaNome, turmaId, alocacaoId } = route.params;

  const [avaliacoes, setAvaliacoes] = useState<ProfessorAvaliacao[]>([]);
  const [selectedAvaliacaoId, setSelectedAvaliacaoId] = useState<string | null>(null);
  const [alunos, setAlunos] = useState<AlunoNota[]>([]);
  const [loadingAvaliacoes, setLoadingAvaliacoes] = useState(true);
  const [loadingAlunos, setLoadingAlunos] = useState(true);
  const [loadingGrades, setLoadingGrades] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDados = useCallback(async () => {
    setLoadingAvaliacoes(true);
    setLoadingAlunos(true);
    setError(null);
    try {
      const [avals, alns] = await Promise.all([
        getProfessorAvaliacoes(alocacaoId),
        getTurmaAlunos(turmaId),
      ]);
      setAvaliacoes(avals);
      setAlunos(alns.map((a) => ({ ...a, valor: "" })));
      if (avals.length > 0) {
        setSelectedAvaliacaoId(avals[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao carregar dados";
      setError(msg);
    } finally {
      setLoadingAvaliacoes(false);
      setLoadingAlunos(false);
    }
  }, [alocacaoId, turmaId]);

  useEffect(() => {
    fetchDados();
  }, [fetchDados]);

  useEffect(() => {
    if (!selectedAvaliacaoId) return;

    let cancelled = false;
    setLoadingGrades(true);

    (async () => {
      try {
        const existing = await getAssessmentGrades(selectedAvaliacaoId);
        if (cancelled) return;
        setAlunos((prev) =>
          prev.map((a) => {
            const nota = existing.notas.find(
              (n) => n.matricula_id === a.matricula_id
            );
            return {
              ...a,
              valor:
                nota !== undefined && nota.valor > 0
                  ? String(nota.valor)
                  : "",
            };
          })
        );
      } catch {
        if (cancelled) return;
      } finally {
        if (!cancelled) setLoadingGrades(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedAvaliacaoId]);

  const handleNotaChange = (matriculaId: string, value: string) => {
    const cleaned = value.replace(",", ".");
    if (cleaned === "" || /^\d*\.?\d{0,2}$/.test(cleaned)) {
      const num = parseFloat(cleaned);
      if (cleaned === "" || num <= 10) {
        setAlunos((prev) =>
          prev.map((a) =>
            a.matricula_id === matriculaId ? { ...a, valor: cleaned } : a
          )
        );
      }
    }
  };

  const handleSave = async () => {
    if (!selectedAvaliacaoId) {
      Alert.alert("Aviso", "Selecione uma avaliação");
      return;
    }

    const notifyHasEmpty = alunos.some((a) => a.valor === "");
    if (notifyHasEmpty) {
      Alert.alert(
        "Notas incompletas",
        "Alguns alunos ainda não têm nota. Deseja continuar?",
        [
          { text: "Revisar", style: "cancel" },
          {
            text: "Salvar mesmo assim",
            onPress: () => confirmSave(),
          },
        ]
      );
    } else {
      confirmSave();
    }
  };

  const confirmSave = async () => {
    if (!selectedAvaliacaoId) return;
    setSaving(true);
    try {
      await saveNotas(
        selectedAvaliacaoId,
        alunos.map((a) => ({
          matricula_id: a.matricula_id,
          valor: a.valor === "" ? 0 : parseFloat(a.valor),
        }))
      );
      Alert.alert("Sucesso", "Notas salvas com sucesso!", [
        { text: "OK", onPress: () => navigation.goBack() },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao salvar notas";
      Alert.alert("Erro", msg);
    } finally {
      setSaving(false);
    }
  };

  const selectedAvaliacao = avaliacoes.find((a) => a.id === selectedAvaliacaoId);

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
              <Ionicons name="arrow-back" size={24} color="#1F1F1F" />
            </TouchableOpacity>
            <View style={styles.headerInfo}>
              <Text style={styles.headerTitle}>Lançar Notas</Text>
              <Text style={styles.headerSubtitle}>
                {turmaNome} · {disciplinaNome}
              </Text>
            </View>
          </View>
          <ErrorState message={error} onRetry={fetchDados} />
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <View style={styles.header}>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              accessibilityLabel="Voltar"
              accessibilityRole="button"
            >
              <Ionicons name="arrow-back" size={24} color="#1F1F1F" />
            </TouchableOpacity>
            <View style={styles.headerInfo}>
              <Text style={styles.headerTitle}>Lançar Notas</Text>
              <Text style={styles.headerSubtitle}>
                {turmaNome} · {disciplinaNome}
              </Text>
            </View>
          </View>

          {loadingAvaliacoes ? (
            <View style={styles.center}>
              <ActivityIndicator size="large" color="#FF5B8F" />
            </View>
          ) : (
            <>
              <View style={styles.avaliacaoSelector}>
                <Text style={styles.avaliacaoLabel}>Avaliação</Text>
                <FlatList
                  horizontal
                  data={avaliacoes}
                  keyExtractor={(item) => item.id}
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={{ gap: 8 }}
                  renderItem={({ item }) => (
                    <TouchableOpacity
                      style={[
                        styles.avaliacaoChip,
                        item.id === selectedAvaliacaoId && styles.avaliacaoChipActive,
                      ]}
                      onPress={() => setSelectedAvaliacaoId(item.id)}
                      accessibilityLabel={`${item.titulo} - ${item.bimestre}º bimestre`}
                      accessibilityRole="button"
                    >
                      <Text
                        style={[
                          styles.avaliacaoChipText,
                          item.id === selectedAvaliacaoId &&
                            styles.avaliacaoChipTextActive,
                        ]}
                      >
                        {item.bimestre}º Bim - {item.titulo}
                      </Text>
                    </TouchableOpacity>
                  )}
                  ListEmptyComponent={
                    <Text style={styles.noAvaliacaoText}>
                      Nenhuma avaliação cadastrada
                    </Text>
                  }
                />
              </View>

              {selectedAvaliacao && (
                <View style={styles.avaliacaoInfo}>
                  <Text style={styles.avaliacaoInfoTitle}>
                    {selectedAvaliacao.titulo}
                  </Text>
                  <Text style={styles.avaliacaoInfoDetalhes}>
                    {selectedAvaliacao.tipo} · Peso {selectedAvaliacao.peso} ·{" "}
                    {selectedAvaliacao.bimestre}º Bimestre · Max:{" "}
                    {selectedAvaliacao.nota_maxima}
                  </Text>
                </View>
              )}

              <FlatList
                data={alunos}
                keyExtractor={(item) => item.matricula_id}
                contentContainerStyle={styles.listContent}
                keyboardShouldPersistTaps="handled"
                renderItem={({ item, index }) => (
                  <View style={styles.alunoRow}>
                    <Text style={styles.alunoIndex}>{index + 1}.</Text>
                    <View style={styles.alunoAvatar}>
                      <Text style={styles.alunoAvatarText}>
                        {item.aluno_nome.charAt(0).toUpperCase()}
                      </Text>
                    </View>
                    <Text style={styles.alunoNome} numberOfLines={1}>
                      {item.aluno_nome}
                    </Text>
                    <TextInput
                      style={styles.notaInput}
                      value={item.valor}
                      onChangeText={(t) =>
                        handleNotaChange(item.matricula_id, t)
                      }
                      keyboardType="decimal-pad"
                      placeholder="0.0"
                      placeholderTextColor="#C7C7C7"
                      maxLength={5}
                      accessibilityLabel={`Nota para ${item.aluno_nome}`}
                      accessibilityRole="none"
                    />
                  </View>
                )}
              />

              <View style={styles.footer}>
                <TouchableOpacity
                  style={[styles.saveButton, saving && styles.saveButtonDisabled]}
                  onPress={handleSave}
                  disabled={saving}
                  activeOpacity={0.8}
                  accessibilityLabel="Salvar notas"
                  accessibilityRole="button"
                >
                  {saving ? (
                    <ActivityIndicator color="#FFF" size="small" />
                  ) : (
                    <>
                      <Ionicons name="save-outline" size={20} color="#FFF" />
                      <Text style={styles.saveButtonText}>Salvar Notas</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </>
          )}
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
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
  avaliacaoSelector: {
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  avaliacaoLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#888",
    marginBottom: 8,
  },
  avaliacaoChip: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1.5,
    borderColor: "#E5E5E5",
  },
  avaliacaoChipActive: {
    backgroundColor: "#FF5B8F",
    borderColor: "#FF5B8F",
  },
  avaliacaoChipText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#666",
  },
  avaliacaoChipTextActive: {
    color: "#FFF",
  },
  noAvaliacaoText: {
    fontSize: 13,
    color: "#888",
    fontStyle: "italic",
  },
  avaliacaoInfo: {
    paddingHorizontal: 24,
    paddingVertical: 8,
    marginBottom: 4,
  },
  avaliacaoInfoTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  avaliacaoInfoDetalhes: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
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
    padding: 10,
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
    marginRight: 10,
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
  notaInput: {
    backgroundColor: "#F5F5F7",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 8,
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
    width: 72,
    textAlign: "center",
    borderWidth: 1,
    borderColor: "#E5E5E5",
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
