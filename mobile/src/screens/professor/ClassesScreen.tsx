import { getApiErrorMessage } from "../../api/errors";
import { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  RefreshControl,
  Alert,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { getProfessorTurmas, liberarBoletim, getLiberacaoStatus } from "../../api/teacher.service";
import type { ProfessorTurma } from "../../api/teacher.service";
import { TurmaCard } from "../../components/professor/TurmaCard";
import { ErrorState } from "../../components/ErrorState";
import { ScreenHeader } from "../../components/ScreenHeader";
import { useToast } from "../../components/Toast";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

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

export function ClassesScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const toast = useToast();
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
      const msg = getApiErrorMessage(err, "Erro ao carregar turmas");
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

  const handleLiberar = useCallback((turma: ProfessorTurma) => {
    Alert.alert(
      "Liberar Boletim",
      `Selecione o bimestre para liberar o boletim de ${turma.turma_codigo}:`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "1º Bimestre",
          onPress: () => confirmarLiberacao(turma.turma_id, 1),
        },
        {
          text: "2º Bimestre",
          onPress: () => confirmarLiberacao(turma.turma_id, 2),
        },
        {
          text: "3º Bimestre",
          onPress: () => confirmarLiberacao(turma.turma_id, 3),
        },
        {
          text: "4º Bimestre",
          onPress: () => confirmarLiberacao(turma.turma_id, 4),
        },
      ]
    );
  }, []);

  const confirmarLiberacao = useCallback(
    async (turmaId: string, bimestre: number) => {
      try {
        await liberarBoletim(turmaId, bimestre);
        toast.success(`Boletim liberado para o ${bimestre}º bimestre.`);
      } catch (err: unknown) {
        const msg = getApiErrorMessage(err, "Erro ao liberar boletim");
        toast.error(msg);
      }
    },
    [toast],
  );

  if (loading) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScrollView contentContainerStyle={styles.scrollContent}>
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
          <ScreenHeader title="Minhas Turmas" />
          <ErrorState message={error} onRetry={() => fetchTurmas()} />
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Minhas Turmas" />
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
          <Text style={styles.screenSubtitle}>
            Selecione uma turma para lançar frequência ou notas
          </Text>

          {turmas.length === 0 && (
            <View style={styles.emptyState}>
              <ThemedIcon name="school-outline" size={48} color="#D0D0D0" />
              <Text style={styles.emptyTitle}>Nenhuma turma encontrada</Text>
              <Text style={styles.emptySubtitle}>
                Você não está alocado em nenhuma turma neste período.
              </Text>
            </View>
          )}

          {turmas.map((turma) => (
            <TurmaCard
              key={turma.alocacao_id}
              turma={turma}
              onChamada={() =>
                navigation.navigate("LancarFrequencia", {
                  turmaId: turma.turma_id,
                  turmaNome: turma.turma_codigo,
                  disciplinaNome: turma.disciplina_nome,
                  alocacaoId: turma.alocacao_id,
                })
              }
              onNotas={() =>
                navigation.navigate("LancarNotas", {
                  turmaId: turma.turma_id,
                  turmaNome: turma.turma_codigo,
                  disciplinaNome: turma.disciplina_nome,
                  alocacaoId: turma.alocacao_id,
                })
              }
              onLiberar={() => handleLiberar(turma)}
            />
          ))}

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
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
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
  turmaGradSkeleton: {
    padding: 20,
  },
  turmaAcoes: {
    flexDirection: "row",
    paddingHorizontal: 20,
    paddingVertical: 12,
    gap: 12,
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
