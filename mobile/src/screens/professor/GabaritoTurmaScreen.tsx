import { getApiErrorMessage } from "../../api/errors";
import { useState, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { getProfessorTurmas, type ProfessorTurma } from "../../api/teacher.service";
import { ScreenHeader } from "../../components/ScreenHeader";
import { ErrorState } from "../../components/ErrorState";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;

export function GabaritoTurmaScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const [turmas, setTurmas] = useState<ProfessorTurma[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProfessorTurmas();
      setTurmas(data);
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Erro ao carregar turmas");
      setError(msg);
    } finally {
      setLoading(false);
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
          <ScreenHeader title="Selecionar Turma" />
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#6C63FF" />
          </View>
        </SafeAreaView>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScreenHeader title="Selecionar Turma" />
          <ErrorState message={error} onRetry={fetch} />
        </SafeAreaView>
      </View>
    );
  }

  const agrupadas = turmas.reduce<Record<string, ProfessorTurma[]>>((acc, t) => {
    const key = `${t.turma_id}::${t.disciplina_nome}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(t);
    return acc;
  }, {});

  const grupos = Object.entries(agrupadas).map(([key, items]) => ({
    key,
    turma: items[0],
    disciplinas: items.map((i) => i.disciplina_nome).join(", "),
    alocacaoId: items[0].alocacao_id,
  }));

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Selecionar Turma" />
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {grupos.length === 0 && (
            <View style={styles.emptyState}>
              <ThemedIcon name="school-outline" size={48} color="#D0D0D0" />
              <Text style={styles.emptyTitle}>Nenhuma turma encontrada</Text>
            </View>
          )}
          {grupos.map((grupo) => (
            <TouchableOpacity
              key={grupo.key}
              style={styles.turmaCard}
              activeOpacity={0.7}
              onPress={() =>
                navigation.navigate("GabaritoAvaliacao", {
                  alocacaoId: grupo.alocacaoId,
                  turmaId: grupo.turma.turma_id,
                  turmaNome: grupo.turma.turma_codigo,
                  disciplinaNome: grupo.disciplinas,
                })
              }
              accessibilityLabel={`Turma ${grupo.turma.turma_codigo}`}
              accessibilityRole="button"
            >
              <View style={styles.turmaIcon}>
                <ThemedIcon name="school" size={24} color="#6C63FF" />
              </View>
              <View style={styles.turmaInfo}>
                <Text style={styles.turmaNome}>
                  {grupo.turma.turma_codigo} {grupo.turma.turma_nome ?? ""}
                </Text>
                <Text style={styles.turmaDetalhes}>
                  {grupo.turma.serie_nome} · {grupo.disciplinas}
                </Text>
              </View>
              <ThemedIcon name="chevron-forward" size={20} color="#C7C7C7" />
            </TouchableOpacity>
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
  turmaCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 16,
    marginBottom: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  turmaIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: "#F0EFFF",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },
  turmaInfo: {
    flex: 1,
  },
  turmaNome: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  turmaDetalhes: {
    fontSize: 13,
    color: "#888",
    marginTop: 2,
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
});
