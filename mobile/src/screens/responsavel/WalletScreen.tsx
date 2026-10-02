import { useCallback } from "react";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
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
import { ErrorState } from "../../components/ErrorState";
import type { ResponsavelStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Wallet">;

interface FeatureItem {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  color: string;
  bgColor: string;
  route?: keyof ResponsavelStackParamList;
  available: boolean;
}

const FEATURES: FeatureItem[] = [
  {
    icon: "cart-outline",
    label: "Cantina",
    color: "#FF9800",
    bgColor: "#FFF3E0",
    route: "Cantina",
    available: true,
  },
  {
    icon: "list-outline",
    label: "Extrato",
    color: "#FF5B8F",
    bgColor: "#FFF0F3",
    route: "Statement",
    available: true,
  },
  {
    icon: "add-circle-outline",
    label: "Recarregar",
    color: "#4CAF50",
    bgColor: "#E8F5E9",
    route: "Recharge",
    available: true,
  },
  {
    icon: "time-outline",
    label: "Histórico",
    color: "#9C27B0",
    bgColor: "#F3E5F5",
    available: false,
  },
];

export function WalletScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const { saldo, ultimaMovimentacao, loading, error, refetch } = useWallet();

  useFocusEffect(
    useCallback(() => {
      refetch();
    }, [refetch])
  );

  const handleFeaturePress = (item: FeatureItem) => {
    if (!item.available || !item.route) return;
    navigation.navigate(item.route as never);
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            accessibilityLabel="Voltar"
            accessibilityRole="button"
          >
            <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Carteira</Text>
          <View style={{ width: 28 }} />
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
          </View>
        ) : error ? (
          <ErrorState message={error} onRetry={refetch} />
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

            <Text style={styles.sectionTitle}>Funcionalidades</Text>

            <View style={styles.featuresGrid}>
              {FEATURES.map((item) => (
                <TouchableOpacity
                  key={item.label}
                  style={[
                    styles.featureCard,
                    !item.available && styles.featureCardDisabled,
                  ]}
                  onPress={() => handleFeaturePress(item)}
                  activeOpacity={item.available ? 0.7 : 1}
                  accessibilityLabel={item.label}
                  accessibilityRole="button"
                  accessibilityState={{ disabled: !item.available }}
                >
                  <View
                    style={[
                      styles.featureIcon,
                      { backgroundColor: item.bgColor },
                    ]}
                  >
                    <ThemedIcon name={item.icon} size={24} color={item.color} />
                  </View>
                  <Text
                    style={[
                      styles.featureLabel,
                      !item.available && styles.featureLabelDisabled,
                    ]}
                  >
                    {item.label}
                  </Text>
                  {!item.available && (
                    <Text style={styles.comingSoon}>Em breve</Text>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
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
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 16,
  },
  featuresGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  featureCard: {
    width: "48%",
    backgroundColor: "white",
    borderRadius: 24,
    padding: 20,
    alignItems: "center",
  },
  featureCardDisabled: {
    opacity: 0.6,
  },
  featureIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },
  featureLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  featureLabelDisabled: {
    color: "#999",
  },
  comingSoon: {
    fontSize: 12,
    color: "#C7C7C7",
    fontWeight: "500",
    marginTop: 4,
  },
});
