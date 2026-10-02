// Tokens de tema do app. As telas devem consumir `useTheme()` e aplicar
// `colors.*` em StyleSheets criados via `createStyles(colors)`, em vez de usar
// cores literais, para que modo escuro e alto contraste valham em todo o app.

export interface ThemeColors {
  /** Fundo padrão das telas. */
  background: string;
  /** Fundo de cards, superfícies elevadas e modais. */
  surface: string;
  /** Fundo de inputs, chips e itens pressionados. */
  surfaceAlt: string;
  /** Cor principal da marca (rosa) e ações primárias. */
  primary: string;
  /** Versão apagada da cor primária, para fundos suaves. */
  primarySoft: string;
  /** Texto primário. */
  text: string;
  /** Texto secundário, legendas e labels. */
  textMuted: string;
  /** Texto sobre a cor primária. */
  onPrimary: string;
  /** Linhas divisórias e bordas de card. */
  border: string;
  /** Sucesso. */
  success: string;
  /** Aviso. */
  warning: string;
  /** Erro. */
  danger: string;
  /** Info. */
  info: string;
  /** Overlay escurecido por trás de modais. */
  overlay: string;
}

const BRAND = "#FF5B8F";

/** Paleta do modo claro. */
export const LIGHT_COLORS: ThemeColors = {
  background: "#F5F5F7",
  surface: "#FFFFFF",
  surfaceAlt: "#F0F0F3",
  primary: BRAND,
  primarySoft: "#FFE3EC",
  text: "#1F1F1F",
  textMuted: "#7A7A7A",
  onPrimary: "#FFFFFF",
  border: "#E5E5E5",
  success: "#27AE60",
  warning: "#F39C12",
  danger: "#E74C3C",
  info: "#2D7FF9",
  overlay: "rgba(0,0,0,0.45)",
};

/** Paleta do modo escuro. */
export const DARK_COLORS: ThemeColors = {
  background: "#0E0E12",
  surface: "#1A1A20",
  surfaceAlt: "#25252E",
  primary: "#FF7BA3",
  primarySoft: "#3A2430",
  text: "#F5F5F7",
  textMuted: "#A0A0AB",
  onPrimary: "#1A0A10",
  border: "#30303A",
  success: "#3DD68C",
  warning: "#F5B942",
  danger: "#FF6B5E",
  info: "#6BA6FF",
  overlay: "rgba(0,0,0,0.7)",
};

/**
 * Alto contraste não é um terceiro tema: é um ajuste sobre a paleta ativa.
 * Textos e bordas ficam mais fortes, e o fundo alterna para preto/branco puro
 * para atender contraste WCAG AAA nos textos principais.
 */
export function applyHighContrast(
  base: ThemeColors,
  isDark: boolean,
): ThemeColors {
  if (isDark) {
    return {
      ...base,
      background: "#000000",
      surface: "#0D0D0D",
      surfaceAlt: "#1F1F1F",
      text: "#FFFFFF",
      textMuted: "#D6D6D6",
      border: "#6E6E6E",
      primary: "#FF9CBE",
      primarySoft: "#3D2831",
    };
  }
  return {
    ...base,
    background: "#FFFFFF",
    surface: "#FFFFFF",
    surfaceAlt: "#EFEFEF",
    text: "#000000",
    textMuted: "#3A3A3A",
    border: "#5A5A5A",
    primary: "#C2185B",
    primarySoft: "#FCE4EC",
  };
}

/** Escalas de fonte disponíveis na tela de acessibilidade. */
export const FONT_SCALES = [
  { id: "pequeno", label: "Pequeno", scale: 0.9 },
  { id: "padrao", label: "Padrão", scale: 1 },
  { id: "grande", label: "Grande", scale: 1.15 },
  { id: "muito-grande", label: "Muito grande", scale: 1.3 },
] as const;

export type FontScaleId = (typeof FONT_SCALES)[number]["id"];

export const FONT_SCALE_VALUES: Record<FontScaleId, number> = FONT_SCALES.reduce(
  (acc, item) => {
    acc[item.id] = item.scale;
    return acc;
  },
  {} as Record<FontScaleId, number>,
);
