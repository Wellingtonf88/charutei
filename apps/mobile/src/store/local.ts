// Persistência local no device (AsyncStorage) — F2 é local-first; sync no backend é o passo
// seguinte (F2.5, plan-gated por tocar packages/knowledge). Helpers JSON tolerantes a erro.
import AsyncStorage from "@react-native-async-storage/async-storage";

export async function loadJSON<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export async function saveJSON<T>(key: string, value: T): Promise<void> {
  await AsyncStorage.setItem(key, JSON.stringify(value));
}
