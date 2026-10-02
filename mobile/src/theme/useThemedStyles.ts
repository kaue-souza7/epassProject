import { StyleSheet, type ImageStyle, type TextStyle, type ViewStyle } from "react-native";
import { LIGHT_COLORS, type ThemeColors } from "./tokens";

/**
 * Chave canônica → cores equivalentes em cada modo.
 *
 * O app foi escrito com cores literais em `StyleSheet.create`. Em vez de
 * reescrever dezenas de telas, mapeamos as cores já usadas para a paleta do
 * tema: cada cor da lista continua igual no claro e ganha um equivalente
 * legível no escuro.
 */
const COLOR_MAP: Record<string, { light: string; dark: string }> = {
  // Fundos de tela e superfície
  "#f5f5f7": { light: "#F5F5F7", dark: "#0E0E12" },
  "#f8f8fa": { light: "#F8F8FA", dark: "#121218" },
  "#ffffff": { light: "#FFFFFF", dark: "#1A1A20" },
  "#fff": { light: "#FFFFFF", dark: "#1A1A20" },
  "#f5f5f5": { light: "#F5F5F5", dark: "#1C1C23" },
  "#f0f0f0": { light: "#F0F0F0", dark: "#25252E" },
  "#f0f0f3": { light: "#F0F0F3", dark: "#25252E" },
  "#eeeeee": { light: "#EEEEEE", dark: "#25252E" },
  "#eee": { light: "#EEEEEE", dark: "#25252E" },
  "#efefef": { light: "#EFEFEF", dark: "#25252E" },

  // Textos
  "#1f1f1f": { light: "#1F1F1F", dark: "#F5F5F7" },
  "#000": { light: "#000000", dark: "#FFFFFF" },
  "#000000": { light: "#000000", dark: "#FFFFFF" },
  "#333": { light: "#333333", dark: "#E6E6EC" },
  "#333333": { light: "#333333", dark: "#E6E6EC" },
  "#444": { light: "#444444", dark: "#D8D8E0" },
  "#4a4a4a": { light: "#4A4A4A", dark: "#D2D2DA" },
  "#666": { light: "#666666", dark: "#B8B8C2" },
  "#666666": { light: "#666666", dark: "#B8B8C2" },
  "#7a7a7a": { light: "#7A7A7A", dark: "#A0A0AB" },
  "#888": { light: "#888888", dark: "#9C9CA6" },
  "#999": { light: "#999999", dark: "#8E8E99" },
  "#999999": { light: "#999999", dark: "#8E8E99" },
  "#a0a0a0": { light: "#A0A0A0", dark: "#8A8A95" },
  "#aaaaaa": { light: "#AAAAAA", dark: "#7E7E88" },
  "#b0b0b0": { light: "#B0B0B0", dark: "#74747F" },
  "#c7c7c7": { light: "#C7C7C7", dark: "#6A6A75" },
  "#d0d0d0": { light: "#D0D0D0", dark: "#5E5E68" },
  "#ddd": { light: "#DDDDDD", dark: "#54545E" },
  "#bbb": { light: "#BBBBBB", dark: "#63636D" },
  "#e0e0e0": { light: "#E0E0E0", dark: "#3A3A44" },
  "#e5e5e5": { light: "#E5E5E5", dark: "#30303A" },
  "#e5e5ea": { light: "#E5E5EA", dark: "#30303A" },
  "#8e8e93": { light: "#8E8E93", dark: "#8A8A95" },
  "#5a5a5a": { light: "#5A5A5A", dark: "#C2C2CC" },
  "#3a3a3a": { light: "#3A3A3A", dark: "#CECED8" },

  // Marca
  "#ff5b8f": { light: "#FF5B8F", dark: "#FF7BA3" },
  "#f84f8d": { light: "#F84F8D", dark: "#FF85A8" },
  "#f43f6e": { light: "#F43F6E", dark: "#FF7A9C" },
  "#e84a7a": { light: "#E84A7A", dark: "#FF85A8" },
  "#ff8664": { light: "#FF8664", dark: "#FF9E85" },
  "#ff9cbe": { light: "#FF9CBE", dark: "#FF9CBE" },

  // Fundos suaves derivados da marca
  "#fff0f3": { light: "#FFF0F3", dark: "#3A2430" },
  "#ffe3ec": { light: "#FFE3EC", dark: "#3A2430" },
  "#fce4ec": { light: "#FCE4EC", dark: "#3A2430" },
  "#fff5f5": { light: "#FFF5F5", dark: "#3A2226" },
  "#ffebee": { light: "#FFEBEE", dark: "#3A2226" },
  "#ffe3e3": { light: "#FFE3E3", dark: "#3E2424" },
  "#fff3d6": { light: "#FFF3D6", dark: "#3A3020" },
  "#fff3cd": { light: "#FFF3CD", dark: "#3A3020" },
  "#fff3e0": { light: "#FFF3E0", dark: "#3A2E20" },
  "#fff8e1": { light: "#FFF8E1", dark: "#39301E" },
  "#fee971": { light: "#FEE971", dark: "#6B5A18" },
  "#e8f5e9": { light: "#E8F5E9", dark: "#1F3324" },
  "#e3f2fd": { light: "#E3F2FD", dark: "#1B2A38" },
  "#f3e5f5": { light: "#F3E5F5", dark: "#2E2338" },
  "#f0efff": { light: "#F0EFFF", dark: "#232141" },

  // Telas já escuras por padrão (ex.: chat da Atena)
  "#1a1a2e": { light: "#1A1A2E", dark: "#141428" },
  "#1a1a3e": { light: "#1A1A3E", dark: "#14142E" },
  "#16213e": { light: "#16213E", dark: "#101A33" },
  "#0d0d1a": { light: "#0D0D1A", dark: "#08080F" },
  "#0f0f23": { light: "#0F0F23", dark: "#08080F" },
  "#0a0a14": { light: "#0A0A14", dark: "#08080F" },
  "#050510": { light: "#050510", dark: "#050510" },
  "#2d1b69": { light: "#2D1B69", dark: "#3B2689" },
  "#2a2a4e": { light: "#2A2A4E", dark: "#20203A" },

  // Estados
  "#27ae60": { light: "#27AE60", dark: "#3DD68C" },
  "#2ecc71": { light: "#2ECC71", dark: "#3DD68C" },
  "#4caf50": { light: "#4CAF50", dark: "#43B95B" },
  "#5cb85c": { light: "#5CB85C", dark: "#43B95B" },
  "#66bb6a": { light: "#66BB6A", dark: "#43B95B" },
  "#34c759": { light: "#34C759", dark: "#3DD68C" },
  "#2e7d32": { light: "#2E7D32", dark: "#5FBF6B" },
  "#e74c3c": { light: "#E74C3C", dark: "#FF6B5E" },
  "#f44336": { light: "#F44336", dark: "#FF6B5E" },
  "#ef5350": { light: "#EF5350", dark: "#FF6B5E" },
  "#ff6b5e": { light: "#FF6B5E", dark: "#FF6B5E" },
  "#f39c12": { light: "#F39C12", dark: "#F5B942" },
  "#ff9800": { light: "#FF9800", dark: "#F5B942" },
  "#f0ad4e": { light: "#F0AD4E", dark: "#F5B942" },
  "#ffb800": { light: "#FFB800", dark: "#F5B942" },
  "#b26a00": { light: "#B26A00", dark: "#E0A94F" },
  "#856404": { light: "#856404", dark: "#D9B451" },
  "#b7791f": { light: "#B7791F", dark: "#D9A551" },
  "#c62828": { light: "#C62828", dark: "#FF6B5E" },
  "#6c63ff": { light: "#6C63FF", dark: "#8E86FF" },
  "#a78bfa": { light: "#A78BFA", dark: "#B9A2FC" },
  "#9b59b6": { light: "#9B59B6", dark: "#B87DD2" },
  "#9c27b0": { light: "#9C27B0", dark: "#B87DD2" },
  "#1565c0": { light: "#1565C0", dark: "#6BA6FF" },
  "#2d7ff9": { light: "#2D7FF9", dark: "#6BA6FF" },
  "#5bc0de": { light: "#5BC0DE", dark: "#7FD3EA" },
  "#ff6b6b": { light: "#FF6B6B", dark: "#FF8A8A" },
};

/** Cores usadas como branco puro que não devem ser mapeadas. */
const FIXED = new Set(["#fff"]);

/**
 * Papéis semânticos das cores literais mais usadas.
 *
 * O `COLOR_MAP` acima resolve claro/escuro, mas o alto contraste reescreve a
 * paleta (`applyHighContrast`) com valores diferentes dos originais. Sem esta
 * tabela, ativar o alto contraste mudaria o fundo e nada mais. Aqui ligamos a
 * cor literal ao seu papel para que o valor venha sempre da paleta ativa.
 */
const SEMANTIC_ROLES: Record<string, keyof ThemeColors> = {
  // Fundos
  "#f5f5f7": "background",
  "#f8f8fa": "background",
  // Superfícies
  "#ffffff": "surface",
  "#f5f5f5": "surface",
  // Textos principais
  "#1f1f1f": "text",
  "#000": "text",
  "#000000": "text",
  "#333": "text",
  "#333333": "text",
  "#3a3a3a": "text",
  "#4a4a4a": "text",
  "#5a5a5a": "text",
  // Textos secundários
  "#666": "textMuted",
  "#666666": "textMuted",
  "#7a7a7a": "textMuted",
  "#888": "textMuted",
  "#888888": "textMuted",
  "#999": "textMuted",
  "#999999": "textMuted",
  "#a0a0a0": "textMuted",
  "#aaaaaa": "textMuted",
  "#b0b0b0": "textMuted",
  // Marca
  "#ff5b8f": "primary",
  "#f84f8d": "primary",
  "#f43f6e": "primary",
  "#e84a7a": "primary",
  // Bordas
  "#c7c7c7": "border",
  "#d0d0d0": "border",
  "#ddd": "border",
  "#e5e5e5": "border",
  "#e5e5ea": "border",
  // Estados
  "#27ae60": "success",
  "#2ecc71": "success",
  "#f39c12": "warning",
  "#ff9800": "warning",
  "#e74c3c": "danger",
  "#f44336": "danger",
  "#2d7ff9": "info",
  "#1565c0": "info",
};

/** Paleta ativa, publicada pelo ThemeProvider. */
let activeColors: ThemeColors = LIGHT_COLORS;

/** Modo e ajustes ativos; inferidos pela paleta quebrava o alto contraste. */
let activeIsDark = false;
let activeHighContrast = false;

/** Escala de fonte ativa, publicada pelo ThemeProvider. */
let activeFontScale = 1;

export function setActiveThemeColors(
  colors: ThemeColors,
  isDark: boolean,
  highContrast: boolean,
) {
  const mudou =
    colors.background !== activeColors.background ||
    colors.text !== activeColors.text ||
    colors.surface !== activeColors.surface ||
    isDark !== activeIsDark ||
    highContrast !== activeHighContrast;
  activeColors = colors;
  activeIsDark = isDark;
  activeHighContrast = highContrast;
  if (mudou) notifyThemeChanged();
}

export function setActiveFontScale(scale: number) {
  if (scale === activeFontScale) return;
  activeFontScale = scale;
  notifyThemeChanged();
}

export function getActiveFontScale(): number {
  return activeFontScale;
}

export function getActiveThemeColors(): ThemeColors {
  return activeColors;
}

type ThemeListener = () => void;
const themeListeners = new Set<ThemeListener>();

/** Avisa as telas assinantes que a paleta ativa mudou. */
export function notifyThemeChanged() {
  themeListeners.forEach((listener) => listener());
}

export function subscribeThemeColors(listener: ThemeListener): () => void {
  themeListeners.add(listener);
  return () => {
    themeListeners.delete(listener);
  };
}

function resolve(value: string, prop?: string): string {
  const key = value.toLowerCase();

  // `white` é ambíguo no código legado: como fundo precisa virar `surface`
  // no escuro, como texto sobre a cor da marca precisa continuar branco.
  if (key === "white") {
    if (prop === "backgroundColor") {
      return activeHighContrast
        ? activeColors.surface
        : activeIsDark
          ? "#1A1A20"
          : "#FFFFFF";
    }
    return value;
  }

  if (FIXED.has(key)) return value;
  const entry = COLOR_MAP[key];
  if (!entry) return value;

  if (activeHighContrast) {
    const role = SEMANTIC_ROLES[key];
    if (role) return activeColors[role];
  }

  return activeIsDark ? entry.dark : entry.light;
}

function mapValue(value: unknown, prop?: string): unknown {
  if (typeof value === "string") return resolve(value, prop);
  if (typeof value === "number") return value;
  if (Array.isArray(value)) return value.map((item) => mapValue(item, prop));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) {
      // A escala de fonte aumenta apenas o texto, preservando o layout
      // (ícones, Dimensions e espaçamentos não são afetados).
      if ((key === "fontSize" || key === "lineHeight") && typeof item === "number") {
        out[key] = Math.round(item * activeFontScale);
      } else {
        out[key] = mapValue(item, key);
      }
    }
    return out;
  }
  return value;
}

type StyleValue = ViewStyle | TextStyle | ImageStyle;
type StyleFactory = Record<string, StyleValue>;

const cache = new WeakMap<StyleFactory, Map<string, Record<string, unknown>>>();

function isDarkActive(): boolean {
  return activeIsDark;
}

function bucketFor(factory: StyleFactory, isDark: boolean): Record<string, unknown> {
  let buckets = cache.get(factory);
  if (!buckets) {
    buckets = new Map();
    cache.set(factory, buckets);
  }
  const key = `${isDark ? "dark" : "light"}@${activeFontScale}@${
    activeHighContrast ? "hc" : "n"
  }`;
  let bucket = buckets.get(key);
  if (!bucket) {
    bucket = StyleSheet.create(mapValue(factory) as StyleFactory) as Record<
      string,
      unknown
    >;
    buckets.set(key, bucket);
  }
  return bucket;
}

/**
 * Substitui `StyleSheet.create` para que as cores literais passem pelo tema.
 *
 * O resultado é um Proxy que resolve cada chave sob demanda e memoriza por
 * modo, então a troca de tema passa a valer em toda a tela sem reescrever os
 * blocos de estilo. A tela re-renderiza na troca porque o ThemeContext é
 * consumido por ela.
 */
export function createThemedStyles<T extends StyleFactory>(factory: T): T {
  return new Proxy(factory, {
    get(_target, prop: string) {
      return bucketFor(factory, isDarkActive())[prop];
    },
    has(_target, prop: string) {
      return prop in bucketFor(factory, isDarkActive());
    },
  }) as T;
}
