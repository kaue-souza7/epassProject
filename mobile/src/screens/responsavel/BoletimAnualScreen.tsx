import { KeepAwake } from "../../components/KeepAwake";
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
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useAnnualReport } from "../../hooks/useReportCard";
import { ErrorState } from "../../components/ErrorState";
import type { ResponsavelStackParamList } from "../../types/navigation";
import type { SituacaoAluno } from "../../types";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "BoletimAnual">;

const SITUACAO_LABELS: Record<SituacaoAluno, string> = {
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  recuperacao: "Recuperação",
  aprovado_pos_recuperacao: "Aprovado pós-rec",
  reprovado_pos_recuperacao: "Reprovado pós-rec",
};

const SITUACAO_COLORS: Record<SituacaoAluno, string> = {
  aprovado: "#4CAF50",
  reprovado: "#F44336",
  recuperacao: "#FF9800",
  aprovado_pos_recuperacao: "#66BB6A",
  reprovado_pos_recuperacao: "#EF5350",
};

function formatMedia(value: number | string | null): string {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(1);
}

function SituacaoBadge({ situacao }: { situacao: SituacaoAluno | null }) {
  if (!situacao) {
    return (
      <View style={styles.situacaoBadgeNaoLiberada}>
        <Text style={styles.situacaoBadgeNaoLiberadaText}>Não liberado</Text>
      </View>
    );
  }
  return (
    <View style={[styles.situacaoBadge, { backgroundColor: SITUACAO_COLORS[situacao] }]}>
      <Text style={styles.situacaoBadgeText}>{SITUACAO_LABELS[situacao]}</Text>
    </View>
  );
}

function DisciplinaCard({
  disciplina,
}: {
  disciplina: {
    disciplina_nome: string;
    media: number;
    frequencia: number | null;
    nota_recuperacao: number | null;
    media_pos_recuperacao: number | null;
  };
}) {
  const showRecuperacao =
    disciplina.nota_recuperacao != null && disciplina.media_pos_recuperacao != null;

  return (
    <View style={styles.disciplinaCard}>
      <View style={styles.disciplinaTopRow}>
        <Text style={styles.disciplinaNome}>{disciplina.disciplina_nome}</Text>
        <Text
          style={[
            styles.disciplinaMedia,
            { color: disciplina.media >= 6 ? "#4CAF50" : "#F44336" },
          ]}
        >
          {formatMedia(disciplina.media)}
        </Text>
      </View>
      <View style={styles.disciplinaBottomRow}>
        <Text style={styles.disciplinaFrequencia}>
          Frequência:{" "}
          {disciplina.frequencia != null ? `${disciplina.frequencia}%` : "—"}
        </Text>
      </View>
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
}

function BimestreSection({
  bimestre,
  disciplinas,
  defaultExpanded,
}: {
  bimestre: number;
  disciplinas: {
    disciplina_nome: string;
    media: number;
    frequencia: number | null;
    nota_recuperacao: number | null;
    media_pos_recuperacao: number | null;
  }[];
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded ?? bimestre === 1);

  return (
    <View style={styles.bimestreSection}>
      <TouchableOpacity
        style={styles.bimestreHeader}
        onPress={() => setExpanded((prev) => !prev)}
        activeOpacity={0.7}
        accessibilityLabel={`${bimestre}º bimestre. Toque para ${expanded ? "recolher" : "expandir"}`}
        accessibilityRole="button"
      >
        <View style={styles.bimestreHeaderLeft}>
          <ThemedIcon
            name={expanded ? "chevron-down" : "chevron-forward"}
            size={18}
            color="#FF5B8F"
          />
          <Text style={styles.bimestreTitle}>{bimestre}º Bimestre</Text>
        </View>
        <Text style={styles.bimestreCount}>{disciplinas.length} disciplinas</Text>
      </TouchableOpacity>
      {expanded && (
        <View style={styles.bimestreContent}>
          {disciplinas.map((d) => (
            <DisciplinaCard key={d.disciplina_nome} disciplina={d} />
          ))}
        </View>
      )}
    </View>
  );
}

export function BoletimAnualScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const { selectedChild } = useSelectedStudent();

  const enrollmentId = selectedChild?.matricula_id ?? null;
  const { annualReport, loading, error, refetch } = useAnnualReport(enrollmentId);

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
              <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Boletim Anual</Text>
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
      {/* Evita a tela apagar durante a leitura. */}
      <KeepAwake />
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Boletim Anual</Text>
          <View style={{ width: 28 }} />
        </View>

        <View style={styles.studentCard}>
          <View style={styles.studentAvatar}>
            <Text style={styles.studentAvatarText}>
              {selectedChild.aluno_nome.charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={styles.studentInfo}>
            <Text style={styles.studentName}>{selectedChild.aluno_nome}</Text>
            {annualReport && (
              <Text style={styles.studentMeta}>
                {annualReport.turma_codigo} · {annualReport.serie_nome} ·{" "}
                {annualReport.ano_letivo}
              </Text>
            )}
          </View>
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
          </View>
        ) : error ? (
          <ErrorState message={error} onRetry={refetch} />
        ) : !annualReport ? (
          <View style={styles.center}>
            <ThemedIcon name="document-text-outline" size={56} color="#D0D0D0" />
            <Text style={styles.emptyTitle}>Nenhum dado disponível</Text>
            <Text style={styles.emptySubtitle}>
              Não foi possível carregar o boletim anual.
            </Text>
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            <View style={styles.summaryCard}>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Situação Final</Text>
                <SituacaoBadge situacao={annualReport.situacao_final} />
              </View>
              <View style={styles.summaryDivider} />
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Média pós-recuperação</Text>
                <Text style={styles.summaryValue}>
                  {formatMedia(annualReport.media_pos_recuperacao)}
                </Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Média pré-recuperação</Text>
                <Text style={styles.summaryValue}>
                  {formatMedia(annualReport.media_pre_recuperacao)}
                </Text>
              </View>
            </View>

            {annualReport.bimestres.map((b) => (
              <BimestreSection
                key={b.bimestre}
                bimestre={b.bimestre}
                disciplinas={b.disciplinas}
              />
            ))}
          </ScrollView>
        )}
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
  scrollContent: {
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  summaryCard: {
    backgroundColor: "white",
    borderRadius: 20,
    padding: 20,
    marginBottom: 20,
  },
  summaryRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 6,
  },
  summaryLabel: {
    fontSize: 14,
    fontWeight: "500",
    color: "#7A7A7A",
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  summaryDivider: {
    height: 1,
    backgroundColor: "#F0F0F0",
    marginVertical: 8,
  },
  situacaoBadge: {
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  situacaoBadgeText: {
    color: "white",
    fontSize: 13,
    fontWeight: "700",
  },
  situacaoBadgeNaoLiberada: {
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 4,
    backgroundColor: "#E5E5EA",
  },
  situacaoBadgeNaoLiberadaText: {
    color: "#7A7A7A",
    fontSize: 13,
    fontWeight: "700",
  },
  bimestreSection: {
    marginBottom: 12,
  },
  bimestreHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "white",
    borderRadius: 20,
    padding: 16,
  },
  bimestreHeaderLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  bimestreTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  bimestreCount: {
    fontSize: 13,
    color: "#888",
    fontWeight: "500",
  },
  bimestreContent: {
    marginTop: 8,
    paddingLeft: 8,
  },
  disciplinaCard: {
    backgroundColor: "white",
    borderRadius: 16,
    padding: 14,
    marginBottom: 8,
  },
  disciplinaTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  disciplinaNome: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1F1F1F",
    flex: 1,
    marginRight: 12,
  },
  disciplinaMedia: {
    fontSize: 20,
    fontWeight: "700",
  },
  disciplinaBottomRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 6,
  },
  disciplinaFrequencia: {
    fontSize: 12,
    color: "#7A7A7A",
    fontWeight: "500",
  },
  recuperacaoRow: {
    marginTop: 6,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: "#F0F0F0",
  },
  recuperacaoLabel: {
    fontSize: 12,
    color: "#FF9800",
    fontWeight: "500",
  },
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
