import { View, Text, TouchableOpacity, StyleSheet, ScrollView, SafeAreaView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;

interface ModuloConfig {
  id: string;
  title: string;
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
  gradient: [string, string];
  onPress: (navigation: NavProp) => void;
}

const MODULOS: ModuloConfig[] = [
  {
    id: "classes",
    title: "Classes",
    description: "Gerenciamento das turmas do professor",
    icon: "school",
    gradient: ["#F84F8D", "#FF8664"],
    onPress: (nav) => nav.navigate("ClassesList"),
  },
  {
    id: "gabarito",
    title: "Correção de Gabarito",
    description: "Funcionalidade futura para correção automatizada de avaliações",
    icon: "scan",
    gradient: ["#6C63FF", "#A78BFA"],
    onPress: (nav) => nav.navigate("GabaritoHome"),
  },
];

export function ProfessorModulosScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.screenTitle}>Módulos</Text>
          <Text style={styles.screenSubtitle}>
            Selecione um módulo para acessar suas funcionalidades
          </Text>

          {MODULOS.map((modulo) => (
            <TouchableOpacity
              key={modulo.id}
              style={styles.moduloCard}
              activeOpacity={0.8}
              onPress={() => modulo.onPress(navigation)}
              accessibilityLabel={modulo.title}
              accessibilityRole="button"
            >
              <LinearGradient
                colors={modulo.gradient}
                start={{ x: 0, y: 0.5 }}
                end={{ x: 1, y: 0.5 }}
                style={styles.moduloGradient}
              >
                <View style={styles.moduloContent}>
                  <View style={styles.moduloIconWrapper}>
                    <ThemedIcon name={modulo.icon} size={28} color="#FFF" />
                  </View>
                  <View style={styles.moduloInfo}>
                    <Text style={styles.moduloTitle}>{modulo.title}</Text>
                    <Text style={styles.moduloDescription}>
                      {modulo.description}
                    </Text>
                  </View>
                  <ThemedIcon name="chevron-forward" size={20} color="rgba(255,255,255,0.6)" />
                </View>
              </LinearGradient>
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
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  },
  screenTitle: {
    fontSize: 34,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  screenSubtitle: {
    fontSize: 14,
    color: "#888",
    marginTop: 4,
    marginBottom: 20,
  },
  moduloCard: {
    borderRadius: 24,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
    overflow: "hidden",
  },
  moduloGradient: {
    padding: 20,
  },
  moduloContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },
  moduloIconWrapper: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
  },
  moduloInfo: {
    flex: 1,
  },
  moduloTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FFF",
  },
  moduloDescription: {
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
    marginTop: 2,
    lineHeight: 18,
  },
});
