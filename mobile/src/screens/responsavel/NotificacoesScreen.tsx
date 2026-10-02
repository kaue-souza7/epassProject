import { useCallback, useEffect, useState } from "react";
import {
  ScrollView,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ScreenHeader } from "../../components/ScreenHeader";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { ThemedIcon } from "../../theme/ThemedIcon";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { getApiErrorMessage } from "../../api/errors";
import {
  getPreferenciasNotificacao,
  setPreferenciaNotificacaoEmail,
  TIPOS_COM_EMAIL,
  type TipoNotificacao,
} from "../../api/communication.service";

export function NotificacoesScreen() {
  useThemeVersion();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { user } = useAuth();

  const email = user?.email ?? "";

  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [preferencias, setPreferencias] = useState<Record<string, boolean>>({});
  // Tipo em voo. Também trava os outros switches para não disparar duas
  // requisições concorrentes que voltariam fora de ordem.
  const [salvando, setSalvando] = useState<TipoNotificacao | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setPreferencias(await getPreferenciasNotificacao());
    } catch (err) {
      setErro(
        getApiErrorMessage(err, "Não foi possível carregar suas preferências"),
      );
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const salvar = useCallback(
    async (tipo: TipoNotificacao, valor: boolean) => {
      if (salvando) return;
      setSalvando(tipo);
      // Atualização otimista: o switch responde na hora e a falha reverte.
      setPreferencias((atual) => ({ ...atual, [tipo]: valor }));
      try {
        const salvo = await setPreferenciaNotificacaoEmail(tipo, valor);
        setPreferencias((atual) => ({ ...atual, [tipo]: salvo.email }));
        toast.success(
          salvo.email
            ? "Este tipo agora também chega por e-mail."
            : "E-mail desligado para este tipo.",
        );
      } catch (err) {
        setPreferencias((atual) => ({ ...atual, [tipo]: !valor }));
        toast.error(getApiErrorMessage(err, "Não foi possível salvar"));
      } finally {
        setSalvando(null);
      }
    },
    [salvando, toast],
  );

  const desligarTodos = useCallback(async () => {
    if (salvando) return;
    const ativos = TIPOS_COM_EMAIL.filter((i) => preferencias[i.tipo]);
    if (ativos.length === 0) {
      toast.info("Nenhum e-mail está ativado.");
      return;
    }
    // Todos de uma vez: um switch por vez obrigaria o responsável a repetir a
    // operação para cada tipo.
    for (const item of ativos) {
      await salvar(item.tipo, false);
    }
  }, [preferencias, salvando, salvar, toast]);

  if (carregando) {
    return (
      <View style={styles.container}>
        <ScreenHeader title="Notificações" />
        <LoadingState label="Carregando preferências" />
      </View>
    );
  }

  if (erro) {
    return (
      <View style={styles.container}>
        <ScreenHeader title="Notificações" />
        <ErrorState message={erro} onRetry={() => void carregar()} />
      </View>
    );
  }

  const algumAtivo = TIPOS_COM_EMAIL.some((i) => preferencias[i.tipo]);

  return (
    <View style={styles.container}>
      <ScreenHeader
        title="Notificações"
        subtitle="Escolha o que também chega por e-mail"
      />

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + 32 },
        ]}
      >
        <View style={styles.card}>
          {TIPOS_COM_EMAIL.map((item, indice) => {
            const ativo = preferencias[item.tipo] === true;
            return (
              <View key={item.tipo}>
                {indice > 0 && <View style={styles.divider} />}
                <View style={styles.row}>
                  <View style={styles.rowIcon}>
                    <ThemedIcon
                      name={item.icone as never}
                      size={20}
                      color="#FF5B8F"
                    />
                  </View>
                  <View style={styles.rowInfo}>
                    <Text style={styles.rowTitle}>{item.titulo}</Text>
                    <Text style={styles.rowDescription}>
                      {item.descricao}
                    </Text>
                  </View>
                  <Switch
                    value={ativo}
                    onValueChange={(v) => void salvar(item.tipo, v)}
                    disabled={salvando !== null}
                    trackColor={{ false: "#E5E5E5", true: "#FF5B8F" }}
                    thumbColor="#FFFFFF"
                    ios_backgroundColor="#E5E5E5"
                    accessibilityLabel={`Receber ${item.titulo} por e-mail`}
                    accessibilityRole="switch"
                    accessibilityState={{
                      checked: ativo,
                      busy: salvando === item.tipo,
                      disabled: salvando !== null,
                    }}
                  />
                </View>
              </View>
            );
          })}
        </View>

        <View style={styles.infoBox}>
          <ThemedIcon
            name="information-circle-outline"
            size={18}
            color="#2D7FF9"
          />
          <Text style={styles.infoText}>
            {email
              ? `O aplicativo e o push continuam funcionando normalmente. O e-mail é uma cópia a mais, enviada para ${email}.`
              : "O aplicativo e o push continuam funcionando normalmente. Para receber por e-mail, cadastre um e-mail na sua conta."}
          </Text>
        </View>

        <TouchableOpacity
          style={algumAtivo ? styles.restaurar : [styles.restaurar, styles.desativado]}
          onPress={() => void desligarTodos()}
          disabled={salvando !== null || !algumAtivo}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="Desligar todos os e-mails"
          accessibilityState={{ disabled: salvando !== null || !algumAtivo }}
        >
          <ThemedIcon name="refresh-outline" size={18} color="#FF5B8F" />
          <Text style={styles.restaurarTexto}>Desligar todos os e-mails</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = createThemedStyles({
  container: { flex: 1, backgroundColor: "#F5F5F7" },
  scroll: { flex: 1 },
  content: { paddingHorizontal: 24, paddingTop: 8, gap: 20 },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    paddingHorizontal: 20,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  divider: {
    height: 1,
    backgroundColor: "#F0F0F3",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 18,
  },
  rowIcon: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: "#FFEAF1",
    alignItems: "center",
    justifyContent: "center",
  },
  rowInfo: { flex: 1 },
  rowTitle: { fontSize: 15, fontWeight: "600", color: "#1F1F1F" },
  rowDescription: {
    fontSize: 12,
    color: "#7A7A7A",
    marginTop: 2,
    lineHeight: 16,
  },

  infoBox: {
    flexDirection: "row",
    gap: 8,
    backgroundColor: "#F0F6FF",
    borderRadius: 12,
    padding: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: "#2D7FF9",
    lineHeight: 17,
  },

  restaurar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 14,
  },
  desativado: { opacity: 0.4 },
  restaurarTexto: {
    fontSize: 14,
    fontWeight: "600",
    color: "#FF5B8F",
  },
});
