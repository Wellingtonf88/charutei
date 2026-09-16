// Formatação de compartilhamento do perfil (F3). Scores/status/badges/streak agora vêm do
// backend (GET /profile, Fase 3 do upgrade — packages/scoring) — este arquivo só formata texto
// para o Share nativo a partir do que a API já calculou.
import { Profile } from "../api/client";

export function shareSummary(p: Profile): string {
  const flavors = p.top_flavors.slice(0, 3).join(", ") || "—";
  return (
    `🥃 Meu paladar CHARUTEI — status ${p.consumer_status.name}\n` +
    `${p.humidor_size} charutos · ${p.distinct_countries} países · ${p.total_tastings} degustações\n` +
    `Sabores favoritos: ${flavors}`
  );
}
