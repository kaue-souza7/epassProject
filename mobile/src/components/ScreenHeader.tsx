import { View, Text, TouchableOpacity } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { createThemedStyles } from "../theme/useThemedStyles";
import { useThemeVersion } from "../theme/useThemeVersion";
import { ThemedIcon } from "../theme/ThemedIcon";

interface ScreenHeaderProps {
  title: string;
  subtitle?: string;
}

/**
 * Altura mínima do topo antes de somar o inset da área segura.
 *
 * `insets.top` é 0 em aparelhos sem notch, e o valor original do padding
 * era 24. Sem este piso, esses aparelhos ficariam colados na borda.
 */
const MIN_TOP_PADDING = 16;
const TOP_GAP = 8;

export function ScreenHeader({ title, subtitle }: ScreenHeaderProps) {
  // Repinta quando a paleta ou a escala de fonte mudam: os estilos são
  // resolvidos sob demanda por `createThemedStyles`, então sem esta
  // assinatura o título ficaria com a cor do tema anterior.
  useThemeVersion();
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();

  return (
    <View
      style={[
        styles.header,
        { paddingTop: Math.max(insets.top, MIN_TOP_PADDING) + TOP_GAP },
      ]}
    >
      <TouchableOpacity
        onPress={() => navigation.goBack()}
        accessibilityLabel="Voltar"
        accessibilityRole="button"
        hitSlop={8}
      >
        <ThemedIcon name="arrow-back" size={24} color="#1F1F1F" />
      </TouchableOpacity>
      <View style={styles.headerInfo}>
        <Text style={styles.headerTitle} numberOfLines={2}>
          {title}
        </Text>
        {subtitle && (
          <Text style={styles.headerSubtitle} numberOfLines={2}>
            {subtitle}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = createThemedStyles({
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingBottom: 8,
    gap: 16,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  headerSubtitle: {
    fontSize: 13,
    color: "#888",
    marginTop: 2,
  },
});
