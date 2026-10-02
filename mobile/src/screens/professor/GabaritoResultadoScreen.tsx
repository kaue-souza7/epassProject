import { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
  Modal,
} from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;
type ScreenRoute = RouteProp<ProfessorStackParamList, "GabaritoResultado">;

export function GabaritoResultadoScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const { avaliacaoId, avaliacaoTitulo, notaMaxima, alocacaoId, turmaId, turmaNome, disciplinaNome, gabarito, matriculaId, alunoNome, respostasAluno } = route.params;

  const [saving, setSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const acertos = respostasAluno.reduce(
    (acc, r, i) => acc + (r === gabarito.respostasCorretas[i] ? 1 : 0),
    0
  );
  const total = gabarito.respostasCorretas.length;
  const erros = total - acertos;
  const nota = Math.round((acertos / total) * notaMaxima * 100) / 100;

  const handleLancarNota = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setShowSuccess(true);
    }, 1500);
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Resultado da Correção" />

        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.infoRow}>
            <View style={styles.infoItem}>
              <ThemedIcon name="person" size={16} color="#888" />
              <Text style={styles.infoText}>{alunoNome}</Text>
            </View>
            <View style={styles.infoItem}>
              <ThemedIcon name="document-text" size={16} color="#888" />
              <Text style={styles.infoText}>{avaliacaoTitulo}</Text>
            </View>
          </View>

          <View style={styles.scoreCard}>
            <View style={styles.scoreCircle}>
              <Text style={styles.scoreValue}>{nota.toFixed(1)}</Text>
              <Text style={styles.scoreMax}>/ {Number(notaMaxima).toFixed(1)}</Text>
            </View>
            <Text style={styles.scoreLabel}>Nota calculada</Text>
            <View style={styles.aproveitamentoBadge}>
              <Text style={styles.aproveitamentoText}>
                Aproveitamento: {Math.round((acertos / total) * 100)}%
              </Text>
            </View>
          </View>

          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <ThemedIcon name="checkmark-circle" size={28} color="#4CAF50" />
              <Text style={styles.statValue}>{acertos}</Text>
              <Text style={styles.statLabel}>Acertos</Text>
            </View>
            <View style={styles.statCard}>
              <ThemedIcon name="close-circle" size={28} color="#F44336" />
              <Text style={[styles.statValue, { color: "#F44336" }]}>{erros}</Text>
              <Text style={styles.statLabel}>Erros</Text>
            </View>
            <View style={styles.statCard}>
              <ThemedIcon name="help-circle" size={28} color="#FF9800" />
              <Text style={styles.statValue}>{total}</Text>
              <Text style={styles.statLabel}>Questões</Text>
            </View>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Detalhamento</Text>
            {respostasAluno.map((resposta, index) => {
              const correta = gabarito.respostasCorretas[index];
              const isAcerto = resposta === correta;
              return (
                <View key={index} style={styles.detalheRow}>
                  <Text style={styles.detalheQuestao}>Q{index + 1}</Text>
                  <View style={styles.detalheRespostas}>
                    <View
                      style={[
                        styles.detalheBadge,
                        isAcerto ? styles.detalheBadgeCorrect : styles.detalheBadgeWrong,
                      ]}
                    >
                      <Text style={styles.detalheBadgeText}>{resposta}</Text>
                    </View>
                    {!isAcerto && (
                      <>
                        <ThemedIcon name="close" size={14} color="#F44336" />
                        <View style={[styles.detalheBadge, styles.detalheBadgeGabarito]}>
                          <Text style={styles.detalheBadgeText}>{correta}</Text>
                        </View>
                      </>
                    )}
                  </View>
                  <ThemedIcon
                    name={isAcerto ? "checkmark-circle" : "close-circle"}
                    size={18}
                    color={isAcerto ? "#4CAF50" : "#F44336"}
                  />
                </View>
              );
            })}
          </View>

          <TouchableOpacity
            style={[styles.primaryButton, saving && styles.primaryButtonDisabled]}
            onPress={handleLancarNota}
            disabled={saving}
            accessibilityLabel="Lançar nota no sistema"
            accessibilityRole="button"
          >
            {saving ? (
              <View style={styles.savingRow}>
                <ActivityIndicator size="small" color="#FFF" />
                <Text style={styles.primaryButtonText}>Salvando nota...</Text>
              </View>
            ) : (
              <>
                <ThemedIcon name="cloud-upload" size={18} color="#FFF" />
                <Text style={styles.primaryButtonText}>Lançar Nota</Text>
              </>
            )}
          </TouchableOpacity>

          <Modal visible={showSuccess} transparent animationType="fade">
            <View style={styles.modalOverlay}>
              <View style={styles.modalContent}>
                <View style={styles.modalIconCircle}>
                  <ThemedIcon name="checkmark-circle" size={56} color="#4CAF50" />
                </View>
                <Text style={styles.modalTitle}>Nota lançada com sucesso</Text>

                <View style={styles.modalInfo}>
                  <View style={styles.modalInfoRow}>
                    <ThemedIcon name="person" size={16} color="#888" />
                    <Text style={styles.modalInfoLabel}>Aluno:</Text>
                    <Text style={styles.modalInfoValue}>{alunoNome}</Text>
                  </View>
                  <View style={styles.modalInfoRow}>
                    <ThemedIcon name="document-text" size={16} color="#888" />
                    <Text style={styles.modalInfoLabel}>Avaliação:</Text>
                    <Text style={styles.modalInfoValue}>{avaliacaoTitulo}</Text>
                  </View>
                  <View style={styles.modalInfoRow}>
                    <ThemedIcon name="checkmark-circle" size={16} color="#4CAF50" />
                    <Text style={styles.modalInfoLabel}>Acertos:</Text>
                    <Text style={styles.modalInfoValue}>{acertos}/{total}</Text>
                  </View>
                  <View style={styles.modalInfoRow}>
                    <ThemedIcon name="star" size={16} color="#FF9800" />
                    <Text style={styles.modalInfoLabel}>Nota:</Text>
                    <Text style={styles.modalInfoValue}>{nota.toFixed(1)}</Text>
                  </View>
                </View>

                <TouchableOpacity
                  style={styles.modalButton}
                  onPress={() => {
                    setShowSuccess(false);
                    navigation.navigate("GabaritoHome");
                  }}
                  accessibilityLabel="Corrigir outra prova"
                  accessibilityRole="button"
                >
                  <ThemedIcon name="camera" size={18} color="#FFF" />
                  <Text style={styles.modalButtonText}>Corrigir outra prova</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.modalButtonSecondary}
                  onPress={() => {
                    setShowSuccess(false);
                    navigation.navigate("GabaritoHome");
                  }}
                  accessibilityLabel="Voltar para Correção de Gabarito"
                  accessibilityRole="button"
                >
                  <ThemedIcon name="home" size={18} color="#6C63FF" />
                  <Text style={styles.modalButtonSecondaryText}>Voltar para Correção de Gabarito</Text>
                </TouchableOpacity>
              </View>
            </View>
          </Modal>

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
    paddingTop: 16,
    paddingBottom: 32,
  },
  infoRow: {
    flexDirection: "row",
    gap: 16,
    marginBottom: 20,
  },
  infoItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  infoText: {
    fontSize: 13,
    color: "#666",
    fontWeight: "500",
  },
  scoreCard: {
    alignItems: "center",
    marginBottom: 24,
  },
  scoreCircle: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: "#F0EFFF",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
    borderWidth: 4,
    borderColor: "#6C63FF",
  },
  scoreValue: {
    fontSize: 36,
    fontWeight: "700",
    color: "#6C63FF",
  },
  scoreMax: {
    fontSize: 14,
    color: "#888",
    fontWeight: "500",
  },
  scoreLabel: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  aproveitamentoBadge: {
    marginTop: 12,
    backgroundColor: "#E8F5E9",
    borderRadius: 20,
    paddingHorizontal: 20,
    paddingVertical: 8,
  },
  aproveitamentoText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#2E7D32",
  },
  statsRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 14,
    alignItems: "center",
    gap: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  statValue: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  statLabel: {
    fontSize: 11,
    color: "#888",
    fontWeight: "500",
  },
  card: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 16,
  },
  detalheRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
    gap: 10,
  },
  detalheQuestao: {
    fontSize: 13,
    fontWeight: "700",
    color: "#1F1F1F",
    width: 28,
  },
  detalheRespostas: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  detalheBadge: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  detalheBadgeCorrect: {
    backgroundColor: "#E8F5E9",
  },
  detalheBadgeWrong: {
    backgroundColor: "#FFEBEE",
  },
  detalheBadgeGabarito: {
    backgroundColor: "#FFF3E0",
  },
  detalheBadgeText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  primaryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#6C63FF",
    borderRadius: 28,
    paddingVertical: 16,
    gap: 8,
    shadowColor: "#6C63FF",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  primaryButtonDisabled: {
    opacity: 0.7,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFF",
  },
  savingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  modalContent: {
    backgroundColor: "#FFF",
    borderRadius: 24,
    padding: 32,
    width: "100%",
    maxWidth: 360,
    alignItems: "center",
  },
  modalIconCircle: {
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 24,
    textAlign: "center",
  },
  modalInfo: {
    width: "100%",
    backgroundColor: "#F5F5F7",
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
    gap: 12,
  },
  modalInfoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  modalInfoLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#888",
  },
  modalInfoValue: {
    flex: 1,
    fontSize: 14,
    fontWeight: "700",
    color: "#1F1F1F",
    textAlign: "right",
  },
  modalButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#6C63FF",
    borderRadius: 28,
    paddingVertical: 14,
    width: "100%",
    gap: 8,
    marginBottom: 12,
  },
  modalButtonText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FFF",
  },
  modalButtonSecondary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 28,
    paddingVertical: 14,
    width: "100%",
    gap: 8,
    borderWidth: 2,
    borderColor: "#6C63FF",
  },
  modalButtonSecondaryText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#6C63FF",
  },
});
