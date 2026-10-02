import { useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Switch,
  Alert,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";
import type { ResponsavelStackParamList } from "../../types/navigation";

const ROLE_LABELS: Record<string, string> = {
  responsavel: "Responsável",
  professor: "Professor",
  admin: "Administrador",
  secretaria: "Secretaria",
  cantineiro: "Cantineiro",
};

/**
 * Altura que a barra de abas flutuante ocupa sobre a tela.
 *
 * A `AnimatedTabBar` é `position: absolute`, então ela sobrepõe o conteúdo em
 * vez de empurrá-lo. Sem esta folga, "Sair da conta" e a versão ficavam
 * escondidos atrás da barra. O valor cobre a barra (~58) mais o respiro de 8
 * que ela aplica abaixo de si.
 */
const TAB_BAR_OVERLAY_HEIGHT = 66;

/** Iniciais do avatar, ignorando espaços e nomes vazios. */
function iniciais(nome: string | undefined): string {
  const limpo = nome?.trim();
  return limpo ? limpo.charAt(0).toUpperCase() : "?";
}

export function PerfilScreen() {
  useThemeVersion();

  const navigation =
    useNavigation<NativeStackNavigationProp<ResponsavelStackParamList>>();
  const insets = useSafeAreaInsets();
  const { user, logout } = useAuth();
  const { isDark, setTheme } = useTheme();
  const { clearSelection } = useSelectedStudent();

  const roleLabel = ROLE_LABELS[user?.perfil ?? ""] ?? user?.perfil ?? "Usuário";
  // A solicitação de documentos é um fluxo exclusivo do responsável.
  const podeSolicitarDocumentos = user?.perfil === "responsavel";
  // Avisos e ocorrências são dirigidos ao responsável; a rota de preferências
  // de e-mail só está registrada na pilha dele.
  const podeConfigurarNotificacoes = user?.perfil === "responsavel";
  const scrollBottomPadding = TAB_BAR_OVERLAY_HEIGHT + insets.bottom + 24;

  const handleLogout = useCallback(() => {
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
  }, [clearSelection, logout]);

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.scrollContent,
          {
            paddingTop: Math.max(insets.top, 16) + 8,
            paddingBottom: scrollBottomPadding,
          },
        ]}
      >
        <Text style={styles.headerTitle}>Perfil</Text>

        <View style={styles.card}>
          <View style={styles.profileSection}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{iniciais(user?.nome)}</Text>
            </View>
            <Text style={styles.userName} numberOfLines={2}>
              {user?.nome ?? "Usuário"}
            </Text>
            <Text style={styles.userRole}>{roleLabel}</Text>
            <Text style={styles.userEmail} numberOfLines={1}>
              {user?.email ?? ""}
            </Text>
          </View>

          <View style={styles.divider} />

          <MenuItem
            icon="create-outline"
            label="Editar informações"
            hint="Nome e e-mail"
            onPress={() => navigation.navigate("EditarPerfil")}
          />

          <View style={styles.divider} />

          {/*
            Avisos e ocorrências chegam para o responsável; a tela de
            preferências só existe na `ResponsavelStack`, então o item fica
            escondido para os demais perfis em vez de navegar para uma rota
            inexistente.
          */}
          {podeConfigurarNotificacoes && (
            <>
              <MenuItem
                icon="notifications-outline"
                label="Notificações"
                hint="Avisos e ocorrências por e-mail"
                onPress={() => navigation.navigate("Notificacoes")}
              />
              <View style={styles.divider} />
            </>
          )}

          {podeSolicitarDocumentos && (
            <>
              <MenuItem
                icon="document-text-outline"
                label="Solicitar documentos"
                hint="Boletins e comprovantes"
                onPress={() => navigation.navigate("SolicitarDocumentos")}
              />
              <View style={styles.divider} />
            </>
          )}

          <MenuItem
            icon="accessibility-outline"
            label="Acessibilidade"
            hint="Texto, contraste e tela ligada"
            onPress={() => navigation.navigate("Acessibilidade")}
          />
        </View>

        <View style={styles.card}>
          <View style={styles.switchItem}>
            <View style={styles.switchText}>
              <Text style={styles.menuItemText}>Modo escuro</Text>
              <Text style={styles.switchHint}>
                {isDark ? "Ativado" : "Desativado"}
              </Text>
            </View>
            <Switch
              value={isDark}
              onValueChange={(v) => setTheme(v ? "dark" : "light")}
              trackColor={{ false: "#E5E5E5", true: "#FF5B8F" }}
              ios_backgroundColor="#E5E5E5"
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
            <ThemedIcon name="log-out-outline" size={20} color="#E74C3C" />
            <Text style={styles.logoutText}>Sair da conta</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.version}>ePass · versão 1.0.0</Text>
      </ScrollView>
    </View>
  );
}

function MenuItem({
  icon,
  label,
  hint,
  onPress,
}: {
  icon: string;
  label: string;
  hint: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={styles.menuItem}
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityRole="button"
    >
      <View style={styles.menuIcon}>
        <ThemedIcon name={icon as never} size={20} color="#FF5B8F" />
      </View>
      <View style={styles.menuText}>
        <Text style={styles.menuItemText}>{label}</Text>
        <Text style={styles.menuItemHint}>{hint}</Text>
      </View>
      <ThemedIcon name="chevron-forward" size={20} color="#C7C7C7" />
    </TouchableOpacity>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F7",
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 24,
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
  userEmail: {
    fontSize: 13,
    color: "#B0B0B0",
    marginTop: 4,
  },
  divider: {
    height: 1,
    backgroundColor: "#E5E5E5",
    marginHorizontal: -24,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingVertical: 16,
  },
  menuIcon: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: "#FFEAF1",
    alignItems: "center",
    justifyContent: "center",
  },
  menuText: {
    flex: 1,
  },
  menuItemText: {
    fontSize: 16,
    color: "#1F1F1F",
    fontWeight: "500",
  },
  menuItemHint: {
    fontSize: 12,
    color: "#7A7A7A",
    marginTop: 2,
  },
  switchItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 12,
  },
  switchText: {
    flex: 1,
  },
  switchHint: {
    fontSize: 12,
    color: "#7A7A7A",
    marginTop: 2,
  },
  logoutItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    gap: 8,
  },
  logoutText: {
    fontSize: 16,
    color: "#E74C3C",
    fontWeight: "600",
  },
  version: {
    fontSize: 12,
    color: "#B0B0B0",
    textAlign: "center",
    marginTop: 4,
  },
});
