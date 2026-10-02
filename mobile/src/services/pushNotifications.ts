import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { Platform } from "react-native";
import * as SecureStore from "./storage";
import { api } from "../api/client";

const PUSH_TOKEN_KEY = "epass_push_token";
const CANAL_AVISOS = "avisos";

/** Handler de foreground: mostra a notificação mesmo com o app aberto. */
export function configurarHandlerForeground(): void {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

/** Canal Android dedicado a avisos (prioridade alta). */
export async function garantirCanalAndroid(): Promise<void> {
  if (Platform.OS !== "android") return;
  await Notifications.setNotificationChannelAsync(CANAL_AVISOS, {
    name: "Avisos e mensagens",
    importance: Notifications.AndroidImportance.HIGH,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#FF5B8F",
    sound: "default",
    lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
  });
}

function projectId(): string | undefined {
  return (
    (Constants?.expoConfig as any)?.extra?.eas?.projectId ??
    (Constants as any)?.easConfig?.projectId ??
    undefined
  );
}

export interface ResultadoPushToken {
  token: string | null;
  /** Motivo legível quando o token não pôde ser obtido (para feedback na UI). */
  motivo: string | null;
}

/**
 * Solicita permissão e obtém o Expo push token.
 *
 * Retorna `{ token: null, motivo }` quando: não é dispositivo físico, permissão
 * negada, projeto EAS sem projectId ou falha de rede. O app segue funcionando
 * com a central in-app (e o polling), que é o fallback garantido.
 */
export async function obterPushToken(): Promise<ResultadoPushToken> {
  if (!Device.isDevice) {
    return {
      token: null,
      motivo:
        "Emulador/simulador não recebe push remoto. Use um dispositivo físico.",
    };
  }

  const { status: statusAtual } = await Notifications.getPermissionsAsync();
  let status = statusAtual;
  if (status !== "granted") {
    const pedido = await Notifications.requestPermissionsAsync();
    status = pedido.status;
  }
  if (status !== "granted") {
    return {
      token: null,
      motivo:
        "Permissão de notificações negada. Habilite nas configurações do sistema.",
    };
  }

  await garantirCanalAndroid();

  const pid = projectId();
  if (!pid) {
    return {
      token: null,
      motivo:
        "Projeto Expo sem projectId (EAS) configurado — push remoto indisponível " +
        "no Expo Go. Os avisos continuam chegando na Central de Notificações.",
    };
  }

  try {
    const { data } = await Notifications.getExpoPushTokenAsync({ projectId: pid });
    await SecureStore.setItemAsync(PUSH_TOKEN_KEY, data);
    return { token: data, motivo: null };
  } catch (err) {
    return {
      token: null,
      motivo:
        err instanceof Error
          ? `Falha ao obter token de push: ${err.message}`
          : "Falha ao obter token de push.",
    };
  }
}

export async function tokenArmazenado(): Promise<string | null> {
  return SecureStore.getItemAsync(PUSH_TOKEN_KEY);
}

/** Registra o token no backend (idempotente). */
export async function registrarPushTokenNoBackend(token: string): Promise<boolean> {
  try {
    await api.post("/notificacoes/push-tokens", { token, plataforma: "expo" });
    return true;
  } catch {
    return false;
  }
}

/** Remove o token no backend e do armazenamento seguro. */
export async function desregistrarPushToken(): Promise<void> {
  const token = await tokenArmazenado();
  if (token) {
    try {
      await api.delete("/notificacoes/push-tokens", { params: { token } });
    } catch {
      // best-effort: logout não pode falhar por causa do push
    }
  }
  await SecureStore.deleteItemAsync(PUSH_TOKEN_KEY);
}
