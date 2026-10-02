import AsyncStorage from "@react-native-async-storage/async-storage";
import type { GabaritoData } from "../types/gabarito";

const GABARITO_PREFIX = "@epass_gabarito_";

export async function salvarGabarito(data: GabaritoData): Promise<void> {
  const key = `${GABARITO_PREFIX}${data.avaliacaoId}`;
  await AsyncStorage.setItem(key, JSON.stringify(data));
}

export async function carregarGabarito(
  avaliacaoId: string
): Promise<GabaritoData | null> {
  const key = `${GABARITO_PREFIX}${avaliacaoId}`;
  const raw = await AsyncStorage.getItem(key);
  if (!raw) return null;
  return JSON.parse(raw) as GabaritoData;
}

export async function listarGabaritos(): Promise<GabaritoData[]> {
  const allKeys = await AsyncStorage.getAllKeys();
  const keys = allKeys.filter((k) => k.startsWith(GABARITO_PREFIX));
  if (keys.length === 0) return [];
  const items = await AsyncStorage.multiGet(keys);
  return items
    .map(([, v]) => (v ? (JSON.parse(v) as GabaritoData) : null))
    .filter((d): d is GabaritoData => d !== null);
}
