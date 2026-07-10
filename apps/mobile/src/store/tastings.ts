// Tasting notes (degustações) — local no device. Alimenta o perfil de paladar (F3) e dá ao
// usuário um motivo recorrente para voltar (registrar o que fumou).
import { loadJSON, saveJSON } from "./local";

const KEY = "charutei.tastings";

export type Tasting = {
  id: string;
  cigarId: string;
  rating: number; // 1..5
  flavors: string[];
  occasion: string;
  note: string;
  date: string; // ISO
};

export const FLAVORS = [
  "Amadeirado",
  "Terroso",
  "Cremoso",
  "Café",
  "Cacau",
  "Couro",
  "Pimenta",
  "Doce",
  "Cedro",
  "Frutado",
];

export async function getTastings(): Promise<Tasting[]> {
  return loadJSON<Tasting[]>(KEY, []);
}

export async function getTastingsFor(cigarId: string): Promise<Tasting[]> {
  return (await getTastings()).filter((t) => t.cigarId === cigarId);
}

export async function addTasting(input: Omit<Tasting, "id" | "date">): Promise<Tasting> {
  const all = await getTastings();
  const entry: Tasting = { ...input, id: `${Date.now()}`, date: new Date().toISOString() };
  await saveJSON(KEY, [entry, ...all]);
  return entry;
}
