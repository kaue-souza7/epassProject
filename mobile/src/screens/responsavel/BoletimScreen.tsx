import { useState, useCallback } from "react";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  SafeAreaView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useReportCard } from "../../hooks/useReportCard";
import { ErrorState } from "../../components/ErrorState";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { SituacaoAluno } from "../../types";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Boletim">;

const BIMESTRES = [1, 2, 3, 4];

const SITUACAO_LABELS: Record<SituacaoAluno, string> = {
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  recuperacao: "Recuperação",
  aprovado_pos_recuperacao: "Aprovado",
  reprovado_pos_recuperacao: "Reprovado",
};

const SITUACAO_COLORS: Record<SituacaoAluno, string> = {
  aprovado: "#4CAF50",
  reprovado: "#F44336",
  recuperacao: "#FF9800",
  aprovado_pos_recuperacao: "#66BB6A",
  reprovado_pos_recuperacao: "#EF5350",
};

function formatMedia(value: number | string): string {
  return Number(value).toFixed(1);
}

export function BoletimScreen() {
  const navigation = useNavigation<NavProp>();
  const { selectedChild } = useSelectedStudent();
  const [bimestre, setBimestre] = useState(1);

  const enrollmentId = selectedChild?.matricula_id ?? null;
  const { reportCard, loading, error, refetch } = useReportCard(
    enrollmentId,
    bimestre
  );

  useFocusEffect(
    useCallback(() => {
      refetch();
    }, [refetch])
  );

  if (!selectedChild) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              accessibilityLabel="Voltar"
              accessibilityRole="button"
            >
              <Ionicons name="chevron-back" size={28} color="#1F1F1F" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Boletim</Text>
            <View style={{ width: 28 }} />
          </View>
          <View style={styles.center}>
            <Text style={styles.noStudentText}>Nenhum aluno selecionado</Text>
            <TouchableOpacity
              style={styles.noStudentButton}
              onPress={() => navigation.navigate("SelectStudent")}
            >
              <Text style={styles.noStudentButtonText}>Selecionar aluno</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Boletim</Text>
          <View style={{ width: 28 }} />
        </View>

        {/* Student info card */}
        <View style={styles.studentCard}>
          <View style={styles.studentAvatar}>
            <Text style={styles.studentAvatarText}>
              {selectedChild.aluno_nome.charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={styles.studentInfo}>
            <Text style={styles.studentName}>{selectedChild.aluno_nome}</Text>
            {reportCard && (
              <Text style={styles.studentMeta}>
                {reportCard.turma_codigo} · {reportCard.serie_nome} ·{" "}
                {reportCard.ano_letivo}
              </Text>
            )}
          </View>
        </View>

        {/* Bimestre selector chips */}
        <View style={styles.chipsRow}>
          {BIMESTRES.map((b) => (
              <TouchableOpacity
                key={b}
                style={[
                  styles.chip,
                  bimestre === b && styles.chipActive,
                ]}
                onPress={() => setBimestre(b)}
                activeOpacity={0.7}
                accessibilityLabel={`${b}º bimestre`}
                accessibilityRole="button"
              >
              <Text
                style={[
                  styles.chipText,
                  bimestre === b && styles.chipTextActive,
                ]}
              >
                {b}º Bim
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
          </View>
        ) : error ? (
          <ErrorState message={error} onRetry={refetch} />
        ) : !reportCard || reportCard.disciplinas.length === 0 ? (
          <View style={styles.center}>
            <Ionicons name="document-text-outline" size={56} color="#D0D0D0" />
            <Text style={styles.emptyTitle}>Nenhuma disciplina</Text>
            <Text style={styles.emptySubtitle}>
              Nenhuma nota lançada para este bimestre.
            </Text>
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {reportCard.disciplinas.map((disciplina) => {
              const situacao = disciplina.situacao;
              const showRecuperacao =
                disciplina.nota_recuperacao != null &&
                disciplina.media_pos_recuperacao != null;

              return (
                <View key={disciplina.disciplina_id} style={styles.disciplinaCard}>
                  {/* Top row: name + media */}
                  <View style={styles.disciplinaTopRow}>
                    <Text style={styles.disciplinaNome}>
                      {disciplina.disciplina_nome}
                    </Text>
                    <Text
                      style={[
                        styles.disciplinaMedia,
                        {
                          color:
                            disciplina.media >= 6 ? "#4CAF50" : "#F44336",
                        },
                      ]}
                    >
                      {formatMedia(disciplina.media)}
                    </Text>
                  </View>

                  {/* Bottom row: frequency + situation badge */}
                  <View style={styles.disciplinaBottomRow}>
                    <Text style={styles.disciplinaFrequencia}>
                      Frequência:{" "}
                      {disciplina.frequencia != null
                        ? `${disciplina.frequencia}%`
                        : "—"}
                    </Text>
                    {situacao && (
                      <View
                        style={[
                          styles.situacaoBadge,
                          { backgroundColor: SITUACAO_COLORS[situacao] },
                        ]}
                      >
                        <Text style={styles.situacaoBadgeText}>
                          {SITUACAO_LABELS[situacao]}
                        </Text>
                      </View>
                    )}
                  </View>

                  {/* Recuperacao details (if present) */}
                  {showRecuperacao && (
                    <View style={styles.recuperacaoRow}>
                      <Text style={styles.recuperacaoLabel}>
                        Rec: {formatMedia(disciplina.nota_recuperacao!)} → Média:{" "}
                        {formatMedia(disciplina.media_pos_recuperacao!)}
                      </Text>
                    </View>
                  )}
                </View>
              );
            })}
          </ScrollView>
        )}
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
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  noStudentText: {
    color: "#333",
    fontSize: 15,
    fontWeight: "500",
    textAlign: "center",
    marginTop: 16,
  },
  noStudentButton: {
    borderWidth: 2,
    borderColor: "#FF5B8F",
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 12,
    marginTop: 24,
  },
  noStudentButtonText: {
    color: "#FF5B8F",
    fontSize: 16,
    fontWeight: "600",
  },

  /* Student card */
  studentCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 36,
    padding: 20,
    marginHorizontal: 24,
    marginBottom: 16,
  },
  studentAvatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "#FF5B8F",
    justifyContent: "center",
    alignItems: "center",
  },
  studentAvatarText: {
    color: "white",
    fontSize: 22,
    fontWeight: "700",
  },
  studentInfo: {
    flex: 1,
    marginLeft: 14,
  },
  studentName: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  studentMeta: {
    fontSize: 13,
    color: "#7A7A7A",
    fontWeight: "500",
    marginTop: 2,
  },

  /* Bimestre chips */
  chipsRow: {
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: 24,
    marginBottom: 16,
  },
  chip: {
    flex: 1,
    backgroundColor: "white",
    borderRadius: 999,
    paddingVertical: 10,
    alignItems: "center",
  },
  chipActive: {
    backgroundColor: "#FF5B8F",
  },
  chipText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  chipTextActive: {
    color: "white",
  },

  /* Scroll content */
  scrollContent: {
    paddingHorizontal: 24,
    paddingBottom: 32,
  },

  /* Disciplina card */
  disciplinaCard: {
    backgroundColor: "white",
    borderRadius: 20,
    padding: 16,
    marginBottom: 10,
  },
  disciplinaTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  disciplinaNome: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
    flex: 1,
    marginRight: 12,
  },
  disciplinaMedia: {
    fontSize: 22,
    fontWeight: "700",
  },
  disciplinaBottomRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 8,
  },
  disciplinaFrequencia: {
    fontSize: 13,
    color: "#7A7A7A",
    fontWeight: "500",
  },
  situacaoBadge: {
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  situacaoBadgeText: {
    color: "white",
    fontSize: 12,
    fontWeight: "700",
  },

  /* Recuperacao */
  recuperacaoRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: "#F0F0F0",
  },
  recuperacaoLabel: {
    fontSize: 13,
    color: "#FF9800",
    fontWeight: "500",
  },

  /* Empty state */
  emptyTitle: {
    color: "#1A1A2E",
    fontSize: 22,
    fontWeight: "700",
    marginTop: 16,
  },
  emptySubtitle: {
    color: "#888",
    fontSize: 15,
    textAlign: "center",
    marginTop: 8,
    lineHeight: 22,
  },
});
