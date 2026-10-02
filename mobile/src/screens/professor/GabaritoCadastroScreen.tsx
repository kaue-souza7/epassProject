import { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  TextInput,
  Alert,
} from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { ScreenHeader } from "../../components/ScreenHeader";
import { useToast } from "../../components/Toast";
import { salvarGabarito } from "../../services/gabaritoStorage";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;
type ScreenRoute = RouteProp<ProfessorStackParamList, "GabaritoCadastro">;

const ALTERNATIVAS = ["A", "B", "C", "D", "E"];

export function GabaritoCadastroScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const toast = useToast();
  const { avaliacaoId, avaliacaoTitulo, notaMaxima, alocacaoId, turmaId, turmaNome, disciplinaNome } = route.params;

  const [numeroQuestoes, setNumeroQuestoes] = useState("5");
  const [respostas, setRespostas] = useState<string[]>([]);
  const [etapa, setEtapa] = useState<"quantidade" | "respostas">("quantidade");

  const questoes = parseInt(numeroQuestoes, 10) || 5;

  const handleConfirmQuantidade = () => {
    const q = parseInt(numeroQuestoes, 10);
    if (!q || q < 1 || q > 50) {
      toast.warning("Informe um número entre 1 e 50 questões.");
      return;
    }
    setRespostas(Array(q).fill(""));
    setEtapa("respostas");
  };

  const handleSetResposta = (index: number, alternativa: string) => {
    setRespostas((prev) => {
      const next = [...prev];
      next[index] = alternativa;
      return next;
    });
  };

  const handleSalvar = async () => {
    const vazias = respostas.some((r) => !r);
    if (vazias) {
      toast.warning("Informe a resposta correta para todas as questões.");
      return;
    }

    await salvarGabarito({
      avaliacaoId,
      questoes: respostas.length,
      respostasCorretas: respostas,
      createdAt: new Date().toISOString(),
    });

    Alert.alert("Gabarito salvo!", "Agora você pode escanear a folha de respostas.", [
      {
        text: "Ir para Câmera",
        onPress: () =>
          navigation.navigate("GabaritoScanner", {
            avaliacaoId,
            avaliacaoTitulo,
            notaMaxima,
            alocacaoId,
            turmaId,
            turmaNome,
            disciplinaNome,
          }),
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Gabarito da Prova" />
        <View style={styles.subheader}>
          <Text style={styles.subheaderLabel}>Avaliação</Text>
          <Text style={styles.subheaderValue}>
            {avaliacaoTitulo} · {turmaNome}
          </Text>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent}>
          {etapa === "quantidade" ? (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Número de questões</Text>
              <Text style={styles.cardSubtitle}>
                Quantas questões objetivas esta prova possui?
              </Text>
              <TextInput
                style={styles.input}
                value={numeroQuestoes}
                onChangeText={setNumeroQuestoes}
                keyboardType="number-pad"
                maxLength={2}
                placeholder="Ex: 10"
                placeholderTextColor="#C7C7C7"
              />
              <TouchableOpacity
                style={styles.primaryButton}
                onPress={handleConfirmQuantidade}
                accessibilityLabel="Confirmar número de questões"
                accessibilityRole="button"
              >
                <Text style={styles.primaryButtonText}>Continuar</Text>
                <ThemedIcon name="arrow-forward" size={18} color="#FFF" />
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <View style={styles.card}>
                <Text style={styles.cardTitle}>Respostas corretas</Text>
                <Text style={styles.cardSubtitle}>
                  Informe a alternativa correta para cada questão.
                </Text>

                {respostas.map((resposta, index) => (
                  <View key={index} style={styles.questaoRow}>
                    <Text style={styles.questaoLabel}>Q{index + 1}</Text>
                    <View style={styles.alternativasRow}>
                      {ALTERNATIVAS.map((alt) => (
                        <TouchableOpacity
                          key={alt}
                          style={[
                            styles.altButton,
                            resposta === alt && styles.altButtonActive,
                          ]}
                          onPress={() => handleSetResposta(index, alt)}
                          accessibilityLabel={`Questão ${index + 1}, alternativa ${alt}`}
                          accessibilityRole="button"
                        >
                          <Text
                            style={[
                              styles.altText,
                              resposta === alt && styles.altTextActive,
                            ]}
                          >
                            {alt}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                ))}
              </View>

              <TouchableOpacity
                style={styles.primaryButton}
                onPress={handleSalvar}
                accessibilityLabel="Salvar gabarito"
                accessibilityRole="button"
              >
                <ThemedIcon name="checkmark-circle" size={18} color="#FFF" />
                <Text style={styles.primaryButtonText}>Salvar Gabarito</Text>
              </TouchableOpacity>
            </>
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
  card: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 13,
    color: "#888",
    marginBottom: 20,
  },
  input: {
    backgroundColor: "#F5F5F7",
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 16,
    fontSize: 24,
    fontWeight: "700",
    color: "#1F1F1F",
    textAlign: "center",
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  questaoRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
    gap: 12,
  },
  questaoLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: "#1F1F1F",
    width: 32,
  },
  alternativasRow: {
    flex: 1,
    flexDirection: "row",
    gap: 8,
  },
  altButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 2,
    borderColor: "#E5E5E5",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#FFF",
  },
  altButtonActive: {
    borderColor: "#6C63FF",
    backgroundColor: "#6C63FF",
  },
  altText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#666",
  },
  altTextActive: {
    color: "#FFF",
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
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFF",
  },
});
