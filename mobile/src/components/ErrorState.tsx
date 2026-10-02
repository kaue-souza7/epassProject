import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { createThemedStyles } from "../theme/useThemedStyles";
import { ThemedIcon } from "../theme/ThemedIcon";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  icon?: keyof typeof Ionicons.glyphMap;
}

export function ErrorState({
  message,
  onRetry,
  retryLabel = "Tentar novamente",
  icon = "alert-circle-outline",
}: ErrorStateProps) {
  return (
    <View style={styles.container}>
      <ThemedIcon name={icon} size={56} color="#FF5B8F" />
      <Text style={styles.message}>{message}</Text>
      {onRetry && (
        <TouchableOpacity
          style={styles.retryButton}
          onPress={onRetry}
          accessibilityLabel={retryLabel}
          accessibilityRole="button"
        >
          <Text style={styles.retryText}>{retryLabel}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  message: {
    color: "#333",
    fontSize: 15,
    fontWeight: "500",
    textAlign: "center",
    marginTop: 16,
    lineHeight: 22,
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
});
