import { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  Animated,
  ActivityIndicator,
} from "react-native";
import { useNavigation, useRoute, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { ProfessorStackParamList } from "../../types/navigation";
import type { GabaritoData } from "../../types/gabarito";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;
type ScreenRoute = RouteProp<ProfessorStackParamList, "GabaritoProcessamento">;

const STAGES = [
  { key: "image", label: "Processando imagem...", icon: "image-outline" as const, start: 0, end: 0.3 },
  { key: "markers", label: "Detectando marcações...", icon: "radio-outline" as const, start: 0.3, end: 0.55 },
  { key: "validate", label: "Validando gabarito...", icon: "checkmark-done-outline" as const, start: 0.55, end: 0.75 },
  { key: "grade", label: "Calculando nota...", icon: "calculator-outline" as const, start: 0.75, end: 1 },
];

const DEMO_RESPOSTAS: string[] = ["A", "B", "C", "D", "A", "B", "C", "D", "A", "B"];

export function GabaritoProcessamentoScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const params = route.params;

  const progress = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(1)).current;
  const stageRef = useRef(0);
  const [progressValue, setProgressValue] = useState(0);
  const [currentStage, setCurrentStage] = useState(0);
  const [completed, setCompleted] = useState(false);

  const stage = STAGES[currentStage];

  useFocusEffect(
    useCallback(() => {
      progress.setValue(0);
      setProgressValue(0);
      setCurrentStage(0);
      setCompleted(false);
      stageRef.current = 0;
      fadeAnim.setValue(1);

      const listener = progress.addListener(({ value }) => {
        const pct = Math.round(value * 100);
        setProgressValue(pct);

        const stageIndex = STAGES.findIndex((s) => value < s.end);
        const idx = stageIndex === -1 ? STAGES.length - 1 : stageIndex;

        if (idx !== stageRef.current) {
          stageRef.current = idx;
          fadeAnim.setValue(0.3);
          Animated.timing(fadeAnim, {
            toValue: 1,
            duration: 300,
            useNativeDriver: false,
          }).start();
        }
        setCurrentStage(idx);

        if (value >= 1) {
          setCompleted(true);
        }
      });

      Animated.timing(progress, {
        toValue: 1,
        duration: 10000,
        useNativeDriver: false,
      }).start();

      return () => {
        progress.removeListener(listener);
        progress.stopAnimation();
      };
    }, [progress, fadeAnim])
  );

  useEffect(() => {
    if (!completed) return;

    const timer = setTimeout(() => {
      const demoGabarito: GabaritoData = {
        avaliacaoId: params.avaliacaoId,
        questoes: 10,
        respostasCorretas: ["A", "B", "C", "E", "A", "B", "C", "E", "A", "B"],
        createdAt: new Date().toISOString(),
      };

      navigation.navigate("GabaritoResultado", {
        avaliacaoId: params.avaliacaoId,
        avaliacaoTitulo: params.avaliacaoTitulo,
        notaMaxima: params.notaMaxima,
        alocacaoId: params.alocacaoId,
        turmaId: params.turmaId,
        turmaNome: params.turmaNome,
        disciplinaNome: params.disciplinaNome,
        gabarito: demoGabarito,
        matriculaId: "demo-matricula-001",
        alunoNome: "João Silva",
        respostasAluno: DEMO_RESPOSTAS,
      });
    }, 1000);

    return () => clearTimeout(timer);
  }, [completed, navigation, params]);

  const progressWidth = progress.interpolate({
    inputRange: [0, 1],
    outputRange: ["0%", "100%"],
  });

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Processando Folha" />

        <View style={styles.content}>
          <View style={styles.progressCard}>
            <View style={styles.progressTrack}>
              <Animated.View style={[styles.progressBar, { width: progressWidth }]} />
            </View>
            <Text style={styles.progressText}>{progressValue}%</Text>
          </View>

          <View style={styles.stageDisplay}>
            {stage && (
              <Animated.View style={[styles.stageCenter, { opacity: fadeAnim }]}>
                <View style={styles.stageIconRing}>
                  <ThemedIcon name={stage.icon} size={44} color="#6C63FF" />
                </View>
                <Text style={styles.stageLabel}>{stage.label}</Text>
                <Text style={styles.stageSubtext}>
                  {stage.key === "image" && "Analisando estrutura da imagem capturada"}
                  {stage.key === "markers" && "Buscando marcadores de canto da folha"}
                  {stage.key === "validate" && "Comparando respostas com o gabarito"}
                  {stage.key === "grade" && "Processando resultado final"}
                </Text>
                <ActivityIndicator size="small" color="#6C63FF" style={{ marginTop: 20 }} />
              </Animated.View>
            )}
          </View>

          <View style={styles.stageList}>
            {STAGES.map((s, i) => {
              const isComplete = i < currentStage;
              const isActive = i === currentStage;
              const isPending = i > currentStage;

              return (
                <View
                  key={s.key}
                  style={[
                    styles.stageRow,
                    isActive && styles.stageRowActive,
                    isComplete && styles.stageRowComplete,
                  ]}
                >
                  <View style={styles.stageDot}>
                    {isComplete && (
                      <ThemedIcon name="checkmark-circle" size={22} color="#4CAF50" />
                    )}
                    {isActive && (
                      <ActivityIndicator size="small" color="#6C63FF" />
                    )}
                    {isPending && <View style={styles.stageDotPending} />}
                  </View>
                  <Text
                    style={[
                      styles.stageRowLabel,
                      isComplete && styles.stageRowLabelComplete,
                      isActive && styles.stageRowLabelActive,
                      isPending && styles.stageRowLabelPending,
                    ]}
                  >
                    {s.label}
                  </Text>
                  {isComplete && (
                    <ThemedIcon name="checkmark" size={16} color="#4CAF50" style={styles.stageRowCheck} />
                  )}
                </View>
              );
            })}
          </View>
        </View>
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
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 16,
  },
  progressCard: {
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  progressTrack: {
    flex: 1,
    height: 8,
    backgroundColor: "#EEE",
    borderRadius: 4,
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    backgroundColor: "#6C63FF",
    borderRadius: 4,
  },
  progressText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#6C63FF",
    minWidth: 40,
    textAlign: "right",
  },
  stageDisplay: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 24,
  },
  stageCenter: {
    alignItems: "center",
  },
  stageIconRing: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: "#F0EFFF",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
    borderWidth: 3,
    borderColor: "#6C63FF",
  },
  stageLabel: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 8,
  },
  stageSubtext: {
    fontSize: 13,
    color: "#888",
    textAlign: "center",
    lineHeight: 18,
  },
  stageList: {
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  stageRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: 10,
    marginBottom: 4,
    gap: 12,
  },
  stageRowActive: {
    backgroundColor: "#F0EFFF",
  },
  stageRowComplete: {
    opacity: 0.7,
  },
  stageDot: {
    width: 22,
    height: 22,
    justifyContent: "center",
    alignItems: "center",
  },
  stageDotPending: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#DDD",
  },
  stageRowLabel: {
    flex: 1,
    fontSize: 14,
    fontWeight: "600",
  },
  stageRowLabelComplete: {
    color: "#4CAF50",
  },
  stageRowLabelActive: {
    color: "#6C63FF",
    fontWeight: "700",
  },
  stageRowLabelPending: {
    color: "#BBB",
  },
  stageRowCheck: {
    marginLeft: 4,
  },
});
