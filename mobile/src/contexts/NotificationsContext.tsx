import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Platform,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import * as Notifications from "expo-notifications";
import { useAuth } from "./AuthContext";
import { createThemedStyles } from "../theme/useThemedStyles";
import {
  abrirNotificacaoNoApp,
  type NotificacaoPayload,
} from "../navigation/navigationRef";
import {
  configurarHandlerForeground,
  garantirCanalAndroid,
  obterPushToken,
  registrarPushTokenNoBackend,
  tokenArmazenado,
} from "../services/pushNotifications";

interface NotificationsContextType {
  pushAtivo: boolean;
  /** Incrementa a cada notificação recebida para as telas recarregarem. */
  versao: number;
  /** Motivo legível quando o push não pôde ser ativado. */
  motivoPush: string | null;
  solicitarPermissao: () => Promise<{ ok: boolean; motivo: string | null }>;
}

const NotificationsContext = createContext<NotificationsContextType | null>(null);

interface BannerNotificacao {
  titulo: string;
  mensagem: string;
  payload: NotificacaoPayload;
}

function payloadDoEvento(dados: Record<string, unknown>): NotificacaoPayload {
  return {
    entidade_tipo: (dados?.entidade_tipo as string | undefined) ?? null,
    entidade_id: (dados?.entidade_id as string | undefined) ?? null,
    aviso_id: (dados?.aviso_id as string | undefined) ?? null,
    ocorrencia_id: (dados?.ocorrencia_id as string | undefined) ?? null,
  };
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [pushAtivo, setPushAtivo] = useState(false);
  const [motivoPush, setMotivoPush] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [banner, setBanner] = useState<BannerNotificacao | null>(null);
  const registrandoRef = useRef(false);
  const bannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mostrarBanner = useCallback((novo: BannerNotificacao) => {
    setBanner(novo);
    if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);
    bannerTimerRef.current = setTimeout(() => setBanner(null), 7000);
  }, []);

  const registrar = useCallback(async (): Promise<{ ok: boolean; motivo: string | null }> => {
    if (registrandoRef.current) return { ok: false, motivo: "Registro em andamento." };
    registrandoRef.current = true;
    try {
      const armazenado = await tokenArmazenado();
      if (armazenado) {
        const ok = await registrarPushTokenNoBackend(armazenado);
        const motivo = ok ? null : "Não foi possível registrar o dispositivo no servidor.";
        setPushAtivo(ok);
        setMotivoPush(motivo);
        return { ok, motivo };
      }

      const { token, motivo } = await obterPushToken();
      if (!token) {
        setPushAtivo(false);
        setMotivoPush(motivo);
        return { ok: false, motivo };
      }
      const ok = await registrarPushTokenNoBackend(token);
      const motivoFinal = ok ? null : "Não foi possível registrar o dispositivo no servidor.";
      setPushAtivo(ok);
      setMotivoPush(motivoFinal);
      return { ok, motivo: motivoFinal };
    } finally {
      registrandoRef.current = false;
    }
  }, []);

  const solicitarPermissao = useCallback(() => registrar(), [registrar]);

  // Configuração única do handler/canal
  useEffect(() => {
    configurarHandlerForeground();
    void garantirCanalAndroid();
  }, []);

  // Registro do token após autenticar
  useEffect(() => {
    if (!isAuthenticated) {
      setPushAtivo(false);
      setMotivoPush(null);
      return;
    }
    let mounted = true;
    (async () => {
      const { ok } = await registrar();
      if (mounted) setPushAtivo(ok);
    })();
    return () => {
      mounted = false;
    };
  }, [isAuthenticated, registrar]);

  useEffect(() => {
    // Notificação recebida com app aberto: além do banner do sistema,
    // mostra o banner in-app (algumas plataformas/configurações não exibem
    // o banner do sistema em foreground).
    const recebida = Notifications.addNotificationReceivedListener((notificacao) => {
      setVersao((v) => v + 1);
      const dados = notificacao.request.content.data as Record<string, unknown>;
      if (Platform.OS !== "web") {
        mostrarBanner({
          titulo: notificacao.request.content.title ?? "Nova notificação",
          mensagem: notificacao.request.content.body ?? "",
          payload: payloadDoEvento(dados),
        });
      }
    });

    const respondida = Notifications.addNotificationResponseReceivedListener((resposta) => {
      const dados = resposta.notification.request.content.data as Record<string, unknown>;
      setVersao((v) => v + 1);
      setBanner(null);
      abrirNotificacaoNoApp(payloadDoEvento(dados));
    });

    // App aberto a partir de uma notificação com ele fechado
    try {
      Notifications.getLastNotificationResponseAsync()
        ?.then((resposta) => {
          if (!resposta) return;
          const dados = resposta.notification.request.content.data as Record<string, unknown>;
          setTimeout(() => abrirNotificacaoNoApp(payloadDoEvento(dados)), 800);
        })
        .catch(() => undefined);
    } catch {
      // plataforma sem suporte (ex.: web)
    }

    return () => {
      recebida.remove();
      respondida.remove();
    };
  }, [mostrarBanner]);

  const topoBanner =
    Platform.OS === "android" ? (StatusBar.currentHeight ?? 24) + 8 : 54;

  return (
    <NotificationsContext.Provider
      value={{ pushAtivo, versao, motivoPush, solicitarPermissao }}
    >
      {children}
      {banner && (
        <TouchableOpacity
          style={[styles.banner, { top: topoBanner }]}
          activeOpacity={0.9}
          onPress={() => {
            const payload = banner.payload;
            setBanner(null);
            abrirNotificacaoNoApp(payload);
          }}
          accessibilityRole="button"
          accessibilityLabel={`Notificação: ${banner.titulo}`}
        >
          <View style={styles.bannerIcone}>
            <Text style={styles.bannerIconeTexto}>🔔</Text>
          </View>
          <View style={styles.bannerConteudo}>
            <Text style={styles.bannerTitulo} numberOfLines={1}>
              {banner.titulo}
            </Text>
            <Text style={styles.bannerMensagem} numberOfLines={2}>
              {banner.mensagem}
            </Text>
          </View>
          <Text
            style={styles.bannerFechar}
            onPress={() => setBanner(null)}
            accessibilityLabel="Fechar notificação"
          >
            ×
          </Text>
        </TouchableOpacity>
      )}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationsContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationsProvider");
  }
  return context;
}

const styles = createThemedStyles({
  banner: {
    position: "absolute",
    left: 12,
    right: 12,
    zIndex: 999,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
    shadowColor: "#000",
    shadowOpacity: 0.18,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 8,
    borderLeftWidth: 4,
    borderLeftColor: "#FF5B8F",
  },
  bannerIcone: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "#FFF0F3",
    alignItems: "center",
    justifyContent: "center",
  },
  bannerIconeTexto: { fontSize: 16 },
  bannerConteudo: { flex: 1 },
  bannerTitulo: { fontSize: 14, fontWeight: "700", color: "#1F1F1F" },
  bannerMensagem: { fontSize: 12, color: "#5A5A5A", marginTop: 2 },
  bannerFechar: { fontSize: 20, color: "#B0B0B0", paddingHorizontal: 4 },
});
