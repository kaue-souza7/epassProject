import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Animated,
  Easing,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  Image,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { LinearGradient } from "expo-linear-gradient";
import { atenaService, streamAtena } from "../../api/atena.service";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");
const LOGO_SIZE = 80;

interface Message {
  id: string;
  role: "user" | "bot";
  text: string;
  /** Inferência em curso: o texto cresce a cada `delta`. */
  streaming?: boolean;
  /** Falhou: o texto é o que deu, não uma resposta completa. */
  erro?: boolean;
}

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

const SUGGESTIONS = [
  "Qual foi a última nota dela?",
  "Ela teve alguma ocorrência?",
  "Tem aviso não lido?",
  "Qual o saldo da carteira?",
];


function TransitionView({ progress }: { progress: Animated.Value }) {
  const bgOpacity = progress.interpolate({
    inputRange: [0, 0.15, 0.5, 1],
    outputRange: [0, 0.6, 0.95, 1],
  });

  const logoScale = progress.interpolate({
    inputRange: [0, 0.15, 0.4, 0.65, 1],
    outputRange: [1, 1.4, 4, 10, 25],
  });

  const logoOpacity = progress.interpolate({
    inputRange: [0, 0.3, 0.55, 0.75],
    outputRange: [1, 1, 0.6, 0],
  });

  const ringScale = progress.interpolate({
    inputRange: [0, 0.3, 0.55, 0.8, 1],
    outputRange: [0.5, 0.8, 2, 8, 20],
  });

  const ringOpacity = progress.interpolate({
    inputRange: [0, 0.3, 0.55, 0.8, 1],
    outputRange: [0, 0.3, 0.5, 0.3, 0],
  });

  const flashOpacity = progress.interpolate({
    inputRange: [0, 0.85, 0.92, 1],
    outputRange: [0, 0, 0.8, 0],
  });

  const particle1 = progress.interpolate({
    inputRange: [0, 0.2, 0.6, 1],
    outputRange: [0, 40, 120, 200],
  });
  const particle2 = progress.interpolate({
    inputRange: [0, 0.25, 0.6, 1],
    outputRange: [0, -50, -140, -220],
  });
  const particle3 = progress.interpolate({
    inputRange: [0, 0.3, 0.6, 1],
    outputRange: [0, 60, 160, 260],
  });
  const particleOpacity = progress.interpolate({
    inputRange: [0, 0.2, 0.5, 0.8, 1],
    outputRange: [0, 0.8, 1, 0.3, 0],
  });

  const glowScale = progress.interpolate({
    inputRange: [0, 0.15, 0.4],
    outputRange: [1, 1.8, 5],
  });
  const glowOpacity = progress.interpolate({
    inputRange: [0, 0.15, 0.4, 0.6],
    outputRange: [0.3, 0.6, 0.4, 0],
  });

  return (
    <View style={styles.transitionContainer}>
      <Animated.View style={[styles.transitionBg, { opacity: bgOpacity }]} />

      <Animated.View
        style={[
          styles.transitionGlow,
          {
            opacity: glowOpacity,
            transform: [{ scale: glowScale }],
          },
        ]}
      >
        <LinearGradient
          colors={["rgba(255,91,143,0.4)", "rgba(255,134,100,0.2)", "transparent"]}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>

      {[-1, 1].map((dirX) =>
        [-1, 1].map((dirY) => {
          const pKey = `p_${dirX}_${dirY}`;
          const pVal = progress.interpolate({
            inputRange: [0, 0.3, 0.7, 1],
            outputRange: [0, dirX * 50 + dirY * 30, dirX * 130 + dirY * 80, dirX * 250 + dirY * 150],
          });
          return (
            <Animated.View
              key={pKey}
              pointerEvents="none"
              style={[
                styles.particle,
                {
                  opacity: particleOpacity,
                  transform: [
                    { translateX: pVal },
                    { translateY: progress.interpolate({
                      inputRange: [0, 0.3, 0.7, 1],
                      outputRange: [0, dirY * 40, dirY * 100, dirY * 180],
                    })},
                  ],
                },
              ]}
            />
          );
        }),
      )}

      <Animated.View
        pointerEvents="none"
        style={[
          styles.portalRing,
          {
            opacity: ringOpacity,
            transform: [{ scale: ringScale }],
          },
        ]}
      >
        <View style={[styles.portalRingInner, { borderColor: "rgba(255,255,255,0.15)" }]} />
      </Animated.View>

      <Animated.Image
        source={require("../../../assets/images/atena/atena-logo.png")}
        style={[
          styles.transitionLogo,
          {
            opacity: logoOpacity,
            transform: [{ scale: logoScale }],
          },
        ]}
      />

      <Animated.View
        pointerEvents="none"
        style={[styles.transitionFlash, { opacity: flashOpacity }]}
      />
    </View>
  );
}

function ChatMessage({ message }: { message: Message }) {
  const isBot = message.role === "bot";

  return (
    <View style={[styles.msgRow, isBot ? styles.msgRowBot : styles.msgRowUser]}>
      {isBot && (
        <View style={styles.msgAvatarSmall}>
          <Image
            source={require("../../../assets/images/atena/atena-logo.png")}
            style={styles.msgAvatarSmallImg}
          />
        </View>
      )}
      <View
        style={[
          styles.msgBubble,
          isBot ? styles.msgBubbleBot : styles.msgBubbleUser,
          // Falha não é resposta da Atena: borda vermelha separa as duas coisas
          // para o responsável não ler um erro como informação do filho.
          message.erro && styles.msgBubbleErro,
        ]}
      >
        <Text style={[styles.msgText, isBot ? styles.msgTextBot : styles.msgTextUser]}>
          {message.text.split(/\*\*(.*?)\*\*/).map((part, i) =>
            i % 2 === 1 ? (
              <Text key={i} style={styles.msgBold}>{part}</Text>
            ) : (
              part
            ),
          )}
        </Text>
      </View>
    </View>
  );
}

function AtenaTypingIndicator() {
  const dots = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const anim = Animated.loop(
      Animated.sequence([
        Animated.timing(dots, { toValue: 1, duration: 600, useNativeDriver: true }),
        Animated.timing(dots, { toValue: 0, duration: 600, useNativeDriver: true }),
      ]),
    );
    anim.start();
    return () => anim.stop();
  }, [dots]);

  return (
    <View style={[styles.msgRow, styles.msgRowBot]}>
      <View style={styles.msgAvatarSmall}>
        <Image
          source={require("../../../assets/images/atena/atena-logo.png")}
          style={styles.msgAvatarSmallImg}
        />
      </View>
      <View style={[styles.msgBubble, styles.msgBubbleBot]}>
        <View style={styles.typingRow}>
          {[0, 1, 2].map((i) => (
            <Animated.View
              key={i}
              style={[
                styles.typingDot,
                {
                  opacity: dots.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.3, 1],
                  }),
                  transform: [
                    {
                      translateY: dots.interpolate({
                        inputRange: [0, 0.5, 1],
                        outputRange: [0, -4, 0],
                      }),
                    },
                  ],
                },
              ]}
            />
          ))}
        </View>
      </View>
    </View>
  );
}

export function AtenaChatScreen() {
  useThemeVersion();

  const navigation = useNavigation();
  const { selectedChild } = useSelectedStudent();
  const [phase, setPhase] = useState<"transition" | "chat">("transition");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sugestoes, setSugestoes] = useState<string[]>(SUGGESTIONS);
  const [esperandoPrimeiroToken, setEsperandoPrimeiroToken] = useState(false);
  // Status do assistente: "desconhecido" ate o primeiro /ai/health responder.
  const [status, setStatus] = useState<string>("desconhecido");
  const flatListRef = useRef<FlatList>(null);
  const progress = useRef(new Animated.Value(0)).current;
  const transitionDone = useRef(false);
  // Conversa atual: mantém o histórico entre as perguntas da mesma sessão. O
  // backend valida o dono — um id de outra pessoa volta 404 e nada é gravado.
  const conversaId = useRef<string | null>(null);
  const cancelarRef = useRef<(() => void) | null>(null);

  const nomeAluno = selectedChild?.aluno_nome.split(" ")[0] ?? "Aluno";

  useEffect(() => {
    Animated.timing(progress, {
      toValue: 1,
      duration: 2000,
      useNativeDriver: true,
      easing: Easing.inOut(Easing.cubic),
    }).start(() => {
      if (!transitionDone.current) {
        transitionDone.current = true;
        setPhase("chat");
        setMessages([{
          id: "welcome",
          role: "bot",
          text: `Olá, ${nomeAluno}! 👋\n\nSou a **Atena**.\n\nPosso responder sobre notas, média, faltas, ocorrências, avisos, Carteira, lanches e documentos dos seus filhos.`,
        }]);
      }
    });
    return () => {
      transitionDone.current = true;
    };
  }, [progress]);

  // Sair da tela cancela a inferência: sem isso, a stream continua no servidor
  // segurando a única vaga de concorrência do Ollama até o timeout.
  useEffect(() => () => cancelarRef.current?.(), []);

  // Status real do assistente.
  //
  // Antes deste efeito, o ponto do cabeçalho era a palavra "Online" fixa. Isso
  // é o pior tipo de mentira em uma tela de status: o usuário acreditava que
  // podia perguntar, e só descobria que não podia quando a pergunta falhava —
  // depois de esperar o carregamento do modelo. O `/ai/health` é autenticado e
  // devolve exatamente o que este perfil pode perguntar, então o mesmo request
  // alimenta o status e as sugestões iniciais.
  useEffect(() => {
    let vivo = true;
    const controller = new AbortController();

    const consultar = async () => {
      try {
        const dados = await atenaService.health(controller.signal);
        if (!vivo) return;
        setStatus(dados.status);
        setSugestoes(dados.sugestoes?.length ? dados.sugestoes : SUGGESTIONS);
      } catch {
        // Falha ao consultar o health NÃO significa que a Atena está fora: pode
        // ser rede. Deixa como "verificando" e tenta de novo no próximo ciclo.
        if (vivo) setStatus("desconhecido");
      }
    };

    void consultar();
    const intervalo = setInterval(consultar, 60_000);
    return () => {
      vivo = false;
      controller.abort();
      clearInterval(intervalo);
    };
  }, []);

  // Traduz o status do backend em cor + rótulo. `desconhecido` é o estado
  // "ainda não sei" — amarelo, nunca verde: verde affirmaria o que não se sabe.
  const saude = useMemo(() => {
    switch (status) {
      case "ok":
        return { rotulo: "Online", cor: "#34D399" };
      case "degraded":
        return { rotulo: "Preparando", cor: "#FBBF24" };
      case "desabilitado":
        return { rotulo: "Desativada", cor: "#9CA3AF" };
      case "unavailable":
        return { rotulo: "Indisponível", cor: "#F87171" };
      default:
        return { rotulo: "Verificando", cor: "#FBBF24" };
    }
  }, [status]);

  const podePerguntar = status !== "unavailable" && status !== "desabilitado";

  const addMessage = useCallback((text: string, role: "user" | "bot") => {
    setMessages((prev) => [...prev, { id: generateId(), role, text }]);
  }, []);

  const handleSend = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isTyping) return;

      cancelarRef.current?.();
      setInputText("");
      setIsTyping(true);
      setEsperandoPrimeiroToken(true);
      setSugestoes([]);

      const idBot = generateId();
      setMessages((prev) => [
        ...prev,
        { id: generateId(), role: "user", text: trimmed },
        { id: idBot, role: "bot", text: "", streaming: true },
      ]);

      const alterarBot = (novo: Partial<Message>) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === idBot ? { ...m, ...novo } : m)),
        );

      const cancelar = streamAtena(
        {
          message: trimmed,
          // O aluno vem do seletor do app; o backend confere se ele é mesmo
          // filho deste usuário (fora do escopo, vira recusa — não resposta).
          aluno_selecionado_id: selectedChild?.aluno_id ?? null,
          conversa_id: conversaId.current,
          salvar: true,
        },
        (frame) => {
          if (frame.tipo === "meta") {
            conversaId.current = frame.conversa_id;
          } else if (frame.tipo === "delta") {
            setEsperandoPrimeiroToken(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === idBot ? { ...m, text: m.text + frame.texto } : m,
              ),
            );
          } else if (frame.tipo === "done") {
            // O `done` é AUTORITATIVO: os deltas são pré-guardrail e podem
            // conter número que o backend cortou.
            alterarBot({ text: frame.resposta.resposta, streaming: false });
            setSugestoes(frame.resposta.sugestoes?.length ? frame.resposta.sugestoes : []);
          } else if (frame.tipo === "erro") {
            alterarBot({
              text: frame.parcial || "Não consegui responder agora.",
              streaming: false,
              erro: true,
            });
          }
        },
        (erro) => {
          alterarBot({ streaming: false });
          setIsTyping(false);
          setEsperandoPrimeiroToken(false);
          cancelarRef.current = null;
          if (erro) {
            alterarBot({ text: erro, streaming: false, erro: true });
          }
        },
      );
      cancelarRef.current = cancelar;
    },
    [isTyping, selectedChild],
  );

  const handleSuggestion = useCallback(
    (text: string) => {
      handleSend(text);
    },
    [handleSend],
  );

  useEffect(() => {
    if (flatListRef.current && messages.length > 0) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages, isTyping]);

  if (phase === "transition") {
    return <TransitionView progress={progress} />;
  }

  return (
    <View style={styles.chatContainer}>
      <LinearGradient
        colors={["#0D0D1A", "#0A0A14"]}
        style={StyleSheet.absoluteFill}
      />

      <SafeAreaView style={styles.chatSafe}>
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.headerBack}
            onPress={() => navigation.goBack()}
            accessibilityLabel="Voltar"
            accessibilityRole="button"
          >
            <ThemedIcon name="chevron-back" size={24} color="rgba(255,255,255,0.7)" />
          </TouchableOpacity>

          <View style={styles.headerCenter}>
            <Image
              source={require("../../../assets/images/atena/atena-logo.png")}
              style={styles.headerLogo}
            />
            <View style={styles.headerInfo}>
              <Text style={styles.headerName}>Atena</Text>
              <View style={styles.headerStatusRow}>
                <View
                  style={[
                    styles.statusDot,
                    { backgroundColor: saude.cor },
                  ]}
                />
                <Text style={styles.headerStatus}>{saude.rotulo}</Text>
              </View>
            </View>
          </View>

          <View style={styles.headerBack} />
        </View>

        <KeyboardAvoidingView
          style={styles.chatBody}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
        >
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => <ChatMessage message={item} />}
            contentContainerStyle={styles.msgList}
            showsVerticalScrollIndicator={false}
            onContentSizeChange={() =>
              flatListRef.current?.scrollToEnd({ animated: true })
            }
          />

          {/* Os "..." só enquanto NENHUM token chegou: depois que a bolha
              começa a crescer, os pontos viram ruído. */}
          {isTyping && esperandoPrimeiroToken && <AtenaTypingIndicator />}

          {!isTyping && sugestoes.length > 0 && (
            <View style={styles.suggestionsContainer}>
              <Text style={styles.suggestionsTitle}>Pergunte para a Atena</Text>
              <View style={styles.suggestionsRow}>
                {sugestoes.map((s) => (
                  <TouchableOpacity
                    key={s}
                    style={styles.suggestionChip}
                    onPress={() => handleSuggestion(s)}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.suggestionChipText}>{s}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          {/* Assistente fora do ar: o histórico continua legível, mas a
              entrada some. Melhor que aceitar a pergunta e desperdiçar uma
              espera de ~30s para descobrir que ela não seria respondida. */}
          {!podePerguntar && (
            <View style={styles.offlineBanner}>
              <Text style={styles.offlineBannerText}>
                {status === "desabilitado"
                  ? "O assistente está desativado no momento."
                  : "A Atena está sem resposta agora. Tente de novo em alguns instantes."}
              </Text>
            </View>
          )}

          {podePerguntar && (
            <View style={styles.inputBar}>
              <TextInput
                style={styles.input}
                placeholder="Digite sua mensagem..."
                placeholderTextColor="rgba(255,255,255,0.3)"
                value={inputText}
                onChangeText={setInputText}
                returnKeyType="send"
                onSubmitEditing={() => handleSend(inputText)}
              />
              <TouchableOpacity
                style={[
                  styles.sendButton,
                  !inputText.trim() && styles.sendButtonDisabled,
                ]}
                onPress={() => handleSend(inputText)}
                disabled={!inputText.trim()}
                accessibilityLabel="Enviar"
                accessibilityRole="button"
              >
                <ThemedIcon name="send" size={18} color="white" />
              </TouchableOpacity>
            </View>
          )}
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = createThemedStyles({
  transitionContainer: {
    flex: 1,
    backgroundColor: "#0A0A14",
    justifyContent: "center",
    alignItems: "center",
  },
  transitionBg: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "#050510",
  },
  transitionGlow: {
    position: "absolute",
    width: 120,
    height: 120,
    borderRadius: 60,
  },
  transitionLogo: {
    width: LOGO_SIZE,
    height: LOGO_SIZE,
    borderRadius: 20,
    position: "absolute",
  },
  portalRing: {
    position: "absolute",
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: "center",
    alignItems: "center",
  },
  portalRingInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
  },
  transitionFlash: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "white",
  },
  particle: {
    position: "absolute",
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "rgba(255,255,255,0.5)",
  },

  chatContainer: {
    flex: 1,
    backgroundColor: "#0D0D1A",
  },
  chatSafe: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.06)",
  },
  headerBack: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  headerCenter: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  headerLogo: {
    width: 32,
    height: 32,
    borderRadius: 8,
  },
  headerInfo: {
    gap: 2,
  },
  headerName: {
    fontSize: 16,
    fontWeight: "700",
    color: "white",
  },
  headerStatusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#34C759",
  },
  headerStatus: {
    fontSize: 11,
    color: "rgba(255,255,255,0.5)",
    fontWeight: "500",
  },

  chatBody: {
    flex: 1,
  },
  msgList: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },

  msgRow: {
    flexDirection: "row",
    marginBottom: 12,
    gap: 8,
  },
  msgRowBot: {
    justifyContent: "flex-start",
  },
  msgRowUser: {
    justifyContent: "flex-end",
  },
  msgAvatarSmall: {
    width: 28,
    height: 28,
    borderRadius: 7,
    alignSelf: "flex-end",
    marginBottom: 2,
  },
  msgAvatarSmallImg: {
    width: 28,
    height: 28,
    borderRadius: 7,
  },
  msgBubble: {
    maxWidth: "78%",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  msgBubbleBot: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    borderBottomLeftRadius: 6,
  },
  msgBubbleUser: {
    backgroundColor: "#FF5B8F",
    borderBottomRightRadius: 6,
  },
  msgBubbleErro: {
    borderColor: "rgba(255,107,107,0.45)",
  },
  msgText: {
    fontSize: 15,
    lineHeight: 22,
  },
  msgTextBot: {
    color: "rgba(255,255,255,0.9)",
  },
  msgTextUser: {
    color: "white",
  },
  msgBold: {
    fontWeight: "700",
    color: "white",
  },

  typingRow: {
    flexDirection: "row",
    gap: 5,
    paddingVertical: 4,
    paddingHorizontal: 4,
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "rgba(255,255,255,0.5)",
  },

  suggestionsContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
    gap: 10,
  },
  suggestionsTitle: {
    fontSize: 12,
    color: "rgba(255,255,255,0.35)",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  suggestionsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  suggestionChip: {
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  suggestionChipText: {
    fontSize: 13,
    color: "rgba(255,255,255,0.7)",
    fontWeight: "600",
  },

  inputBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.06)",
  },
  offlineBanner: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.06)",
    backgroundColor: "rgba(251,191,36,0.08)",
  },
  offlineBannerText: {
    fontSize: 12,
    color: "rgba(255,255,255,0.6)",
    textAlign: "center",
  },
  input: {
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 22,
    paddingHorizontal: 18,
    paddingVertical: 12,
    fontSize: 15,
    color: "white",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#FF5B8F",
    justifyContent: "center",
    alignItems: "center",
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
});
