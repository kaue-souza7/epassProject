import type { NativeStackNavigationOptions } from "@react-navigation/native-stack";

const base = {
  headerShown: false,
  gestureEnabled: true,
  fullScreenGestureEnabled: true,
} satisfies NativeStackNavigationOptions;

export const push = {
  ...base,
  animation: "slide_from_right",
  animationDuration: 300,
} satisfies NativeStackNavigationOptions;

export const pushBack = {
  ...base,
  animation: "slide_from_left",
  animationDuration: 260,
} satisfies NativeStackNavigationOptions;

export const fade = {
  ...base,
  animation: "fade",
  animationDuration: 280,
} satisfies NativeStackNavigationOptions;

export const modal = {
  ...base,
  animation: "slide_from_bottom",
  animationDuration: 380,
  gestureDirection: "vertical",
  gestureEnabled: true,
} satisfies NativeStackNavigationOptions;

export const wizard = {
  ...base,
  animation: "simple_push",
  animationDuration: 320,
} satisfies NativeStackNavigationOptions;
