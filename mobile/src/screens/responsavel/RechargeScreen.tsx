import { useRef, useState } from "react";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useRecharge } from "../../hooks/useWallet";
import { getApiErrorMessage } from "../../api/errors";
import { useToast } from "../../components/Toast";
import type { ResponsavelStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Recharge">;

const QUICK_VALUES = [10, 20, 50, 100];

function novaChaveIdempotencia(): string {
  return `recarga-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function RechargeScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const toast = useToast();
  const { realizarRecarga, loading } = useRecharge();
  const [amount, setAmount] = useState("");
  // Reutilizada em retentativas do mesmo formulário: evita dupla cobrança
  // quando o usuário toca duas vezes ou a requisição é reenviada.
  const idempotencyKeyRef = useRef(novaChaveIdempotencia());

  const numericAmount = parseFloat(amount.replace(",", "."));

  const handleQuickAmount = (value: number) => {
    setAmount(value.toFixed(2).replace(".", ","));
  };

  const handleConfirm = async () => {
    const valorArredondado = Math.round(numericAmount * 100) / 100;
    if (isNaN(valorArredondado) || valorArredondado <= 0) {
      toast.warning("Informe um valor maior que zero.");
      return;
    }

    try {
      await realizarRecarga(valorArredondado, idempotencyKeyRef.current);
      idempotencyKeyRef.current = novaChaveIdempotencia();
      toast.success(
        `Foram adicionados R$ ${valorArredondado.toFixed(2)} à carteira.`,
      );
      setTimeout(() => navigation.goBack(), 1100);
    } catch (err: unknown) {
      toast.error(getApiErrorMessage(err, "Erro ao realizar recarga"));
    }
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <View style={styles.header}>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              accessibilityLabel="Voltar"
              accessibilityRole="button"
            >
              <ThemedIcon name="chevron-back" size={28} color="#1F1F1F" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Recarregar</Text>
            <View style={{ width: 28 }} />
          </View>

          <View style={styles.content}>
            <Text style={styles.label}>Valor da recarga</Text>

            <View style={styles.inputContainer}>
              <Text style={styles.currencySign}>R$</Text>
              <TextInput
                style={styles.input}
                keyboardType="decimal-pad"
                placeholder="0,00"
                placeholderTextColor="#C7C7C7"
                value={amount}
                onChangeText={setAmount}
              />
            </View>

            <View style={styles.quickRow}>
              {QUICK_VALUES.map((val) => (
                <TouchableOpacity
                  key={val}
                  style={[
                    styles.quickButton,
                    numericAmount === val && styles.quickButtonActive,
                  ]}
                  onPress={() => handleQuickAmount(val)}
                  accessibilityLabel={`Recarregar R$ ${val}`}
                  accessibilityRole="button"
                >
                  <Text
                    style={[
                      styles.quickButtonText,
                      numericAmount === val && styles.quickButtonTextActive,
                    ]}
                  >
                    R$ {val}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TouchableOpacity
              style={[
                styles.confirmButton,
                (isNaN(numericAmount) || numericAmount <= 0) && styles.confirmButtonDisabled,
              ]}
              onPress={handleConfirm}
              disabled={isNaN(numericAmount) || numericAmount <= 0 || loading}
              accessibilityLabel="Confirmar recarga"
              accessibilityRole="button"
            >
              {loading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.confirmButtonText}>Confirmar recarga</Text>
              )}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
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
  flex: {
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
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 40,
  },
  label: {
    fontSize: 16,
    fontWeight: "500",
    color: "#7A7A7A",
    marginBottom: 16,
    textAlign: "center",
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 36,
    paddingHorizontal: 24,
    height: 80,
    marginBottom: 24,
  },
  currencySign: {
    fontSize: 28,
    fontWeight: "700",
    color: "#1F1F1F",
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 28,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  quickRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 32,
  },
  quickButton: {
    flex: 1,
    backgroundColor: "white",
    borderRadius: 16,
    paddingVertical: 14,
    alignItems: "center",
  },
  quickButtonActive: {
    backgroundColor: "#FF5B8F",
  },
  quickButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  quickButtonTextActive: {
    color: "white",
  },
  confirmButton: {
    backgroundColor: "#FF5B8F",
    borderRadius: 999,
    height: 56,
    justifyContent: "center",
    alignItems: "center",
  },
  confirmButtonDisabled: {
    opacity: 0.5,
  },
  confirmButtonText: {
    color: "white",
    fontSize: 17,
    fontWeight: "700",
  },
});
