import { useState, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  SafeAreaView,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { LinearGradient } from "expo-linear-gradient";
import { getProfessorTurmas, type ProfessorTurma } from "../../api/teacher.service";
import { ErrorState } from "../../components/ErrorState";
import type { ProfessorStackParamList } from "../../types/navigation";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;

function SkeletonTurmaCard() {
  return (
    <View style={styles.turmaCard}>
      <View style={styles.turmaGradSkeleton}>
        <View style={[styles.skeletonBlock, { width: "60%", height: 20, borderRadius: 4 }]} />
        <View style={[styles.skeletonBlock, { width: "40%", height: 14, borderRadius: 4, marginTop: 8 }]} />
      </View>
      <View style={styles.turmaAcoes}>
        <View style={[styles.skeletonBlock, { width: 80, height: 32, borderRadius: 16 }]} />
        <View style={[styles.skeletonBlock, { width: 80, height: 32, borderRadius: 16 }]} />
      </View>
    </View>
  );
}

export function ProfessorModulosScreen() {
  const navigation = useNavigation<NavProp>();
  const [turmas, setTurmas] = useState<ProfessorTurma[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTurmas = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await getProfessorTurmas();
      setTurmas(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao carregar turmas";
      setError(msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchTurmas();
    }, [fetchTurmas])
  );

  if (loading) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScrollView contentContainerStyle={styles.scrollContent}>
            <View style={[styles.skeletonBlock, { width: "40%", height: 20, borderRadius: 4, marginBottom: 16 }]} />
            <SkeletonTurmaCard />
            <View style={{ height: 12 }} />
            <SkeletonTurmaCard />
            <View style={{ height: 12 }} />
            <SkeletonTurmaCard />
          </ScrollView>
        </SafeAreaView>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <Text style={styles.screenTitle}>Módulos</Text>
          </View>
          <ErrorState message={error} onRetry={() => fetchTurmas()} />
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchTurmas(true)}
              tintColor="#FF5B8F"
            />
          }
        >
          <Text style={styles.screenTitle}>Módulos</Text>
          <Text style={styles.screenSubtitle}>
            Selecione uma turma para lançar frequência ou notas
          </Text>

          {turmas.length === 0 && (
            <View style={styles.emptyState}>
              <Ionicons name="school-outline" size={48} color="#D0D0D0" />
              <Text style={styles.emptyTitle}>Nenhuma turma encontrada</Text>
              <Text style={styles.emptySubtitle}>
                Você não está alocado em nenhuma turma neste período.
              </Text>
            </View>
          )}

          {turmas.map((turma) => (
            <View key={turma.alocacao_id} style={styles.turmaCard}>
              <LinearGradient
                colors={["#F84F8D", "#FF8664"]}
                start={{ x: 0, y: 0.5 }}
                end={{ x: 1, y: 0.5 }}
                style={styles.turmaGradient}
              >
                <View style={styles.turmaCardContent}>
                  <View style={styles.turmaInfo}>
                    <Text style={styles.turmaNome}>
                      {turma.turma_codigo} {turma.turma_nome ?? ""}
                    </Text>
                    <Text style={styles.turmaDisciplina}>
                      {turma.disciplina_nome}
                    </Text>
                    <Text style={styles.turmaDetalhes}>
                      {turma.serie_nome} · {turma.turno} · {turma.ano_letivo}
                    </Text>
                  </View>
                  <View style={styles.turmaAlunosBadge}>
                    <Text style={styles.turmaAlunosCount}>
                      {turma.total_alunos}
                    </Text>
                    <Text style={styles.turmaAlunosLabel}>alunos</Text>
                  </View>
                </View>
              </LinearGradient>

              <View style={styles.turmaAcoes}>
                <TouchableOpacity
                  style={styles.acaoButton}
                  onPress={() =>
                    navigation.navigate("LancarFrequencia", {
                      turmaId: turma.turma_id,
                      turmaNome: turma.turma_codigo,
                      disciplinaNome: turma.disciplina_nome,
                      alocacaoId: turma.alocacao_id,
                    })
                  }
                  accessibilityLabel="Lançar chamada"
                  accessibilityRole="button"
                >
                  <Ionicons name="calendar" size={16} color="#FF5B8F" />
                  <Text style={styles.acaoText}>Chamada</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.acaoButton}
                  onPress={() =>
                    navigation.navigate("LancarNotas", {
                      turmaId: turma.turma_id,
                      turmaNome: turma.turma_codigo,
                      disciplinaNome: turma.disciplina_nome,
                      alocacaoId: turma.alocacao_id,
                    })
                  }
                  accessibilityLabel="Lançar notas"
                  accessibilityRole="button"
                >
                  <Ionicons name="document-text" size={16} color="#FF5B8F" />
                  <Text style={styles.acaoText}>Notas</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))}

          <View style={{ height: 100 }} />
        </ScrollView>
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
  header: {
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  },
  screenTitle: {
    fontSize: 34,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  screenSubtitle: {
    fontSize: 14,
    color: "#888",
    marginTop: 4,
    marginBottom: 20,
  },
  turmaCard: {
    backgroundColor: "#FFF",
    borderRadius: 24,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
    overflow: "hidden",
  },
  turmaGradient: {
    padding: 20,
  },
  turmaGradSkeleton: {
    padding: 20,
  },
  turmaCardContent: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  turmaInfo: {
    flex: 1,
  },
  turmaNome: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FFF",
  },
  turmaDisciplina: {
    fontSize: 14,
    color: "rgba(255,255,255,0.9)",
    marginTop: 4,
    fontWeight: "500",
  },
  turmaDetalhes: {
    fontSize: 12,
    color: "rgba(255,255,255,0.7)",
    marginTop: 4,
  },
  turmaAlunosBadge: {
    backgroundColor: "rgba(255,255,255,0.2)",
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
    alignItems: "center",
    minWidth: 56,
  },
  turmaAlunosCount: {
    fontSize: 22,
    fontWeight: "700",
    color: "#FFF",
  },
  turmaAlunosLabel: {
    fontSize: 10,
    color: "rgba(255,255,255,0.8)",
    fontWeight: "500",
  },
  turmaAcoes: {
    flexDirection: "row",
    paddingHorizontal: 20,
    paddingVertical: 12,
    gap: 12,
  },
  acaoButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF0F3",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 6,
  },
  acaoText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FF5B8F",
  },
  skeletonBlock: {
    backgroundColor: "#E5E5E5",
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 48,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
    marginTop: 12,
  },
  emptySubtitle: {
    fontSize: 13,
    color: "#888",
    textAlign: "center",
    marginTop: 6,
    paddingHorizontal: 24,
  },
});
