import { useEffect } from "react";
import {
  activateKeepAwakeAsync,
  deactivateKeepAwake,
} from "expo-keep-awake";
import { useTheme } from "../contexts/ThemeContext";

const TAG = "epass-leitura";

/**
 * Mantém a tela ligada enquanto o componente está montado, se o usuário
 * tiver ligado a preferência "Manter tela ligada" em Acessibilidade.
 *
 * Deve ser usado nas telas de leitura (boletim, avisos, documentos, pedidos)
 * para o conteúdo não apagar enquanto a pessoa está lendo.
 */
export function KeepAwake() {
  const { keepAwake } = useTheme();

  useEffect(() => {
    if (!keepAwake) return;

    activateKeepAwakeAsync(TAG).catch(() => {
      // Sem permissão de keep-awake a tela apaga normalmente.
    });

    return () => {
      deactivateKeepAwake(TAG);
    };
  }, [keepAwake]);

  return null;
}
