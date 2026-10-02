import { useEffect, useState } from "react";
import {
  getActiveFontScale,
  getActiveThemeColors,
  subscribeThemeColors,
} from "./useThemedStyles";

type Version = { background: string; text: string; primary: string; fontScale: number };

function snapshot(): Version {
  const colors = getActiveThemeColors();
  return {
    background: colors.background,
    text: colors.text,
    primary: colors.primary,
    fontScale: getActiveFontScale(),
  };
}

/**
 * Faz a tela re-renderizar quando o tema ativo muda.
 *
 * Os StyleSheets são criados no escopo de módulo via `createThemedStyles`, que
 * resolve as cores e a escala de fonte sob demanda. Como a tela não consome o
 * ThemeContext diretamente, ela precisa assinar a mudança para repintar ao
 * alternar o tema, o contraste ou o tamanho da fonte.
 */
export function useThemeVersion(): Version {
  const [version, setVersion] = useState<Version>(snapshot);

  useEffect(() => subscribeThemeColors(() => setVersion(snapshot())), []);

  return version;
}
