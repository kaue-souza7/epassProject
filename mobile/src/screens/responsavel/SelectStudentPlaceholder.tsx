import { useEffect, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  FlatList,
  SafeAreaView,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { LinearGradient } from "expo-linear-gradient";
import { useDashboard } from "../../hooks/useDashboard";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { Child } from "../../types/responsavel";
import type { SituacaoAluno } from "../../types";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "SelectStudent">;

const SITUACAO_LABELS: Record<SituacaoAluno, string> = {
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  recuperacao: "Recuperação",
  aprovado_pos_recuperacao: "Aprovado pós-recuperação",
  reprovado_pos_recuperacao: "Reprovado pós-recuperação",
};

const SITUACAO_COLORS: Record<SituacaoAluno, string> = {
  aprovado: "#4CAF50",
  reprovado: "#F44336",
  recuperacao: "#FF9800",
  aprovado_pos_recuperacao: "#66BB6A",
  reprovado_pos_recuperacao: "#EF5350",
};

export function SelectStudentPlaceholder() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const { data, loading, error, refetch } = useDashboard();
  const { selectChild } = useSelectedStudent();
  const autoSelected = useRef(false);

  useEffect(() => {
    if (data?.filhos.length && !autoSelected.current) {
      autoSelected.current = true;
      selectChild(data.filhos[0]);
      navigation.replace("HomeTabs");
    }
  }, [data, navigation, selectChild]);

  if (loading) {
    return (
      <LinearGradient colors={["#F84F8D", "#FF8664"]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={styles.gradient}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <ActivityIndicator size="large" color="white" />
            <Text style={styles.statusText}>Carregando alunos...</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>
    );
  }

  if (error) {
    return (
      <LinearGradient colors={["#F84F8D", "#FF8664"]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={styles.gradient}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <ThemedIcon name="alert-circle-outline" size={56} color="white" />
            <Text style={styles.statusText}>
              Não foi possível carregar seus alunos.
            </Text>
            <TouchableOpacity style={styles.retryButton} onPress={refetch}>
              <ThemedIcon name="refresh" size={18} color="white" />
              <Text style={styles.retryText}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </LinearGradient>
    );
  }

  const filhos = data?.filhos ?? [];

  if (filhos.length === 0) {
    return (
      <LinearGradient colors={["#F84F8D", "#FF8664"]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={styles.gradient}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <ThemedIcon name="people-outline" size={56} color="white" />
            <Text style={styles.statusText}>
              Nenhum aluno encontrado para este responsável.
            </Text>
          </View>
        </SafeAreaView>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={["#F84F8D", "#FF8664"]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={styles.gradient}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <Text style={styles.title}>Selecione um aluno</Text>
          <Text style={styles.subtitle}>
            Escolha qual aluno deseja acompanhar.
          </Text>
        </View>
        <FlatList
          data={filhos}
          keyExtractor={(item) => item.aluno_id}
          renderItem={({ item }) => (
            <ChildCard
              child={item}
              onPress={() => {
                selectChild(item);
                navigation.replace("HomeTabs");
              }}
            />
          )}
          contentContainerStyle={styles.list}
        />
      </SafeAreaView>
    </LinearGradient>
  );
}

function ChildCard({ child, onPress }: { child: Child; onPress: () => void }) {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.cardContent}>
        <Text style={styles.cardName}>{child.aluno_nome}</Text>
        {child.turma_codigo && (
          <Text style={styles.cardClass}>{child.turma_codigo}</Text>
        )}
      </View>
      {child.situacao && (
        <View
          style={[
            styles.badge,
            { backgroundColor: SITUACAO_COLORS[child.situacao] },
          ]}
        >
          <Text style={styles.badgeText}>
            {SITUACAO_LABELS[child.situacao]}
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = createThemedStyles({
  gradient: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  statusText: {
    color: "white",
    fontSize: 16,
    marginTop: 16,
    fontWeight: "500",
    textAlign: "center",
  },
  retryButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 2,
    borderColor: "white",
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 12,
    marginTop: 24,
  },
  retryText: {
    color: "white",
    fontSize: 16,
    fontWeight: "600",
  },
  header: {
    alignItems: "center",
    paddingTop: 48,
    paddingBottom: 24,
    paddingHorizontal: 24,
  },
  title: {
    color: "white",
    fontSize: 26,
    fontWeight: "700",
  },
  subtitle: {
    color: "rgba(255,255,255,0.8)",
    fontSize: 15,
    marginTop: 8,
    textAlign: "center",
  },
  list: {
    padding: 16,
    gap: 12,
    paddingBottom: 32,
  },
  card: {
    backgroundColor: "white",
    borderRadius: 36,
    padding: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  cardContent: {
    flex: 1,
    marginRight: 12,
  },
  cardName: {
    fontSize: 17,
    fontWeight: "700",
    color: "#333",
  },
  cardClass: {
    fontSize: 14,
    color: "#888",
    marginTop: 4,
  },
  badge: {
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  badgeText: {
    color: "white",
    fontSize: 12,
    fontWeight: "700",
  },
});
