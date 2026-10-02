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
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { getTurmaAlunos, type ProfessorAluno } from "../../api/teacher.service";
import { ErrorState } from "../../components/ErrorState";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList, "TurmaAlunos">;
type ScreenRoute = RouteProp<ProfessorStackParamList, "TurmaAlunos">;

export function TurmaAlunosScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const { turmaNome, disciplinaNome } = route.params;

  const [alunos, setAlunos] = useState<ProfessorAluno[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlunos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTurmaAlunos(route.params.turmaId);
      setAlunos(data);
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Erro ao carregar alunos");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [route.params.turmaId]);

  useEffect(() => {
    fetchAlunos();
  }, [fetchAlunos]);

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
              <Text style={styles.headerTitle}>{turmaNome}</Text>
              <Text style={styles.headerSubtitle}>{disciplinaNome}</Text>
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
            <Text style={styles.headerTitle}>{turmaNome}</Text>
            <Text style={styles.headerSubtitle}>
              {disciplinaNome} · {alunos.length} alunos
            </Text>
          </View>
        </View>

        <FlatList
          data={alunos}
          keyExtractor={(item) => item.matricula_id}
          contentContainerStyle={styles.listContent}
          initialNumToRender={15}
          maxToRenderPerBatch={10}
          windowSize={7}
          removeClippedSubviews
          renderItem={({ item, index }) => (
            <View style={styles.alunoRow}>
              <View style={styles.alunoAvatar}>
                <Text style={styles.alunoAvatarText}>
                  {item.aluno_nome.charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.alunoInfo}>
                <Text style={styles.alunoNome}>{item.aluno_nome}</Text>
              </View>
              <Text style={styles.alunoIndex}>{index + 1}</Text>
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <ThemedIcon name="people-outline" size={48} color="#D0D0D0" />
              <Text style={styles.emptyText}>Nenhum aluno encontrado</Text>
            </View>
          }
        />
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
    paddingBottom: 16,
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
  listContent: {
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  alunoRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 14,
    marginBottom: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  alunoAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
  },
  alunoAvatarText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FF5B8F",
  },
  alunoInfo: {
    flex: 1,
    marginLeft: 14,
  },
  alunoNome: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  alunoIndex: {
    fontSize: 12,
    fontWeight: "500",
    color: "#B0B0B0",
    marginLeft: 8,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 14,
    color: "#888",
    marginTop: 12,
  },
});
