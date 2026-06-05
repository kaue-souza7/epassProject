import Constants from "expo-constants";
import { Platform } from "react-native";

const BACKEND_PORT = 8000;
const API_PREFIX = "/api/v1";

const log = __DEV__ ? console.log : () => {};

export function getApiUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  if (envUrl) {
    log("API URL (env):", envUrl);
    return envUrl;
  }

  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) {
    const host = hostUri.split(":")[0];
    const url = `http://${host}:${BACKEND_PORT}${API_PREFIX}`;
    log("API URL (hostUri):", url);
    return url;
  }

  if (Platform.OS === "android") {
    const url = `http://10.0.2.2:${BACKEND_PORT}${API_PREFIX}`;
    log("API URL (android):", url);
    return url;
  }

  if (Platform.OS === "web" && typeof window !== "undefined") {
    const host = window.location.hostname;
    const url = `http://${host}:${BACKEND_PORT}${API_PREFIX}`;
    log("API URL (web):", url);
    return url;
  }

  const url = `http://localhost:${BACKEND_PORT}${API_PREFIX}`;
  log("API URL (fallback):", url);
  return url;
}
