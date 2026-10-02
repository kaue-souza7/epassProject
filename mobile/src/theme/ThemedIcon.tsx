import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { getActiveThemeColors } from "./useThemedStyles";
import { useThemeVersion } from "./useThemeVersion";

type IconProps = ComponentProps<typeof Ionicons>;

/**
 * Ícone que respeita o tema.
 *
 * As telas passam cores literais para `Ionicons` (ex.: `color="#1F1F1F"`).
 * Este wrapper remapeia essa cor para a paleta ativa, para que os ícones
 * continuem legíveis no modo escuro e no alto contraste.
 */
export function ThemedIcon(props: IconProps) {
  // Re-renderiza quando a paleta muda para reavaliar a cor.
  useThemeVersion();
  const colors = getActiveThemeColors();
  return <Ionicons {...props} color={remapIconColor(props.color, colors)} />;
}

const DARK_ICON_LIGHT: Record<string, string> = {
  "#1f1f1f": "#F5F5F7",
  "#000000": "#FFFFFF",
  "#000": "#FFFFFF",
  "#333333": "#E6E6EC",
  "#333": "#E6E6EC",
  "#444444": "#D8D8E0",
  "#444": "#D8D8E0",
  "#4a4a4a": "#D2D2DA",
  "#666666": "#B8B8C2",
  "#666": "#B8B8C2",
  "#7a7a7a": "#A0A0AB",
  "#888888": "#9C9CA6",
  "#888": "#9C9CA6",
  "#999999": "#8E8E99",
  "#999": "#8E8E99",
  "#a0a0a0": "#8A8A95",
  "#aaaaaa": "#7E7E88",
  "#b0b0b0": "#74747F",
  "#c7c7c7": "#6A6A75",
  "#d0d0d0": "#5E5E68",
  "#e0e0e0": "#3A3A44",
  "#e5e5e5": "#30303A",
};

const HIGH_CONTRAST_LIGHT: Record<string, string> = {
  "#7a7a7a": "#3A3A3A",
  "#888888": "#3A3A3A",
  "#888": "#3A3A3A",
  "#999999": "#3A3A3A",
  "#999": "#3A3A3A",
  "#a0a0a0": "#3A3A3A",
  "#aaaaaa": "#3A3A3A",
  "#b0b0b0": "#3A3A3A",
  "#c7c7c7": "#3A3A3A",
  "#d0d0d0": "#3A3A3A",
  "#e0e0e0": "#3A3A3A",
  "#e5e5e5": "#3A3A3A",
};

function remapIconColor(
  color: IconProps["color"],
  colors: ReturnType<typeof getActiveThemeColors>,
): string {
  if (typeof color !== "string") return colors.text;
  const key = color.toLowerCase();

  const isDark = colors.background === "#0E0E12" || colors.background === "#000000";
  if (isDark) {
    const escuro = DARK_ICON_LIGHT[key];
    if (escuro) return escuro;
  }
  const isHighContrastLight = colors.background === "#FFFFFF" && colors.text === "#000000";
  if (isHighContrastLight) {
    const hc = HIGH_CONTRAST_LIGHT[key];
    if (hc) return hc;
  }
  return color;
}
