import axios from "axios";
import * as SecureStore from "../services/storage";
import { getApiUrl } from "./config";

const API_URL = getApiUrl();

const ACCESS_TOKEN_KEY = "epass_access_token";
const REFRESH_TOKEN_KEY = "epass_refresh_token";

export async function getStoredAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function setTokens(access: string, refresh: string) {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, access);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

let onForcedLogout: (() => Promise<void>) | null = null;

export function setOnForcedLogout(cb: () => Promise<void>) {
  onForcedLogout = cb;
}

let isRefreshing = false;
let pendingRequests: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function handlePendingRequests(error: unknown, token: string | null = null) {
  pendingRequests.forEach((p) => {
    if (token) {
      p.resolve(token);
    } else {
      p.reject(error);
    }
  });
  pendingRequests = [];
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  const token = await getStoredAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status !== 401 || error.config?._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingRequests.push({ resolve, reject });
      }).then((token) => {
        error.config.headers.Authorization = `Bearer ${token}`;
        return api(error.config);
      });
    }

    error.config._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      if (!refreshToken) {
        throw new Error("No refresh token available");
      }
      const { data } = await axios.post(`${API_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      await setTokens(data.access_token, data.refresh_token);
      handlePendingRequests(null, data.access_token);
      error.config.headers.Authorization = `Bearer ${data.access_token}`;
      return api(error.config);
    } catch (refreshError) {
      handlePendingRequests(refreshError);
      await clearTokens();
      await onForcedLogout?.();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export { api };
