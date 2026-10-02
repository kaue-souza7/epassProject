import { useAuth } from "../contexts/AuthContext";
import { ResponsavelStack } from "./ResponsavelStack";
import { ProfessorStack } from "./ProfessorStack";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { createThemedStyles } from "../theme/useThemedStyles";
import { ThemedIcon } from "../theme/ThemedIcon";

function UnauthorizedScreen() {
  const { logout } = useAuth();
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <View style={styles.iconCircle}>
          <ThemedIcon name="shield-checkmark-outline" size={48} color="#FF5B8F" />
        </View>
        <Text style={styles.title}>Acesso não autorizado</Text>
        <Text style={styles.subtitle}>
          Seu perfil de usuário não tem permissão para acessar este aplicativo.
          Entre em contato com a administração.
        </Text>
        <TouchableOpacity
          style={styles.button}
          onPress={logout}
          accessibilityLabel="Sair da conta"
          accessibilityRole="button"
        >
          <Text style={styles.buttonText}>Sair da conta</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export function ProfileRouter() {
  const { user } = useAuth();

  switch (user?.perfil) {
    case "responsavel":
      return <ResponsavelStack />;
    case "professor":
      return <ProfessorStack />;
    default:
      return <UnauthorizedScreen />;
  }
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F7",
    justifyContent: "center",
    alignItems: "center",
  },
  content: {
    alignItems: "center",
    paddingHorizontal: 32,
    gap: 16,
  },
  iconCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1F1F1F",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 15,
    color: "#7A7A7A",
    textAlign: "center",
    lineHeight: 22,
  },
  button: {
    marginTop: 16,
    backgroundColor: "#FF5B8F",
    borderRadius: 999,
    paddingHorizontal: 32,
    paddingVertical: 14,
  },
  buttonText: {
    color: "white",
    fontSize: 16,
    fontWeight: "700",
  },
});
