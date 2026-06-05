import { Platform } from "react-native";
import * as ExpoSecureStore from "expo-secure-store";

const isWeb = Platform.OS === "web";
const TOKEN_KEYWORDS = ["token", "refresh"];

function isTokenKey(key: string): boolean {
  return TOKEN_KEYWORDS.some((kw) => key.toLowerCase().includes(kw));
}

function warnInsecure(key: string): void {
  if (__DEV__ && isTokenKey(key)) {
    console.warn(
      `[SecureStore] "${key}" armazenado em sessionStorage na Web. ` +
        "Em produção, utilize HTTP-only cookies para segurança dos tokens."
    );
  }
}

export async function getItemAsync(key: string): Promise<string | null> {
  if (isWeb) return sessionStorage.getItem(key);
  return ExpoSecureStore.getItemAsync(key);
}

export async function setItemAsync(key: string, value: string): Promise<void> {
  if (isWeb) {
    warnInsecure(key);
    sessionStorage.setItem(key, value);
    return;
  }
  await ExpoSecureStore.setItemAsync(key, value);
}

export async function deleteItemAsync(key: string): Promise<void> {
  if (isWeb) {
    sessionStorage.removeItem(key);
    return;
  }
  await ExpoSecureStore.deleteItemAsync(key);
}
