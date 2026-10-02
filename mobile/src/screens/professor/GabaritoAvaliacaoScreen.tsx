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
import { useNavigation, useRoute, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { getProfessorAvaliacoes, type ProfessorAvaliacao } from "../../api/teacher.service";
import { ScreenHeader } from "../../components/ScreenHeader";
import { ErrorState } from "../../components/ErrorState";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;
type ScreenRoute = RouteProp<ProfessorStackParamList, "GabaritoAvaliacao">;

export function GabaritoAvaliacaoScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const { alocacaoId, turmaId, turmaNome, disciplinaNome } = route.params;

  const [avaliacoes, setAvaliacoes] = useState<ProfessorAvaliacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProfessorAvaliacoes(alocacaoId);
      setAvaliacoes(data);
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Erro ao carregar avaliações");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [alocacaoId]);

  useFocusEffect(
    useCallback(() => {
      fetch();
    }, [fetch])
  );

  const handleSelect = (aval: ProfessorAvaliacao) => {
    navigation.navigate("GabaritoCadastro", {
      avaliacaoId: aval.id,
      avaliacaoTitulo: aval.titulo,
      notaMaxima: aval.nota_maxima,
      alocacaoId,
      turmaId,
      turmaNome,
      disciplinaNome,
    });
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScreenHeader title="Selecionar Avaliação" />
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
          <ScreenHeader title="Selecionar Avaliação" />
          <ErrorState message={error} onRetry={fetch} />
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Selecionar Avaliação" />
        <View style={styles.subheader}>
          <Text style={styles.subheaderLabel}>Turma</Text>
          <Text style={styles.subheaderValue}>
            {turmaNome} · {disciplinaNome}
          </Text>
        </View>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {avaliacoes.length === 0 && (
            <View style={styles.emptyState}>
              <ThemedIcon name="document-text-outline" size={48} color="#D0D0D0" />
              <Text style={styles.emptyTitle}>Nenhuma avaliação encontrada</Text>
              <Text style={styles.emptySubtitle}>
                Crie uma avaliação antes de usar a correção de gabarito.
              </Text>
            </View>
          )}
          {avaliacoes.map((aval) => (
            <TouchableOpacity
              key={aval.id}
              style={styles.avalCard}
              activeOpacity={0.7}
              onPress={() => handleSelect(aval)}
              accessibilityLabel={aval.titulo}
              accessibilityRole="button"
            >
              <View style={styles.avalIcon}>
                <ThemedIcon name="document-text" size={24} color="#6C63FF" />
              </View>
              <View style={styles.avalInfo}>
                <Text style={styles.avalTitulo}>{aval.titulo}</Text>
                <Text style={styles.avalDetalhes}>
                  {aval.tipo} · {aval.bimestre}º Bimestre · {aval.peso} peso(s)
                </Text>
              </View>
              <View style={styles.avalBadge}>
                <Text style={styles.avalBadgeText}>{aval.nota_maxima}</Text>
              </View>
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
  subheader: {
    paddingHorizontal: 24,
    paddingTop: 8,
    paddingBottom: 4,
  },
  subheaderLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  subheaderValue: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1F1F1F",
    marginTop: 2,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
  },
  avalCard: {
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
  avalIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: "#F0EFFF",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },
  avalInfo: {
    flex: 1,
  },
  avalTitulo: {
    fontSize: 15,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  avalDetalhes: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  avalBadge: {
    backgroundColor: "#F0EFFF",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginLeft: 8,
  },
  avalBadgeText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#6C63FF",
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
