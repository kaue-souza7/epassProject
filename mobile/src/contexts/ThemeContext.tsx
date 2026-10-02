import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { useColorScheme } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  applyHighContrast,
  DARK_COLORS,
  FONT_SCALE_VALUES,
  LIGHT_COLORS,
  type FontScaleId,
  type ThemeColors,
} from "../theme/tokens";
import { setActiveFontScale, setActiveThemeColors } from "../theme/useThemedStyles";
import { createThemedStyles } from "../theme/useThemedStyles";

const THEME_KEY = "epass_theme";
const FONT_SCALE_KEY = "epass_font_scale";
const HIGH_CONTRAST_KEY = "epass_high_contrast";
const KEEP_AWAKE_KEY = "epass_keep_awake";

export type ThemeMode = "light" | "dark";

interface ThemeContextType {
  theme: ThemeMode;
  isDark: boolean;
  colors: ThemeColors;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
  fontScale: number;
  fontScaleId: FontScaleId;
  setFontScaleId: (id: FontScaleId) => void;
  highContrast: boolean;
  setHighContrast: (value: boolean) => void;
  keepAwake: boolean;
  setKeepAwake: (value: boolean) => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

function isThemeMode(value: unknown): value is ThemeMode {
  return value === "light" || value === "dark";
}

function isFontScaleId(value: string | null): value is FontScaleId {
  return value !== null && value in FONT_SCALE_VALUES;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [theme, setThemeState] = useState<ThemeMode>("light");
  const [fontScaleId, setFontScaleIdState] = useState<FontScaleId>("padrao");
  const [highContrast, setHighContrastState] = useState(false);
  const [keepAwake, setKeepAwakeState] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const [storedTheme, storedScale, storedContrast, storedAwake] =
        await AsyncStorage.multiGet([
          THEME_KEY,
          FONT_SCALE_KEY,
          HIGH_CONTRAST_KEY,
          KEEP_AWAKE_KEY,
        ]);
      if (!active) return;

      if (isThemeMode(storedTheme[1])) {
        setThemeState(storedTheme[1]);
      } else {
        setThemeState(systemScheme === "dark" ? "dark" : "light");
      }

      if (isFontScaleId(storedScale[1])) {
        setFontScaleIdState(storedScale[1]);
      }
      if (storedContrast[1] === "true") setHighContrastState(true);
      if (storedAwake[1] === "true") setKeepAwakeState(true);

      setLoaded(true);
    })();
    return () => {
      active = false;
    };
  }, [systemScheme]);

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeState(mode);
    AsyncStorage.setItem(THEME_KEY, mode).catch(() => {});
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const next = current === "light" ? "dark" : "light";
      AsyncStorage.setItem(THEME_KEY, next).catch(() => {});
      return next;
    });
  }, []);

  const setFontScaleId = useCallback((id: FontScaleId) => {
    setFontScaleIdState(id);
    AsyncStorage.setItem(FONT_SCALE_KEY, id).catch(() => {});
  }, []);

  const setHighContrast = useCallback((value: boolean) => {
    setHighContrastState(value);
    AsyncStorage.setItem(HIGH_CONTRAST_KEY, String(value)).catch(() => {});
  }, []);

  const setKeepAwake = useCallback((value: boolean) => {
    setKeepAwakeState(value);
    AsyncStorage.setItem(KEEP_AWAKE_KEY, String(value)).catch(() => {});
  }, []);

  const colors = useMemo(() => {
    const base = theme === "dark" ? DARK_COLORS : LIGHT_COLORS;
    return highContrast ? applyHighContrast(base, theme === "dark") : base;
  }, [theme, highContrast]);

  // Publica a paleta e a escala fora do React para que `createThemedStyles`
  // (usado no escopo de módulo pelas telas) resolva os valores do tema ativo.
  useEffect(() => {
    setActiveThemeColors(colors, theme === "dark", highContrast);
  }, [colors, theme, highContrast]);

  useEffect(() => {
    setActiveFontScale(FONT_SCALE_VALUES[fontScaleId]);
  }, [fontScaleId]);

  const value = useMemo<ThemeContextType>(
    () => ({
      theme,
      isDark: theme === "dark",
      colors,
      toggleTheme,
      setTheme,
      fontScale: FONT_SCALE_VALUES[fontScaleId],
      fontScaleId,
      setFontScaleId,
      highContrast,
      setHighContrast,
      keepAwake,
      setKeepAwake,
    }),
    [
      theme,
      colors,
      toggleTheme,
      setTheme,
      fontScaleId,
      setFontScaleId,
      highContrast,
      setHighContrast,
      keepAwake,
      setKeepAwake,
    ]
  );

  if (!loaded) return null;

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within ThemeProvider");
  return context;
}
