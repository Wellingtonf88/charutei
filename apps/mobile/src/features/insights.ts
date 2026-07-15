// Insights derivados (F3) — perfil de paladar, nível e gamificação. Puros (sem I/O): recebem
// os dados já buscados (degustações + coleção + catálogo) e calculam no cliente.
import { CatalogEntry, CollectionItem, TastingNote } from "../api/client";

export type Count = { key: string; count: number };

export type Palate = {
  totalTastings: number;
  humidorSize: number;
  avgRating: number; // 0 se sem degustações
  topFlavors: Count[]; // sabores mais registrados (desc)
  countries: Count[]; // países no humidor (desc)
  distinctFlavors: number;
  distinctCountries: number;
};

export type Level = { name: string; index: number; next: number | null; score: number };

export type Badge = {
  id: string;
  label: string;
  icon: string; // Ionicons name
  earned: boolean;
  hint: string;
};

function tally(values: string[]): Count[] {
  const map = new Map<string, number>();
  for (const v of values) map.set(v, (map.get(v) ?? 0) + 1);
  return [...map.entries()]
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count);
}

export function computePalate(
  tastings: TastingNote[],
  items: CollectionItem[],
  catalog: CatalogEntry[],
): Palate {
  const byId = new Map(catalog.map((c) => [c.id, c]));
  const countries = tally(
    items.map((i) => byId.get(i.cigar_id)?.country).filter((x): x is string => !!x),
  );
  const flavors = tally(tastings.flatMap((t) => t.flavors));
  const avg = tastings.length
    ? tastings.reduce((s, t) => s + t.rating, 0) / tastings.length
    : 0;
  return {
    totalTastings: tastings.length,
    humidorSize: items.length,
    avgRating: avg,
    topFlavors: flavors.slice(0, 6),
    countries,
    distinctFlavors: flavors.length,
    distinctCountries: countries.length,
  };
}

const LEVELS = ["Novato", "Aficionado", "Conhecedor", "Mestre Charuteiro"];
const THRESHOLDS = [0, 5, 15, 30];

// Pontuação simples: cada charuto vale 1, cada degustação vale 2.
export function computeLevel(p: Palate): Level {
  const score = p.humidorSize + p.totalTastings * 2;
  let index = 0;
  for (let i = THRESHOLDS.length - 1; i >= 0; i--) {
    if (score >= THRESHOLDS[i]) {
      index = i;
      break;
    }
  }
  const next = index < THRESHOLDS.length - 1 ? THRESHOLDS[index + 1] : null;
  return { name: LEVELS[index], index, next, score };
}

// Streak = dias consecutivos (até hoje/ontem) com ao menos uma degustação registrada.
export function computeStreak(tastings: TastingNote[]): number {
  const days = new Set(
    tastings
      .map((t) => t.created_at)
      .filter((x): x is string => !!x)
      .map((iso) => new Date(iso).toISOString().slice(0, 10)),
  );
  if (days.size === 0) return 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  // se não houve degustação hoje nem ontem, streak = 0
  const key = (d: Date) => d.toISOString().slice(0, 10);
  const yesterday = new Date(today.getTime() - 86_400_000);
  let cursor = days.has(key(today)) ? today : days.has(key(yesterday)) ? yesterday : null;
  if (!cursor) return 0;
  let streak = 0;
  while (days.has(key(cursor))) {
    streak++;
    cursor = new Date(cursor.getTime() - 86_400_000);
  }
  return streak;
}

export function computeBadges(p: Palate, streak: number): Badge[] {
  return [
    {
      id: "first",
      label: "Primeira tragada",
      icon: "flame",
      earned: p.totalTastings >= 1,
      hint: "Registre sua 1ª degustação",
    },
    {
      id: "collector",
      label: "Colecionador",
      icon: "albums",
      earned: p.humidorSize >= 10,
      hint: "10 charutos no humidor",
    },
    {
      id: "traveler",
      label: "Viajante",
      icon: "earth",
      earned: p.distinctCountries >= 3,
      hint: "Charutos de 3 países",
    },
    {
      id: "critic",
      label: "Crítico",
      icon: "star",
      earned: p.totalTastings >= 5,
      hint: "5 degustações registradas",
    },
    {
      id: "palate",
      label: "Paladar amplo",
      icon: "color-palette",
      earned: p.distinctFlavors >= 5,
      hint: "5 sabores diferentes",
    },
    {
      id: "streak",
      label: "Ritual",
      icon: "calendar",
      earned: streak >= 3,
      hint: "3 dias seguidos degustando",
    },
  ];
}

export function shareSummary(p: Palate, level: Level): string {
  const flavors = p.topFlavors.slice(0, 3).map((f) => f.key).join(", ") || "—";
  return (
    `🥃 Meu paladar CHARUTEI — nível ${level.name}\n` +
    `${p.humidorSize} charutos · ${p.distinctCountries} países · ${p.totalTastings} degustações\n` +
    `Sabores favoritos: ${flavors}`
  );
}
