import { getApiErrorMessage } from "../../api/errors";
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
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useAuth } from "../../contexts/AuthContext";
import { getProfessorTurmas, type ProfessorTurma } from "../../api/teacher.service";
import { ErrorState } from "../../components/ErrorState";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;

export function ProfessorResumoScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const { user } = useAuth();
  const [turmas, setTurmas] = useState<ProfessorTurma[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await getProfessorTurmas();
      setTurmas(data);
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Erro ao carregar dados");
      setError(msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetch();
    }, [fetch])
  );

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
          <ErrorState message={error} onRetry={() => fetch()} />
        </SafeAreaView>
      </View>
    );
  }

  const totalAlunos = turmas.reduce((acc, t) => acc + t.total_alunos, 0);

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetch(true)}
              tintColor="#FF5B8F"
            />
          }
        >
          <Text style={styles.headerTitle}>Resumo</Text>

          <LinearGradient
            colors={["#F84F8D", "#FF8664"]}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
            style={styles.heroCard}
          >
            <Text style={styles.heroGreeting}>Olá,</Text>
            <Text style={styles.heroName}>{user?.nome ?? "Professor"}</Text>
            <Text style={styles.heroSub}>Bom dia! Vamos ver sua agenda de hoje.</Text>
          </LinearGradient>

          <View style={styles.statsRow}>
            <View style={[styles.statCard, { backgroundColor: "#FFF0F3" }]}>
              <ThemedIcon name="school" size={22} color="#FF5B8F" />
              <Text style={styles.statValue}>{turmas.length}</Text>
              <Text style={styles.statLabel}>Turmas</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: "#E8F5E9" }]}>
              <ThemedIcon name="people" size={22} color="#4CAF50" />
              <Text style={styles.statValue}>{totalAlunos}</Text>
              <Text style={styles.statLabel}>Alunos</Text>
            </View>
          </View>

          <Text style={styles.sectionTitle}>Turmas</Text>

          {turmas.slice(0, 5).map((turma) => (
            <TouchableOpacity
              key={turma.alocacao_id}
              style={styles.turmaCard}
              activeOpacity={0.7}
              onPress={() =>
                navigation.navigate("TurmaAlunos", {
                  turmaId: turma.turma_id,
                  turmaNome: turma.turma_codigo,
                  disciplinaNome: turma.disciplina_nome,
                  alocacaoId: turma.alocacao_id,
                })
              }
              accessibilityLabel={`Turma ${turma.turma_codigo}`}
              accessibilityRole="button"
            >
              <View style={styles.turmaInfo}>
                <Text style={styles.turmaNome}>
                  {turma.turma_codigo} {turma.turma_nome ?? ""}
                </Text>
                <Text style={styles.turmaDisciplina}>
                  {turma.disciplina_nome}
                </Text>
              </View>
              <View style={styles.turmaBadge}>
                <Text style={styles.turmaBadgeText}>{turma.total_alunos}</Text>
              </View>
            </TouchableOpacity>
          ))}

          {turmas.length > 5 && (
            <TouchableOpacity
              style={styles.verMaisButton}
              onPress={() => navigation.navigate("ClassesList")}
              accessibilityLabel="Ver todas as turmas"
              accessibilityRole="button"
            >
              <Text style={styles.verMaisText}>
                Ver todas as {turmas.length} turmas
              </Text>
              <ThemedIcon name="arrow-forward" size={16} color="#FF5B8F" />
            </TouchableOpacity>
          )}

          <View style={{ height: 100 }} />
        </ScrollView>
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
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  },
  headerTitle: {
    fontSize: 40,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 24,
  },
  heroCard: {
    borderRadius: 40,
    padding: 24,
    marginBottom: 24,
  },
  heroGreeting: {
    fontSize: 16,
    color: "rgba(255,255,255,0.8)",
    fontWeight: "500",
  },
  heroName: {
    fontSize: 26,
    fontWeight: "700",
    color: "#FFF",
    marginTop: 4,
  },
  heroSub: {
    fontSize: 14,
    color: "rgba(255,255,255,0.7)",
    marginTop: 8,
  },
  statsRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    borderRadius: 20,
    padding: 16,
    alignItems: "center",
    gap: 6,
  },
  statValue: {
    fontSize: 28,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  statLabel: {
    fontSize: 13,
    color: "#7A7A7A",
    fontWeight: "500",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 12,
  },
  turmaCard: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  turmaInfo: {
    flex: 1,
  },
  turmaNome: {
    fontSize: 15,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  turmaDisciplina: {
    fontSize: 13,
    color: "#888",
    marginTop: 2,
  },
  turmaBadge: {
    backgroundColor: "#FFF0F3",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  turmaBadgeText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#FF5B8F",
  },
  verMaisButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    gap: 6,
  },
  verMaisText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#FF5B8F",
  },
});
