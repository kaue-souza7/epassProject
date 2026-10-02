import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { createThemedStyles } from "../theme/useThemedStyles";
import { ThemedIcon } from "../theme/ThemedIcon";

const ACTIVE = "#FF5B8F";
const INACTIVE = "#B0B0B0";

export interface AnimatedTab {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  badge?: number;
}

interface AnimatedTabBarProps extends BottomTabBarProps {
  tabs: Record<string, AnimatedTab>;
  header?: ReactNode;
}

export function AnimatedTabBar({
  state,
  navigation,
  tabs,
  header,
}: AnimatedTabBarProps) {
  const insets = useSafeAreaInsets();
  const [barWidth, setBarWidth] = useState(0);
  const progress = useRef(new Animated.Value(state.index)).current;

  const count = state.routes.length;
  const tabWidth = count > 0 ? barWidth / count : 0;

  useEffect(() => {
    Animated.timing(progress, {
      toValue: state.index,
      duration: 320,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [state.index, progress]);

  const translateX = progress.interpolate({
    inputRange: [0, Math.max(1, count - 1)],
    outputRange: [0, tabWidth * (count - 1)],
  });

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom + 8 }]}>
      {header}

      <View
        style={styles.bar}
        onLayout={(e) => setBarWidth(e.nativeEvent.layout.width)}
      >
        {tabWidth > 0 && (
          <Animated.View
            style={[
              styles.indicator,
              {
                width: tabWidth - 8,
                transform: [{ translateX }],
              },
            ]}
          />
        )}

        {state.routes.map((route, index) => {
          const focused = index === state.index;
          const config = tabs[route.name];
          const badge = config?.badge ?? 0;

          const iconScale = progress.interpolate({
            inputRange: [index - 1, index, index + 1],
            outputRange: [1, 1.18, 1],
            extrapolate: "clamp",
          });

          const lift = progress.interpolate({
            inputRange: [index - 1, index, index + 1],
            outputRange: [0, -2, 0],
            extrapolate: "clamp",
          });

          return (
            <Pressable
              key={route.key}
              style={styles.item}
              onPress={() => {
                const event = navigation.emit({
                  type: "tabPress",
                  target: route.key,
                  canPreventDefault: true,
                });
                if (!focused && !event.defaultPrevented) {
                  navigation.navigate(route.name, route.params);
                }
              }}
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={config?.label ?? route.name}
            >
              <Animated.View style={{ transform: [{ scale: iconScale }, { translateY: lift }] }}>
                <ThemedIcon
                  name={config?.icon ?? "ellipse"}
                  size={20}
                  color={focused ? ACTIVE : INACTIVE}
                />
                {badge > 0 && (
                  <Animated.View
                    style={[
                      styles.badge,
                      {
                        transform: [
                          {
                            scale: progress.interpolate({
                              inputRange: [index - 1, index, index + 1],
                              outputRange: [0.8, 1.25, 0.8],
                              extrapolate: "clamp",
                            }),
                          },
                        ],
                      },
                    ]}
                  >
                    <Text style={styles.badgeText}>{badge > 9 ? "9+" : badge}</Text>
                  </Animated.View>
                )}
              </Animated.View>

              <Animated.Text
                style={[
                  styles.label,
                  { color: focused ? ACTIVE : INACTIVE },
                ]}
              >
                {config?.label ?? route.name}
              </Animated.Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 0,
  },
  bar: {
    flexDirection: "row",
    backgroundColor: "white",
    borderRadius: 48,
    paddingVertical: 6,
    paddingHorizontal: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 8,
    ...Platform.select({ web: { overflow: "hidden" as never }, default: {} }),
  },
  indicator: {
    position: "absolute",
    top: 4,
    bottom: 4,
    left: 4,
    borderRadius: 48,
    backgroundColor: "#FFF0F3",
  },
  item: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 6,
    gap: 2,
  },
  label: {
    fontSize: 10,
    fontWeight: "600",
  },
  badge: {
    position: "absolute",
    top: -4,
    right: -8,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: ACTIVE,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 3,
  },
  badgeText: {
    color: "white",
    fontSize: 9,
    fontWeight: "700",
  },
});
