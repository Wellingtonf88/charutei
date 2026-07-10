// Aging tracker — registra localmente quando cada charuto entrou no humidor e agenda um
// lembrete de "descanso" (retenção): "seu charuto está pronto". Notificação LOCAL agendada
// (funciona no Expo Go); push remoto exige dev build (fora do MVP).
import * as Notifications from "expo-notifications";

import { cigarLabel } from "../api/client";
import { loadJSON, saveJSON } from "./local";

const KEY = "charutei.aging"; // { [cigarId]: ISO da 1ª entrada no humidor }
export const REST_DAYS = 30;

export type AddedMap = Record<string, string>;

export async function getAddedMap(): Promise<AddedMap> {
  return loadJSON<AddedMap>(KEY, {});
}

export function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000));
}

// Registra a entrada (mantém a 1ª data) e agenda o lembrete de descanso.
export async function recordAdded(cigarId: string): Promise<void> {
  const map = await getAddedMap();
  if (map[cigarId]) return;
  map[cigarId] = new Date().toISOString();
  await saveJSON(KEY, map);
  await scheduleRestReminder(cigarId);
}

async function scheduleRestReminder(cigarId: string): Promise<void> {
  try {
    const perm = await Notifications.getPermissionsAsync();
    if (!perm.granted) {
      const req = await Notifications.requestPermissionsAsync();
      if (!req.granted) return;
    }
    await Notifications.scheduleNotificationAsync({
      content: {
        title: "Seu charuto descansou 🥃",
        body: `${cigarLabel(cigarId)} completou ${REST_DAYS} dias de descanso — pronto para apreciar.`,
      },
      trigger: { seconds: REST_DAYS * 86_400 },
    });
  } catch {
    // notificações indisponíveis (ex.: permissão negada) — aging segue funcionando sem lembrete.
  }
}
