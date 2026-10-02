import { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
  Platform,
  SafeAreaView,
  StatusBar,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import QRCode from "react-native-qrcode-svg";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const CARD_WIDTH = SCREEN_WIDTH - 48;
const CARD_HEIGHT = CARD_WIDTH * 1.58;

function generateId(): string {
  const y = new Date().getFullYear();
  const r = Math.floor(100000 + Math.random() * 900000);
  return `EP-${y}-${r}`;
}

function generateQrData(nome: string, turma: string): string {
  return JSON.stringify({ aluno: nome, turma, status: "ativo" });
}

export function CarteirinhaDigitalScreen() {
  useThemeVersion();

  const navigation = useNavigation();
  const { selectedChild } = useSelectedStudent();
  const [isFlipped, setIsFlipped] = useState(false);
  const [matriculaId] = useState(generateId);

  const flipAnim = useRef(new Animated.Value(0)).current;
  const mountAnim = useRef(new Animated.Value(0)).current;
  const shineAnim = useRef(new Animated.Value(-1)).current;

  useEffect(() => {
    Animated.timing(mountAnim, {
      toValue: 1,
      duration: 600,
      useNativeDriver: true,
    }).start();
  }, [mountAnim]);

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shineAnim, {
          toValue: 2,
          duration: 4000,
          useNativeDriver: true,
        }),
        Animated.timing(shineAnim, {
          toValue: -1,
          duration: 0,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [shineAnim]);

  const handleFlip = () => {
    Animated.timing(flipAnim, {
      toValue: isFlipped ? 0 : 180,
      duration: 500,
      useNativeDriver: true,
    }).start();
    setIsFlipped(!isFlipped);
  };

  const frontOpacity = flipAnim.interpolate({
    inputRange: [0, 90, 180],
    outputRange: [1, 0, 0],
  });
  const backOpacity = flipAnim.interpolate({
    inputRange: [0, 90, 180],
    outputRange: [0, 0, 1],
  });
  const frontRotation = flipAnim.interpolate({
    inputRange: [0, 180],
    outputRange: ["0deg", "180deg"],
  });
  const backRotation = flipAnim.interpolate({
    inputRange: [0, 180],
    outputRange: ["180deg", "360deg"],
  });

  const mountScale = mountAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.92, 1],
  });
  const mountOpacity = mountAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0.6, 1],
  });

  const shineX = shineAnim.interpolate({
    inputRange: [-1, 2],
    outputRange: [-CARD_WIDTH, CARD_WIDTH * 2],
  });

  const nome = selectedChild?.aluno_nome ?? "Aluno";
  const turma = selectedChild?.turma_codigo ?? "---";
  const inicial = nome.charAt(0).toUpperCase();

  const qrData = generateQrData(nome, turma);

  const series = turma.split(" ")[0] ?? turma;

  const cardContent = (
    <LinearGradient
      colors={["#1a1a3e", "#2d1b69", "#1a1a3e"]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.cardGradient}
    >
      <View style={styles.shineContainer}>
        <Animated.View
          style={[
            styles.shineBar,
            { transform: [{ translateX: shineX }] },
          ]}
        />
      </View>

      <View style={styles.cardHeader}>
        <View style={styles.cardLogoRow}>
          <Text style={styles.cardLogo}>ePass</Text>
          <View style={styles.badgeAtivo}>
            <View style={styles.badgeDot} />
            <Text style={styles.badgeText}>ATIVO</Text>
          </View>
        </View>
      </View>

      <View style={styles.cardAvatarRow}>
        <View style={styles.cardAvatar}>
          <Text style={styles.cardAvatarText}>{inicial}</Text>
        </View>
      </View>

      <Text style={styles.cardName} numberOfLines={1}>
        {nome}
      </Text>
      <Text style={styles.cardClass}>{turma}</Text>

      <View style={styles.cardFooter}>
        <View style={styles.cardIdRow}>
          <ThemedIcon name="barcode-outline" size={14} color="rgba(255,255,255,0.4)" />
          <Text style={styles.cardId}>{matriculaId}</Text>
        </View>
      </View>
    </LinearGradient>
  );

  const backContent = (
    <LinearGradient
      colors={["#1a1a3e", "#2d1b69", "#1a1a3e"]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.cardGradient}
    >
      <View style={styles.backContent}>
        <Text style={styles.backTitle}>Identificação</Text>

        <View style={styles.backRow}>
          <Text style={styles.backLabel}>Nome</Text>
          <Text style={styles.backValue}>{nome}</Text>
        </View>
        <View style={styles.backDivider} />
        <View style={styles.backRow}>
          <Text style={styles.backLabel}>Turma</Text>
          <Text style={styles.backValue}>{turma}</Text>
        </View>
        <View style={styles.backDivider} />
        <View style={styles.backRow}>
          <Text style={styles.backLabel}>Série</Text>
          <Text style={styles.backValue}>{series}</Text>
        </View>
        <View style={styles.backDivider} />
        <View style={styles.backRow}>
          <Text style={styles.backLabel}>Ano</Text>
          <Text style={styles.backValue}>{new Date().getFullYear()}</Text>
        </View>
        <View style={styles.backDivider} />
        <View style={styles.backRow}>
          <Text style={styles.backLabel}>Matrícula</Text>
          <Text style={styles.backValue}>{matriculaId}</Text>
        </View>

        <View style={styles.backQrWrapper}>
          <QRCode
            value={qrData}
            size={80}
            backgroundColor="transparent"
            color="rgba(255,255,255,0.9)"
          />
        </View>
      </View>
    </LinearGradient>
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      <LinearGradient
        colors={["#0F0F23", "#1a1a3e", "#0D0D1A"]}
        style={StyleSheet.absoluteFill}
      />

      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.headerBack}
            onPress={() => navigation.goBack()}
            accessibilityLabel="Voltar"
            accessibilityRole="button"
          >
            <ThemedIcon name="chevron-back" size={24} color="rgba(255,255,255,0.7)" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Carteirinha Digital</Text>
          <View style={styles.headerBack} />
        </View>

        <View style={styles.cardContainer}>
          <Animated.View
            style={[
              styles.cardOuter,
              {
                opacity: mountOpacity,
                transform: [{ scale: mountScale }],
              },
            ]}
          >
            <TouchableOpacity
              activeOpacity={1}
              onPress={handleFlip}
              accessibilityLabel={
                isFlipped
                  ? "Virar para frente da carteirinha"
                  : "Virar para verso da carteirinha"
              }
              accessibilityRole="button"
            >
              <View style={styles.cardStack}>
                <Animated.View
                  style={[
                    styles.cardFace,
                    {
                      opacity: frontOpacity,
                      transform: [
                        { perspective: 1000 },
                        { rotateY: frontRotation },
                      ],
                    },
                  ]}
                >
                  {cardContent}
                </Animated.View>

                <Animated.View
                  style={[
                    styles.cardFace,
                    styles.cardBackFace,
                    {
                      opacity: backOpacity,
                      transform: [
                        { perspective: 1000 },
                        { rotateY: backRotation },
                      ],
                    },
                  ]}
                >
                  {backContent}
                </Animated.View>
              </View>
            </TouchableOpacity>
          </Animated.View>
        </View>

        <Text style={styles.tapHint}>
          <ThemedIcon name="hand-left-outline" size={14} color="rgba(255,255,255,0.3)" />{" "}
          Toque no cartão para virar
        </Text>
      </SafeAreaView>
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#0F0F23",
  },
  safe: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  headerBack: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: "white",
  },
  cardContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingBottom: 20,
  },
  cardOuter: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
  },
  cardStack: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    position: "relative",
  },
  cardFace: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    borderRadius: 24,
    backfaceVisibility: "hidden",
    ...Platform.select({
      ios: {
        shadowColor: "#2d1b69",
        shadowOffset: { width: 0, height: 12 },
        shadowOpacity: 0.5,
        shadowRadius: 30,
      },
      android: {
        elevation: 20,
      },
    }),
  },
  cardBackFace: {
    position: "absolute",
    top: 0,
    left: 0,
  },
  cardGradient: {
    flex: 1,
    borderRadius: 24,
    padding: 24,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  shineContainer: {
    ...StyleSheet.absoluteFill,
    borderRadius: 24,
    overflow: "hidden",
  },
  shineBar: {
    width: 80,
    height: "200%",
    backgroundColor: "rgba(255,255,255,0.06)",
    transform: [{ rotate: "25deg" }],
    position: "absolute",
    top: "-50%",
  },
  cardHeader: {
    marginBottom: 16,
  },
  cardLogoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  cardLogo: {
    fontSize: 20,
    fontWeight: "900",
    color: "rgba(255,255,255,0.9)",
    letterSpacing: 1,
  },
  badgeAtivo: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(52,199,89,0.15)",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    gap: 5,
    borderWidth: 1,
    borderColor: "rgba(52,199,89,0.3)",
  },
  badgeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#34C759",
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#34C759",
    letterSpacing: 0.5,
  },
  cardAvatarRow: {
    alignItems: "center",
    marginBottom: 12,
  },
  cardAvatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "rgba(255,255,255,0.12)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.2)",
  },
  cardAvatarText: {
    fontSize: 28,
    fontWeight: "700",
    color: "white",
  },
  cardName: {
    fontSize: 22,
    fontWeight: "800",
    color: "white",
    textAlign: "center",
  },
  cardClass: {
    fontSize: 14,
    color: "rgba(255,255,255,0.6)",
    textAlign: "center",
    marginTop: 4,
    fontWeight: "500",
  },
  cardFooter: {
    marginTop: "auto",
    alignItems: "center",
  },
  cardIdRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  cardId: {
    fontSize: 12,
    color: "rgba(255,255,255,0.4)",
    fontWeight: "600",
    letterSpacing: 1,
    fontVariant: ["tabular-nums"],
  },

  backContent: {
    flex: 1,
    gap: 0,
  },
  backTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "rgba(255,255,255,0.8)",
    marginBottom: 16,
  },
  backRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
  },
  backLabel: {
    fontSize: 13,
    color: "rgba(255,255,255,0.4)",
    fontWeight: "500",
  },
  backValue: {
    fontSize: 13,
    color: "rgba(255,255,255,0.85)",
    fontWeight: "700",
  },
  backDivider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  backQrWrapper: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 8,
  },

  tapHint: {
    textAlign: "center",
    fontSize: 13,
    color: "rgba(255,255,255,0.25)",
    paddingBottom: 24,
    fontWeight: "500",
  },
});
