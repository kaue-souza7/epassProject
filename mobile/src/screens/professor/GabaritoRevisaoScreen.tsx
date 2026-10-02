import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
  Image,
} from "react-native";
import Svg, { Circle, Line, Rect, Text as SvgText } from "react-native-svg";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { getTurmaAlunos } from "../../api/teacher.service";
import { ScreenHeader } from "../../components/ScreenHeader";
import { DetectorWebView } from "../../components/gabarito/DetectorWebView";
import type { ProfessorStackParamList } from "../../types/navigation";
import type { DetectionResult } from "../../types/gabarito";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;
type ScreenRoute = RouteProp<ProfessorStackParamList, "GabaritoRevisao">;

const ALTERNATIVAS = ["A", "B", "C", "D", "E"];

function gerarMockRespostas(gabarito: string[]): string[] {
  return gabarito.map((correta) => {
    const errar = Math.random() < 0.25;
    if (errar) {
      const outras = ALTERNATIVAS.filter((a) => a !== correta);
      return outras[Math.floor(Math.random() * outras.length)];
    }
    return correta;
  });
}

export function GabaritoRevisaoScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const { avaliacaoId, avaliacaoTitulo, notaMaxima, alocacaoId, turmaId, turmaNome, disciplinaNome, gabarito, imageBase64 } = route.params;

  const [detection, setDetection] = useState<DetectionResult | null>(null);
  const [detectionDone, setDetectionDone] = useState(false);
  const [respostasDetectadas, setRespostasDetectadas] = useState<string[] | null>(null);
  const [alunos, setAlunos] = useState<{ matricula_id: string; aluno_nome: string }[]>([]);
  const [selectedAluno, setSelectedAluno] = useState<{ matricula_id: string; aluno_nome: string } | null>(null);
  const [showAlunos, setShowAlunos] = useState(false);
  const [loadingAlunos, setLoadingAlunos] = useState(true);

  useEffect(() => {
    getTurmaAlunos(turmaId)
      .then((data) => setAlunos(data))
      .catch(() => {})
      .finally(() => setLoadingAlunos(false));
  }, [turmaId]);

  const handleDetectionResult = useCallback((result: DetectionResult) => {
    setDetection(result);
    setDetectionDone(true);
    const mock = gerarMockRespostas(gabarito.respostasCorretas);
    setRespostasDetectadas(mock);
  }, [gabarito.respostasCorretas]);

  const handleRetry = () => {
    navigation.goBack();
  };

  const toggleResposta = (index: number) => {
    if (!respostasDetectadas) return;
    setRespostasDetectadas((prev) => {
      if (!prev) return prev;
      const atual = prev[index];
      const idxAtual = ALTERNATIVAS.indexOf(atual);
      const proxima = ALTERNATIVAS[(idxAtual + 1) % ALTERNATIVAS.length];
      const next = [...prev];
      next[index] = proxima;
      return next;
    });
  };

  const handleContinuar = () => {
    if (!selectedAluno || !respostasDetectadas) return;
    navigation.navigate("GabaritoResultado", {
      avaliacaoId,
      avaliacaoTitulo,
      notaMaxima,
      alocacaoId,
      turmaId,
      turmaNome,
      disciplinaNome,
      gabarito,
      matriculaId: selectedAluno.matricula_id,
      alunoNome: selectedAluno.aluno_nome,
      respostasAluno: respostasDetectadas,
    });
  };

  const imageUri = `data:image/jpeg;base64,${imageBase64}`;

  if (!detectionDone) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScreenHeader title="Processando..." />
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#6C63FF" />
            <Text style={styles.loadingText}>Detectando marcadores da folha...</Text>
          </View>
        </SafeAreaView>
        <DetectorWebView base64={imageBase64} onResult={handleDetectionResult} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Revisar Respostas" />
        <View style={styles.subheader}>
          <Text style={styles.subheaderValue}>
            {avaliacaoTitulo} · {turmaNome}
          </Text>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.detectionCard}>
            {detection && (
              <>
                <View style={styles.imageContainer}>
                  <Image
                    source={{ uri: imageUri }}
                    style={styles.image}
                    resizeMode="contain"
                  />
                  <Svg viewBox="0 0 600 800" style={StyleSheet.absoluteFill}>
                    {detection.markers.map((m) => (
                      <g key={m.name}>
                        <Circle cx={m.expectedCx} cy={m.expectedCy} r={3} fill="rgba(255,255,255,0.5)" />
                        <Line
                          x1={m.x - 16} y1={m.y}
                          x2={m.x + 16} y2={m.y}
                          stroke={m.found ? "#4CAF50" : "#F44336"}
                          strokeWidth={3}
                        />
                        <Line
                          x1={m.x} y1={m.y - 16}
                          x2={m.x} y2={m.y + 16}
                          stroke={m.found ? "#4CAF50" : "#F44336"}
                          strokeWidth={3}
                        />
                        <Rect
                          x={m.x - 8} y={m.y - 8}
                          width={16} height={16}
                          stroke={m.found ? "#4CAF50" : "#F44336"}
                          strokeWidth={2}
                          fill="none"
                        />
                        <SvgText
                          x={m.x + 20} y={m.y + 5}
                          fill={m.found ? "#4CAF50" : "#F44336"}
                          fontSize={14}
                          fontWeight="bold"
                        >
                          {m.found ? "OK" : "FAIL"}
                        </SvgText>
                      </g>
                    ))}
                    {detection.allFound && (
                      <Line
                        x1={detection.markers[0].x} y1={detection.markers[0].y}
                        x2={detection.markers[1].x} y2={detection.markers[1].y}
                        stroke="#6C63FF" strokeWidth={2} strokeDasharray="6,4"
                      />
                    )}
                    {detection.allFound && (
                      <Line
                        x1={detection.markers[1].x} y1={detection.markers[1].y}
                        x2={detection.markers[3].x} y2={detection.markers[3].y}
                        stroke="#6C63FF" strokeWidth={2} strokeDasharray="6,4"
                      />
                    )}
                    {detection.allFound && (
                      <Line
                        x1={detection.markers[3].x} y1={detection.markers[3].y}
                        x2={detection.markers[2].x} y2={detection.markers[2].y}
                        stroke="#6C63FF" strokeWidth={2} strokeDasharray="6,4"
                      />
                    )}
                    {detection.allFound && (
                      <Line
                        x1={detection.markers[2].x} y1={detection.markers[2].y}
                        x2={detection.markers[0].x} y2={detection.markers[0].y}
                        stroke="#6C63FF" strokeWidth={2} strokeDasharray="6,4"
                      />
                    )}
                  </Svg>
                </View>

                <View style={styles.detectionStatus}>
                  <ThemedIcon
                    name={detection.allFound ? "checkmark-circle" : "close-circle"}
                    size={22}
                    color={detection.allFound ? "#4CAF50" : "#F44336"}
                  />
                  <Text style={[styles.detectionText, detection.allFound ? styles.detectionOk : styles.detectionFail]}>
                    {detection.allFound
                      ? `${detection.foundCount} marcadores encontrados`
                      : `Apenas ${detection.foundCount} de 4 marcadores`}
                  </Text>
                </View>

                {!detection.allFound && (
                  <TouchableOpacity
                    style={styles.retryButton}
                    onPress={handleRetry}
                    accessibilityLabel="Tirar nova foto"
                    accessibilityRole="button"
                  >
                    <ThemedIcon name="camera" size={18} color="#FFF" />
                    <Text style={styles.retryButtonText}>Tentar novamente</Text>
                  </TouchableOpacity>
                )}
              </>
            )}
          </View>

          <TouchableOpacity
            style={styles.alunoSelector}
            onPress={() => setShowAlunos(!showAlunos)}
            accessibilityLabel="Selecionar aluno"
            accessibilityRole="button"
          >
            <ThemedIcon name="person" size={20} color="#6C63FF" />
            <Text style={styles.alunoSelectorText}>
              {selectedAluno ? selectedAluno.aluno_nome : "Selecionar aluno..."}
            </Text>
            <ThemedIcon name={showAlunos ? "chevron-up" : "chevron-down"} size={20} color="#C7C7C7" />
          </TouchableOpacity>

          {showAlunos && (
            <View style={styles.alunoList}>
              {loadingAlunos ? (
                <ActivityIndicator size="small" color="#6C63FF" style={{ padding: 16 }} />
              ) : (
                alunos.map((a) => (
                  <TouchableOpacity
                    key={a.matricula_id}
                    style={[
                      styles.alunoItem,
                      selectedAluno?.matricula_id === a.matricula_id && styles.alunoItemActive,
                    ]}
                    onPress={() => {
                      setSelectedAluno(a);
                      setShowAlunos(false);
                    }}
                  >
                    <Text style={styles.alunoItemText}>{a.aluno_nome}</Text>
                    {selectedAluno?.matricula_id === a.matricula_id && (
                      <ThemedIcon name="checkmark" size={20} color="#6C63FF" />
                    )}
                  </TouchableOpacity>
                ))
              )}
            </View>
          )}

          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>Respostas detectadas</Text>
              <Text style={styles.cardSubtitle}>
                Toque na alternativa para corrigir manualmente
              </Text>
            </View>

            {respostasDetectadas &&
              respostasDetectadas.map((resposta, index) => (
                <View key={index} style={styles.questaoRow}>
                  <Text style={styles.questaoLabel}>Q{index + 1}</Text>
                  <View style={styles.alternativasRow}>
                    {ALTERNATIVAS.map((alt) => {
                      const isDetectada = resposta === alt;
                      const isCorreta = gabarito.respostasCorretas[index] === alt;
                      return (
                        <TouchableOpacity
                          key={alt}
                          style={[
                            styles.altButton,
                            isDetectada && styles.altButtonDetected,
                            isDetectada && isCorreta && styles.altButtonCorrect,
                            isDetectada && !isCorreta && styles.altButtonWrong,
                          ]}
                          onPress={() => toggleResposta(index)}
                          accessibilityLabel={`Questão ${index + 1}, ${alt}`}
                          accessibilityRole="button"
                        >
                          <Text
                            style={[
                              styles.altText,
                              isDetectada && styles.altTextDetected,
                            ]}
                          >
                            {alt}
                          </Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </View>
              ))}
          </View>

          <TouchableOpacity
            style={[
              styles.primaryButton,
              !selectedAluno && styles.primaryButtonDisabled,
            ]}
            onPress={handleContinuar}
            disabled={!selectedAluno}
            accessibilityLabel="Ver resultado da correção"
            accessibilityRole="button"
          >
            <ThemedIcon name="calculator" size={18} color="#FFF" />
            <Text style={styles.primaryButtonText}>Ver Resultado</Text>
          </TouchableOpacity>

          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>

      <DetectorWebView base64={imageBase64} onResult={handleDetectionResult} />
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
    paddingHorizontal: 24,
  },
  loadingText: {
    fontSize: 15,
    color: "#888",
    marginTop: 16,
  },
  subheader: {
    paddingHorizontal: 24,
    paddingTop: 8,
    paddingBottom: 4,
  },
  subheaderValue: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 12,
    paddingBottom: 32,
  },
  detectionCard: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 16,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  imageContainer: {
    aspectRatio: 600 / 800,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "#1a1a2e",
  },
  image: {
    width: "100%",
    height: "100%",
  },
  detectionStatus: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 12,
    gap: 8,
  },
  detectionText: {
    fontSize: 15,
    fontWeight: "700",
  },
  detectionOk: {
    color: "#4CAF50",
  },
  detectionFail: {
    color: "#F44336",
  },
  retryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#6C63FF",
    borderRadius: 28,
    paddingVertical: 12,
    marginTop: 12,
    gap: 8,
  },
  retryButtonText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FFF",
  },
  alunoSelector: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 14,
    marginBottom: 8,
    gap: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  alunoSelectorText: {
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  alunoList: {
    backgroundColor: "#FFF",
    borderRadius: 16,
    marginBottom: 16,
    overflow: "hidden",
  },
  alunoItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#F0F0F0",
  },
  alunoItemActive: {
    backgroundColor: "#F0EFFF",
  },
  alunoItemText: {
    flex: 1,
    fontSize: 14,
    fontWeight: "600",
    color: "#1F1F1F",
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
  cardHeader: {
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  cardSubtitle: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  questaoRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
    gap: 8,
  },
  questaoLabel: {
    fontSize: 13,
    fontWeight: "700",
    color: "#1F1F1F",
    width: 28,
  },
  alternativasRow: {
    flex: 1,
    flexDirection: "row",
    gap: 6,
  },
  altButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: "#E5E5E5",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#FFF",
  },
  altButtonDetected: {
    borderWidth: 0,
  },
  altButtonCorrect: {
    backgroundColor: "#4CAF50",
  },
  altButtonWrong: {
    backgroundColor: "#F44336",
  },
  altText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#666",
  },
  altTextDetected: {
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
  primaryButtonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFF",
  },
});
