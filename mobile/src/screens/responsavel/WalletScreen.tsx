import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useWallet } from "../../hooks/useWallet";
import type { ResponsavelStackParamList } from "../../types/navigation";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Wallet">;

export function WalletScreen() {
  const navigation = useNavigation<NavProp>();
  const { saldo, ultimaMovimentacao, loading, error, refetch } = useWallet();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Carteira</Text>
          <View style={{ width: 28 }} />
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Ionicons name="alert-circle-outline" size={56} color="#FF5B8F" />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity style={styles.retryButton} onPress={refetch}>
              <Text style={styles.retryText}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.content}>
            <View style={styles.balanceCard}>
              <Text style={styles.balanceLabel}>Saldo disponível</Text>
              <Text style={styles.balanceAmount}>
                R$ {(saldo ?? 0).toFixed(2)}
              </Text>
              <Text style={styles.lastMovement}>
                Última: {ultimaMovimentacao ?? "—"}
              </Text>
            </View>

            <View style={styles.actionsRow}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => navigation.navigate("Statement")}
              >
                <View style={[styles.actionIcon, { backgroundColor: "#FFF0F3" }]}>
                  <Ionicons name="list-outline" size={24} color="#FF5B8F" />
                </View>
                <Text style={styles.actionLabel}>Extrato</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => navigation.navigate("Recharge")}
              >
                <View style={[styles.actionIcon, { backgroundColor: "#E8F5E9" }]}>
                  <Ionicons name="add-circle-outline" size={24} color="#4CAF50" />
                </View>
                <Text style={styles.actionLabel}>Recarregar</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
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
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  errorText: {
    color: "#333",
    fontSize: 15,
    fontWeight: "500",
    textAlign: "center",
    marginTop: 16,
  },
  retryButton: {
    borderWidth: 2,
    borderColor: "#FF5B8F",
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 12,
    marginTop: 24,
  },
  retryText: {
    color: "#FF5B8F",
    fontSize: 16,
    fontWeight: "600",
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  balanceCard: {
    backgroundColor: "white",
    borderRadius: 36,
    padding: 32,
    alignItems: "center",
    marginBottom: 32,
  },
  balanceLabel: {
    fontSize: 16,
    color: "#7A7A7A",
    fontWeight: "500",
    marginBottom: 8,
  },
  balanceAmount: {
    fontSize: 48,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 12,
  },
  lastMovement: {
    fontSize: 14,
    color: "#C7C7C7",
    fontWeight: "500",
  },
  actionsRow: {
    flexDirection: "row",
    gap: 16,
  },
  actionButton: {
    flex: 1,
    backgroundColor: "white",
    borderRadius: 24,
    padding: 24,
    alignItems: "center",
  },
  actionIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },
  actionLabel: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F1F1F",
  },
});
