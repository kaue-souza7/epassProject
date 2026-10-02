import { TouchableOpacity, View, Text, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import type { ProfessorTurma } from "../../api/teacher.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { ThemedIcon } from "../../theme/ThemedIcon";

interface TurmaCardProps {
  turma: ProfessorTurma;
  onChamada: () => void;
  onNotas: () => void;
  onLiberar?: () => void;
}

export function TurmaCard({ turma, onChamada, onNotas, onLiberar }: TurmaCardProps) {
  return (
    <View style={styles.turmaCard}>
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
          onPress={onChamada}
          accessibilityLabel="Lançar chamada"
          accessibilityRole="button"
        >
          <ThemedIcon name="calendar" size={16} color="#FF5B8F" />
          <Text style={styles.acaoText}>Chamada</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.acaoButton}
          onPress={onNotas}
          accessibilityLabel="Lançar notas"
          accessibilityRole="button"
        >
          <ThemedIcon name="document-text" size={16} color="#FF5B8F" />
          <Text style={styles.acaoText}>Notas</Text>
        </TouchableOpacity>

        {onLiberar && (
          <TouchableOpacity
            style={styles.acaoButton}
            onPress={onLiberar}
            accessibilityLabel="Liberar boletim"
            accessibilityRole="button"
          >
            <ThemedIcon name="checkmark-circle" size={16} color="#FF5B8F" />
            <Text style={styles.acaoText}>Liberar</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = createThemedStyles({
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
});
