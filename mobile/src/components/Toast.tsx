import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { createThemedStyles } from "../theme/useThemedStyles";
import { ThemedIcon } from "../theme/ThemedIcon";

export type ToastTone = "success" | "error" | "info" | "warning";

interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastContextValue {
  show: (tone: ToastTone, message: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DURATION = 3200;
const MAX_VISIBLE = 3;

const TONE: Record<
  ToastTone,
  { bg: string; icon: keyof typeof Ionicons.glyphMap; color: string }
> = {
  success: { bg: "#27AE60", icon: "checkmark-circle", color: "#FFFFFF" },
  error: { bg: "#E74C3C", icon: "alert-circle", color: "#FFFFFF" },
  info: { bg: "#FF5B8F", icon: "information-circle", color: "#FFFFFF" },
  warning: { bg: "#F39C12", icon: "warning", color: "#FFFFFF" },
};

function ToastCard({
  item,
  onDismiss,
  bottomInset,
}: {
  item: ToastItem;
  onDismiss: (id: number) => void;
  bottomInset: number;
}) {
  const anim = useRef(new Animated.Value(0)).current;
  const press = useRef(new Animated.Value(0)).current;
  const height = useRef(new Animated.Value(0)).current;
  const tone = TONE[item.tone];

  useEffect(() => {
    Animated.parallel([
      Animated.timing(anim, {
        toValue: 1,
        duration: 340,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(height, {
        toValue: 1,
        duration: 340,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: false,
      }),
    ]).start();

    const timer = setTimeout(() => dismiss(), DURATION);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function dismiss() {
    Animated.parallel([
      Animated.timing(anim, {
        toValue: 0,
        duration: 220,
        easing: Easing.in(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(height, {
        toValue: 0,
        duration: 220,
        easing: Easing.in(Easing.cubic),
        useNativeDriver: false,
      }),
    ]).start(() => onDismiss(item.id));
  }

  const translateY = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [40, 0],
  });
  const opacity = anim;
  const scale = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.92, 1],
  });
  const maxHeight = height.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 160],
  });

  return (
    <Animated.View
      style={[
        styles.wrapper,
        { bottom: bottomInset, maxHeight, opacity, transform: [{ translateY }, { scale }] },
      ]}
    >
      <Animated.View
        style={[
          styles.card,
          { backgroundColor: tone.bg },
          {
            transform: [
              { scale: press.interpolate({ inputRange: [0, 1], outputRange: [1, 0.97] }) },
            ],
          },
        ]}
      >
        <Pressable
          onPress={dismiss}
          accessibilityRole="button"
          accessibilityLabel={item.message}
          onPressIn={() =>
            Animated.spring(press, {
              toValue: 1,
              useNativeDriver: true,
              speed: 40,
              bounciness: 0,
            }).start()
          }
          onPressOut={() =>
            Animated.spring(press, {
              toValue: 0,
              useNativeDriver: true,
              speed: 40,
              bounciness: 8,
            }).start()
          }
          style={styles.pressable}
        >
          <Animated.View style={styles.iconWrap}>
            <ThemedIcon name={tone.icon} size={20} color={tone.color} />
          </Animated.View>
          <Text style={styles.message} numberOfLines={3}>
            {item.message}
          </Text>
          <ThemedIcon name="close" size={16} color="rgba(255,255,255,0.7)" />
        </Pressable>
      </Animated.View>
    </Animated.View>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const insets = useSafeAreaInsets();
  const nextId = useRef(0);
  const bottomInset = insets.bottom + 96;

  const show = useCallback((tone: ToastTone, message: string) => {
    const id = nextId.current++;
    setItems((prev) => [...prev, { id, tone, message }].slice(-MAX_VISIBLE));
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      show,
      success: (m: string) => show("success", m),
      error: (m: string) => show("error", m),
      info: (m: string) => show("info", m),
      warning: (m: string) => show("warning", m),
    }),
    [show],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {items.map((item, i) => (
        <ToastCard
          key={item.id}
          item={item}
          bottomInset={bottomInset + i * 12}
          onDismiss={(id) => setItems((prev) => prev.filter((t) => t.id !== id))}
        />
      ))}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

const styles = createThemedStyles({
  wrapper: {
    position: "absolute",
    left: 16,
    right: 16,
    zIndex: 999,
    elevation: 12,
  },
  card: {
    borderRadius: 16,
    overflow: "hidden",
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOpacity: 0.22,
        shadowRadius: 14,
        shadowOffset: { width: 0, height: 6 },
      },
      android: { elevation: 10 },
      default: {},
    }),
  },
  pressable: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 14,
    paddingHorizontal: 16,
  },
  iconWrap: {
    width: 22,
    alignItems: "center",
  },
  message: {
    flex: 1,
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    lineHeight: 19,
  },
});
