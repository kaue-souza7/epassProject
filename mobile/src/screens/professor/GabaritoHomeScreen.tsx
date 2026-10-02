import { View, Text, TouchableOpacity, StyleSheet, ScrollView, SafeAreaView } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;

export function GabaritoHomeScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Correção de Gabarito" />
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <TouchableOpacity
            style={styles.startCard}
            activeOpacity={0.8}
            onPress={() => navigation.navigate("GabaritoTurma")}
            accessibilityLabel="Iniciar nova correção"
            accessibilityRole="button"
          >
            <LinearGradient
              colors={["#6C63FF", "#A78BFA"]}
              start={{ x: 0, y: 0.5 }}
              end={{ x: 1, y: 0.5 }}
              style={styles.startGradient}
            >
              <View style={styles.startIconWrapper}>
                <ThemedIcon name="camera" size={32} color="#FFF" />
              </View>
              <Text style={styles.startTitle}>Nova Correção</Text>
              <Text style={styles.startSubtitle}>
                Fotografe a folha de respostas e corrija automaticamente
              </Text>
              <View style={styles.startBadge}>
                <ThemedIcon name="scan-outline" size={16} color="#FFF" />
                <Text style={styles.startBadgeText}>Automático</Text>
              </View>
            </LinearGradient>
          </TouchableOpacity>

          <View style={styles.infoSection}>
            <Text style={styles.infoTitle}>Como funciona</Text>
            {[
              { icon: "document-text", text: "Selecione a turma e a avaliação" },
              { icon: "checkbox", text: "Informe o gabarito da prova" },
              { icon: "camera", text: "Fotografe a folha de respostas do aluno" },
              { icon: "checkmark-circle", text: "Revise e confirme a nota" },
            ].map((item, idx) => (
              <View key={idx} style={styles.infoRow}>
                <View style={styles.infoIconWrapper}>
                  <ThemedIcon name={item.icon as any} size={18} color="#6C63FF" />
                </View>
                <Text style={styles.infoText}>{item.text}</Text>
              </View>
            ))}
          </View>
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
    paddingTop: 24,
    paddingBottom: 32,
  },
  startCard: {
    borderRadius: 24,
    marginBottom: 24,
    shadowColor: "#6C63FF",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 8,
    overflow: "hidden",
  },
  startGradient: {
    padding: 28,
    alignItems: "center",
  },
  startIconWrapper: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
  },
  startTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#FFF",
    marginBottom: 6,
  },
  startSubtitle: {
    fontSize: 14,
    color: "rgba(255,255,255,0.8)",
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 16,
  },
  startBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.2)",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 6,
    gap: 6,
  },
  startBadgeText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FFF",
  },
  infoSection: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 20,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 16,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    marginBottom: 14,
  },
  infoIconWrapper: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: "#F0EFFF",
    justifyContent: "center",
    alignItems: "center",
  },
  infoText: {
    fontSize: 14,
    color: "#444",
    flex: 1,
  },
});
