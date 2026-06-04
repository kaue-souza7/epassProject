import { View, Text, StyleSheet, SafeAreaView } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export function RelatoriosScreen() {
  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.center}>
          <Ionicons name="document-text-outline" size={56} color="#D0D0D0" />
          <Text style={styles.title}>Relatórios</Text>
          <Text style={styles.subtitle}>
            Boletins, histórico escolar e frequência em breve.
          </Text>
        </View>
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
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  title: {
    color: "#1A1A2E",
    fontSize: 22,
    fontWeight: "700",
    marginTop: 16,
  },
  subtitle: {
    color: "#888",
    fontSize: 15,
    textAlign: "center",
    marginTop: 8,
  },
});
