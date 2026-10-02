import { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Share,
  Alert,
  Platform,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import QRCode from "react-native-qrcode-svg";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import type { AutorizacaoMock, TipoAutorizacao } from "../../types/release";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type Phase = "form" | "active" | "cancelled" | "expired";

function generateId(): string {
  const hex = "0123456789abcdef";
  let id = "";
  for (let i = 0; i < 36; i++) {
    if (i === 8 || i === 13 || i === 18 || i === 23) {
      id += "-";
    } else {
      id += hex[Math.floor(Math.random() * 16)];
    }
  }
  return id;
}

function applyCpfMask(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
  if (digits.length <= 9)
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const day = d.getDate().toString().padStart(2, "0");
  const month = (d.getMonth() + 1).toString().padStart(2, "0");
  const year = d.getFullYear();
  const hours = d.getHours().toString().padStart(2, "0");
  const minutes = d.getMinutes().toString().padStart(2, "0");
  return `${day}/${month}/${year} ${hours}:${minutes}`;
}

const TIPO_OPTIONS: { value: TipoAutorizacao; label: string; desc: string }[] = [
  { value: "temporaria", label: "Temporária", desc: "15 minutos" },
  { value: "diaria", label: "Diária", desc: "24 horas" },
];

export function LiberarAlunoScreen() {
  useThemeVersion();

  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const { selectedChild } = useSelectedStudent();

  const [tipo, setTipo] = useState<TipoAutorizacao>("temporaria");
  const [nomeAutorizado, setNomeAutorizado] = useState("");
  const [cpfRaw, setCpfRaw] = useState("");
  const [phase, setPhase] = useState<Phase>("form");
  const [autorizacao, setAutorizacao] = useState<AutorizacaoMock | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cpfMasked = applyCpfMask(cpfRaw);
  const cpfDigits = cpfRaw.replace(/\D/g, "").slice(0, 11);
  const nomeValido = nomeAutorizado.trim().length > 0;
  const cpfValido = cpfDigits.length === 11;
  const formularioValido = nomeValido && cpfValido;

  const duracaoSegundos = tipo === "temporaria" ? 15 * 60 : 24 * 60 * 60;

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return clearTimer;
  }, [clearTimer]);

  const startTimer = useCallback(
    (expiresAt: string) => {
      clearTimer();
      const tick = () => {
        const now = Date.now();
        const exp = new Date(expiresAt).getTime();
        const diff = Math.max(0, Math.floor((exp - now) / 1000));
        setTimeLeft(diff);
        if (diff <= 0) {
          clearTimer();
          setPhase("expired");
        }
      };
      tick();
      timerRef.current = setInterval(tick, 1000);
    },
    [clearTimer],
  );

  const handleGerarQR = () => {
    if (!formularioValido || !selectedChild) return;

    const now = new Date();
    const durationMs = tipo === "temporaria" ? 15 * 60 * 1000 : 24 * 60 * 60 * 1000;
    const expiresAt = new Date(now.getTime() + durationMs);

    const auth: AutorizacaoMock = {
      id: generateId(),
      aluno_id: selectedChild.aluno_id,
      aluno_nome: selectedChild.aluno_nome,
      turma_codigo: selectedChild.turma_codigo ?? "---",
      nome_autorizado: nomeAutorizado.trim(),
      cpf: cpfMasked,
      tipo,
      created_at: now.toISOString(),
      expires_at: expiresAt.toISOString(),
      status: "ativa",
    };

    setAutorizacao(auth);
    setPhase("active");
    startTimer(auth.expires_at);
  };

  const handleCancel = () => {
    Alert.alert(
      "Cancelar autorização?",
      "O QR Code deixará de ser válido.",
      [
        { text: "Não", style: "cancel" },
        {
          text: "Sim, cancelar",
          style: "destructive",
          onPress: () => {
            clearTimer();
            setPhase("cancelled");
            if (autorizacao) {
              setAutorizacao({ ...autorizacao, status: "cancelada" });
            }
          },
        },
      ],
    );
  };

  const handleShare = async () => {
    if (!autorizacao) return;
    const tipoLabel = autorizacao.tipo === "temporaria" ? "Temporária (15 min)" : "Diária (24h)";
    try {
      await Share.share({
        message:
          `Autorização de retirada de aluno\n\n` +
          `Aluno: ${autorizacao.aluno_nome}\n` +
          `Turma: ${autorizacao.turma_codigo}\n\n` +
          `Pessoa autorizada:\n${autorizacao.nome_autorizado}\n\n` +
          `CPF:\n${autorizacao.cpf}\n\n` +
          `Tipo:\n${tipoLabel}\n\n` +
          `Validade:\n${formatDateTime(autorizacao.expires_at)}`,
        title: "Liberação Digital - ePass",
      });
    } catch {
      // user cancelled share
    }
  };

  const handleVoltar = () => {
    clearTimer();
    navigation.goBack();
  };

  const handleNovoQR = () => {
    clearTimer();
    setTipo("temporaria");
    setNomeAutorizado("");
    setCpfRaw("");
    setAutorizacao(null);
    setPhase("form");
    setTimeLeft(0);
  };

  const progress = autorizacao
    ? Math.max(0, Math.min(1, timeLeft / duracaoSegundos))
    : 0;

  const isExpiredOrCancelled =
    phase === "expired" || phase === "cancelled";

  if (!selectedChild) {
    return (
      <SafeAreaView style={[styles.safe, { backgroundColor: "#F5F5F7" }]}>
        <View style={styles.center}>
          <ThemedIcon name="alert-circle-outline" size={48} color="#FF5B8F" />
          <Text style={styles.centerText}>
            Nenhum aluno selecionado.
          </Text>
          <TouchableOpacity style={styles.voltarBtn} onPress={handleVoltar}>
            <Text style={styles.voltarBtnText}>Voltar</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: "#F5F5F7" }]}>
      <LinearGradient
        colors={["#F84F8D", "#FF8664"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={[styles.header, { paddingTop: insets.top + 8 }]}
      >
        <TouchableOpacity
          style={styles.backButton}
          onPress={handleVoltar}
          accessibilityLabel="Voltar"
          accessibilityRole="button"
        >
          <ThemedIcon name="arrow-back" size={24} color="white" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Liberar Aluno</Text>
        <View style={styles.backButton} />
      </LinearGradient>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {phase === "form" && (
          <View style={styles.formContainer}>
            <View style={styles.studentCard}>
              <View style={styles.studentAvatar}>
                <Text style={styles.studentAvatarText}>
                  {selectedChild.aluno_nome.charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.studentInfo}>
                <Text style={styles.studentName}>{selectedChild.aluno_nome}</Text>
                <Text style={styles.studentClass}>
                  {selectedChild.turma_codigo ?? "Sem turma"}
                </Text>
              </View>
            </View>

            <View>
              <Text style={styles.inputLabel}>Tipo de autorização</Text>
              <View style={styles.tipoRow}>
                {TIPO_OPTIONS.map((opt) => {
                  const selected = tipo === opt.value;
                  return (
                    <TouchableOpacity
                      key={opt.value}
                      style={[
                        styles.tipoOption,
                        selected && styles.tipoOptionSelected,
                      ]}
                      onPress={() => setTipo(opt.value)}
                      accessibilityLabel={opt.label}
                      accessibilityRole="radio"
                      accessibilityState={{ selected }}
                    >
                      <View
                        style={[
                          styles.radio,
                          selected && styles.radioSelected,
                        ]}
                      >
                        {selected && (
                          <View style={styles.radioInner} />
                        )}
                      </View>
                      <View style={styles.tipoTextGroup}>
                        <Text
                          style={[
                            styles.tipoLabel,
                            selected && styles.tipoLabelSelected,
                          ]}
                        >
                          {opt.label}
                        </Text>
                        <Text
                          style={[
                            styles.tipoDesc,
                            selected && styles.tipoDescSelected,
                          ]}
                        >
                          {opt.desc}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            <View>
              <Text style={styles.inputLabel}>Nome completo</Text>
              <TextInput
                style={styles.input}
                placeholder="Nome da pessoa autorizada"
                placeholderTextColor="#C7C7C7"
                value={nomeAutorizado}
                onChangeText={setNomeAutorizado}
                autoCapitalize="words"
                returnKeyType="next"
                accessibilityLabel="Nome completo da pessoa autorizada"
              />
            </View>

            <View>
              <Text style={styles.inputLabel}>CPF</Text>
              <TextInput
                style={styles.input}
                placeholder="000.000.000-00"
                placeholderTextColor="#C7C7C7"
                value={cpfMasked}
                onChangeText={(v) => setCpfRaw(v)}
                keyboardType="number-pad"
                maxLength={14}
                returnKeyType="go"
                onSubmitEditing={handleGerarQR}
                accessibilityLabel="CPF da pessoa autorizada"
              />
            </View>

            <TouchableOpacity
              style={[
                styles.primaryButton,
                !formularioValido && styles.primaryButtonDisabled,
              ]}
              onPress={handleGerarQR}
              disabled={!formularioValido}
              accessibilityLabel="Gerar QR Code"
              accessibilityRole="button"
            >
              <ThemedIcon name="qr-code" size={20} color="white" />
              <Text style={styles.primaryButtonText}>Gerar QR Code</Text>
            </TouchableOpacity>
          </View>
        )}

        {(phase === "active" || phase === "cancelled" || phase === "expired") && autorizacao && (
          <View style={styles.qrContainer}>
            <View style={styles.qrCard}>
              <View style={styles.qrWrapper}>
                {isExpiredOrCancelled && (
                  <View style={styles.qrOverlay}>
                    <View
                      style={[
                        styles.statusBadge,
                        phase === "cancelled"
                          ? styles.badgeCancelled
                          : styles.badgeExpired,
                      ]}
                    >
                      <ThemedIcon
                        name={
                          phase === "cancelled"
                            ? "close-circle"
                            : "time-outline"
                        }
                        size={18}
                        color="white"
                      />
                      <Text style={styles.badgeText}>
                        {phase === "cancelled" ? "CANCELADO" : "EXPIRADO"}
                      </Text>
                    </View>
                  </View>
                )}
                <QRCode
                  value={autorizacao.id}
                  size={200}
                  backgroundColor={isExpiredOrCancelled ? "#E5E5E5" : "white"}
                  color={isExpiredOrCancelled ? "#C7C7C7" : "#1F1F1F"}
                />
              </View>

              <View style={styles.qrInfo}>
                <View style={styles.qrInfoRow}>
                  <ThemedIcon name="person-outline" size={16} color="#7A7A7A" />
                  <Text style={styles.qrInfoLabel}>Aluno:</Text>
                  <Text style={styles.qrInfoValue}>{autorizacao.aluno_nome}</Text>
                </View>
                <View style={styles.qrInfoRow}>
                  <ThemedIcon name="school-outline" size={16} color="#7A7A7A" />
                  <Text style={styles.qrInfoLabel}>Turma:</Text>
                  <Text style={styles.qrInfoValue}>{autorizacao.turma_codigo}</Text>
                </View>
                <View style={styles.qrInfoRow}>
                  <ThemedIcon name="people-outline" size={16} color="#7A7A7A" />
                  <Text style={styles.qrInfoLabel}>Autorizado:</Text>
                  <Text style={styles.qrInfoValue}>{autorizacao.nome_autorizado}</Text>
                </View>
                <View style={styles.qrInfoRow}>
                  <ThemedIcon name="id-card-outline" size={16} color="#7A7A7A" />
                  <Text style={styles.qrInfoLabel}>CPF:</Text>
                  <Text style={styles.qrInfoValue}>{autorizacao.cpf}</Text>
                </View>
                <View style={styles.qrInfoRow}>
                  <ThemedIcon
                    name={autorizacao.tipo === "temporaria" ? "time-outline" : "calendar-outline"}
                    size={16}
                    color="#7A7A7A"
                  />
                  <Text style={styles.qrInfoLabel}>Tipo:</Text>
                  <Text style={styles.qrInfoValue}>
                    {autorizacao.tipo === "temporaria" ? "Temporária (15 min)" : "Diária (24h)"}
                  </Text>
                </View>
              </View>
            </View>

            {!isExpiredOrCancelled && (
              <View style={styles.timerSection}>
                {autorizacao.tipo === "temporaria" ? (
                  <>
                    <View style={styles.timerRing}>
                      <Text
                        style={[
                          styles.timerText,
                          timeLeft < 60 && styles.timerTextUrgent,
                        ]}
                      >
                        {formatTime(timeLeft)}
                      </Text>
                    </View>
                    <View style={styles.progressBar}>
                      <View
                        style={[
                          styles.progressFill,
                          {
                            width: `${progress * 100}%`,
                            backgroundColor:
                              timeLeft < 60 ? "#FF5B8F" : "#34C759",
                          },
                        ]}
                      />
                    </View>
                    <Text style={styles.timerLabel}>Tempo restante</Text>
                  </>
                ) : (
                  <>
                    <View style={styles.validadeCard}>
                      <ThemedIcon name="calendar-outline" size={22} color="#FF5B8F" />
                      <Text style={styles.validadeText}>
                        Válido até {formatDateTime(autorizacao.expires_at)}
                      </Text>
                    </View>
                    <View style={styles.progressBar}>
                      <View
                        style={[
                          styles.progressFill,
                          {
                            width: `${progress * 100}%`,
                            backgroundColor: "#FF5B8F",
                          },
                        ]}
                      />
                    </View>
                    <Text style={styles.timerLabel}>
                      {Math.floor(progress * 100)}% do período
                    </Text>
                  </>
                )}
              </View>
            )}

            {phase === "expired" && (
              <Text style={styles.expiredText}>
                O período para esta liberação expirou.
              </Text>
            )}

            <View style={styles.actions}>
              {phase === "active" && (
                <>
                  <TouchableOpacity
                    style={styles.shareButton}
                    onPress={handleShare}
                    accessibilityLabel="Compartilhar autorização"
                    accessibilityRole="button"
                  >
                    <ThemedIcon name="share-outline" size={20} color="white" />
                    <Text style={styles.shareButtonText}>Compartilhar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.cancelButton}
                    onPress={handleCancel}
                    accessibilityLabel="Cancelar autorização"
                    accessibilityRole="button"
                  >
                    <ThemedIcon name="close-outline" size={20} color="#FF5B8F" />
                    <Text style={styles.cancelButtonText}>Cancelar</Text>
                  </TouchableOpacity>
                </>
              )}
              {(phase === "cancelled" || phase === "expired") && (
                <TouchableOpacity
                  style={styles.primaryButton}
                  onPress={handleNovoQR}
                  accessibilityLabel="Gerar nova autorização"
                  accessibilityRole="button"
                >
                  <ThemedIcon name="refresh-outline" size={20} color="white" />
                  <Text style={styles.primaryButtonText}>
                    {phase === "expired" ? "Gerar Novo QR" : "Nova Autorização"}
                  </Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = createThemedStyles({
  safe: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
    gap: 16,
  },
  centerText: {
    fontSize: 16,
    color: "#7A7A7A",
    textAlign: "center",
    fontWeight: "500",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "white",
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 24,
    paddingBottom: 40,
  },

  formContainer: {
    gap: 24,
  },
  studentCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 36,
    padding: 20,
    gap: 16,
  },
  studentAvatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
  },
  studentAvatarText: {
    fontSize: 26,
    fontWeight: "700",
    color: "#FF5B8F",
  },
  studentInfo: {
    flex: 1,
  },
  studentName: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  studentClass: {
    fontSize: 14,
    color: "#7A7A7A",
    marginTop: 2,
    fontWeight: "500",
  },
  inputLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
    marginBottom: 8,
  },
  input: {
    backgroundColor: "white",
    borderRadius: 28,
    paddingHorizontal: 20,
    paddingVertical: 16,
    fontSize: 16,
    color: "#1F1F1F",
    borderWidth: 1.5,
    borderColor: "#E5E5E5",
  },
  tipoRow: {
    flexDirection: "row",
    gap: 12,
  },
  tipoOption: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 20,
    padding: 16,
    gap: 12,
    borderWidth: 1.5,
    borderColor: "#E5E5E5",
  },
  tipoOptionSelected: {
    borderColor: "#FF5B8F",
    backgroundColor: "#FFF0F3",
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: "#C7C7C7",
    justifyContent: "center",
    alignItems: "center",
  },
  radioSelected: {
    borderColor: "#FF5B8F",
  },
  radioInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: "#FF5B8F",
  },
  tipoTextGroup: {
    flex: 1,
  },
  tipoLabel: {
    fontSize: 15,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  tipoLabelSelected: {
    color: "#FF5B8F",
  },
  tipoDesc: {
    fontSize: 12,
    color: "#7A7A7A",
    marginTop: 1,
    fontWeight: "500",
  },
  tipoDescSelected: {
    color: "#FF5B8F",
  },
  primaryButton: {
    flexDirection: "row",
    backgroundColor: "#FF5B8F",
    borderRadius: 999,
    height: 56,
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  primaryButtonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    color: "white",
    fontSize: 17,
    fontWeight: "700",
  },

  qrContainer: {
    gap: 20,
  },
  qrCard: {
    backgroundColor: "white",
    borderRadius: 36,
    padding: 24,
    alignItems: "center",
    gap: 20,
  },
  qrWrapper: {
    position: "relative",
  },
  qrOverlay: {
    ...StyleSheet.absoluteFill,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 10,
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 999,
  },
  badgeCancelled: {
    backgroundColor: "#FF5B8F",
  },
  badgeExpired: {
    backgroundColor: "#8E8E93",
  },
  badgeText: {
    color: "white",
    fontSize: 16,
    fontWeight: "700",
  },
  qrInfo: {
    width: "100%",
    gap: 12,
  },
  qrInfoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  qrInfoLabel: {
    fontSize: 14,
    color: "#7A7A7A",
    fontWeight: "500",
    width: 80,
  },
  qrInfoValue: {
    fontSize: 14,
    color: "#1F1F1F",
    fontWeight: "600",
    flex: 1,
  },

  timerSection: {
    alignItems: "center",
    gap: 12,
  },
  timerRing: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: "white",
    justifyContent: "center",
    alignItems: "center",
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 12,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  timerText: {
    fontSize: 28,
    fontWeight: "800",
    color: "#1F1F1F",
    fontVariant: ["tabular-nums"],
  },
  timerTextUrgent: {
    color: "#FF5B8F",
  },
  validadeCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 20,
    padding: 18,
    gap: 12,
    alignSelf: "stretch",
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 12,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  validadeText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F1F1F",
    flex: 1,
  },
  progressBar: {
    width: "100%",
    height: 6,
    backgroundColor: "#E5E5E5",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
  },
  timerLabel: {
    fontSize: 13,
    color: "#7A7A7A",
    fontWeight: "500",
  },

  expiredText: {
    textAlign: "center",
    fontSize: 15,
    color: "#8E8E93",
    fontWeight: "500",
  },

  actions: {
    gap: 12,
  },
  shareButton: {
    flexDirection: "row",
    backgroundColor: "#34C759",
    borderRadius: 999,
    height: 52,
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  shareButtonText: {
    color: "white",
    fontSize: 16,
    fontWeight: "700",
  },
  cancelButton: {
    flexDirection: "row",
    backgroundColor: "white",
    borderRadius: 999,
    height: 52,
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    borderWidth: 1.5,
    borderColor: "#FF5B8F",
  },
  cancelButtonText: {
    color: "#FF5B8F",
    fontSize: 16,
    fontWeight: "700",
  },
  voltarBtn: {
    backgroundColor: "#FF5B8F",
    borderRadius: 999,
    paddingHorizontal: 32,
    paddingVertical: 14,
  },
  voltarBtnText: {
    color: "white",
    fontSize: 16,
    fontWeight: "700",
  },
});
