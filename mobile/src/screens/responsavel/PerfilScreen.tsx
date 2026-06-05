import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Switch,
  Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";

const ROLE_LABELS: Record<string, string> = {
  responsavel: "Responsável",
  professor: "Professor",
  admin: "Administrador",
  secretaria: "Secretaria",
};

export function PerfilScreen() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const { clearSelection } = useSelectedStudent();

  const roleLabel = ROLE_LABELS[user?.perfil ?? ""] ?? user?.perfil ?? "Usuário";

  const handleLogout = () => {
    Alert.alert(
      "Sair da conta",
      "Tem certeza que deseja sair?",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Sair",
          style: "destructive",
          onPress: async () => {
            try { clearSelection(); } catch {}
            await logout();
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.headerTitle}>Perfil</Text>

          <View style={styles.card}>
            <View style={styles.profileSection}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>
                  {user?.nome?.charAt(0).toUpperCase() ?? "?"}
                </Text>
              </View>
              <Text style={styles.userName}>{user?.nome ?? "Usuário"}</Text>
              <Text style={styles.userRole}>{roleLabel}</Text>
            </View>

            <View style={styles.divider} />

            <TouchableOpacity
              style={styles.menuItem}
              accessibilityLabel="Editar informações"
              accessibilityRole="button"
            >
              <Text style={styles.menuItemText}>Editar informações</Text>
              <Ionicons name="chevron-forward" size={20} color="#C7C7C7" />
            </TouchableOpacity>

            <View style={styles.divider} />

            <TouchableOpacity
              style={styles.menuItem}
              accessibilityLabel="Solicitar documentos"
              accessibilityRole="button"
            >
              <Text style={styles.menuItemText}>Solicitar documentos</Text>
              <Ionicons name="chevron-forward" size={20} color="#C7C7C7" />
            </TouchableOpacity>
          </View>

          <View style={styles.card}>
            <TouchableOpacity
              style={styles.menuItem}
              accessibilityLabel="Acessibilidade"
              accessibilityRole="button"
            >
              <Text style={styles.menuItemText}>Acessibilidade</Text>
              <Ionicons name="chevron-forward" size={20} color="#C7C7C7" />
            </TouchableOpacity>

            <View style={styles.divider} />

            <View style={styles.switchItem}>
              <Text style={styles.menuItemText}>Modo escuro</Text>
              <Switch
                value={isDark}
                onValueChange={toggleTheme}
                trackColor={{ false: "#E5E5E5", true: "#FF5B8F" }}
                thumbColor="white"
                accessibilityLabel="Alternar modo escuro"
                accessibilityRole="switch"
              />
            </View>

            <View style={styles.divider} />

            <TouchableOpacity
              style={styles.logoutItem}
              onPress={handleLogout}
              accessibilityLabel="Sair da conta"
              accessibilityRole="button"
            >
              <Text style={styles.logoutText}>Sair</Text>
              <Ionicons name="chevron-forward" size={20} color="#FF5B8F" />
            </TouchableOpacity>
          </View>
        </ScrollView>
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
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  },
  headerTitle: {
    fontSize: 40,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 24,
  },
  card: {
    backgroundColor: "white",
    borderRadius: 36,
    padding: 24,
    marginBottom: 20,
  },
  profileSection: {
    alignItems: "center",
    paddingBottom: 8,
  },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: 44,
    borderWidth: 5,
    borderColor: "#FF5B8F",
    backgroundColor: "#FF5B8F",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },
  avatarText: {
    color: "white",
    fontSize: 36,
    fontWeight: "700",
  },
  userName: {
    fontSize: 22,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 4,
  },
  userRole: {
    fontSize: 14,
    color: "#7A7A7A",
    fontWeight: "500",
  },
  divider: {
    height: 1,
    backgroundColor: "#E5E5E5",
    marginHorizontal: -24,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 16,
  },
  menuItemText: {
    fontSize: 16,
    color: "#1F1F1F",
    fontWeight: "500",
  },
  switchItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 12,
  },
  logoutItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    gap: 6,
  },
  logoutText: {
    fontSize: 16,
    color: "#FF5B8F",
    fontWeight: "600",
  },
});
