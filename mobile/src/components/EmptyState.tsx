import { Text, View } from "react-native";
import { ThemedIcon } from "../theme/ThemedIcon";
import { createThemedStyles } from "../theme/useThemedStyles";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <View style={styles.container}>
      {icon ? (
        <View style={styles.iconWrap}>
          <ThemedIcon name={icon as never} size={30} color="#B0B0B0" />
        </View>
      ) : null}
      <Text style={styles.title}>{title}</Text>
      {description ? <Text style={styles.description}>{description}</Text> : null}
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    alignItems: "center",
    paddingVertical: 40,
    paddingHorizontal: 24,
    gap: 8,
  },
  iconWrap: {
    width: 64,
    height: 64,
    borderRadius: 22,
    backgroundColor: "#F0F0F3",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
    textAlign: "center",
  },
  description: {
    fontSize: 13,
    color: "#7A7A7A",
    textAlign: "center",
    lineHeight: 19,
  },
});
