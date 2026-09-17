// Aging (F2.5b) — a *data* de entrada no humidor vem do servidor (`collection_item.created_at`);
// aqui só agendamos o lembrete LOCAL de descanso (retenção). Push remoto = dev build (fora do MVP).
import * as Notifications from "expo-notifications";

import { cigarLabel } from "../api/client";

export const REST_DAYS = 30;

export function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000));
}

// Agenda "seu charuto descansou" para REST_DAYS após a entrada no humidor.
export async function scheduleRestReminder(cigarId: string): Promise<void> {
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
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
        seconds: REST_DAYS * 86_400,
      },
    });
  } catch {
    // notificações indisponíveis — aging segue exibido a partir do servidor.
  }
}
