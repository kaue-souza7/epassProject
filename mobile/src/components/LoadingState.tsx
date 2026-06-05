import { View, ActivityIndicator, StyleSheet } from "react-native";

interface LoadingStateProps {
  color?: string;
  size?: "small" | "large";
}

export function LoadingState({
  color = "#FF5B8F",
  size = "large",
}: LoadingStateProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color={color} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
});
