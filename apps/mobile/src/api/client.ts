// Cliente do BFF do CHARUTEI. O app é só cliente — a inteligência vive no backend (cascata
// cost-aware). Funções puras (token injetado); os hooks React Query em ./hooks os consomem.
//
// URL por ambiente via `EXPO_PUBLIC_API_BASE_URL` (inlined no bundle pelo Expo, ver .env.example)
// — nunca hardcoded no código-fonte (era um IP de LAN fixo em app.json, débito da Fase 1).
const BASE_URL: string = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type BandCandidate = { cigar_id: string; label: string | null; score: number };

export type RecognitionResult = {
  cigar_id: string | null;
  confidence: number;
  candidates: BandCandidate[];
  needs_human: boolean;
  used_vision_llm: boolean;
  tier_resolved: number;
  cost_usd: number;
};

export type CollectionItem = {
  id: string;
  collection_id: string;
  cigar_id: string;
  quantity: number;
  created_at: string | null; // entrada no humidor (aging, F2.5)
};

export type TastingNote = {
  id: string;
  user_id: string;
  cigar_id: string;
  rating: number;
  flavors: string[];
  occasion: string;
  note: string;
  created_at: string | null;
};
export type TastingInput = {
  cigarId: string;
  rating: number;
  flavors: string[];
  occasion: string;
  note: string;
};
export type Collection = { id: string; user_id: string; name: string; items: CollectionItem[] };

export type CatalogEntry = {
  id: string;
  label: string;
  strength: string | null;
  brand: string | null;
  country: string | null;
  pairings: string[];
};

export type Citation = { source_id: string; title: string | null; snippet: string | null };
export type AskResult = {
  answer: string | null;
  tier_resolved: number;
  cost_usd: number;
  citations: Citation[];
  needs_human: boolean;
};

function headers(token: string, extra?: Record<string, string>): Record<string, string> {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(extra ?? {}) };
}

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw new Error(`${what} falhou (${res.status})`);
  return (await res.json()) as T;
}

export async function recognizeBand(
  token: string,
  input: { ref: string; visualText?: string; ocrText?: string | null; dataB64?: string },
): Promise<RecognitionResult> {
  const res = await fetch(`${BASE_URL}/bands/recognize`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({
      ref: input.ref,
      visual_text: input.visualText ?? "",
      ocr_text: input.ocrText ?? null,
      ...(input.dataB64 ? { data_b64: input.dataB64 } : {}),
    }),
  });
  return json<RecognitionResult>(res, "reconhecimento");
}

export async function addToCollection(
  token: string,
  cigarId: string,
  idempotencyKey: string,
): Promise<Collection> {
  const res = await fetch(`${BASE_URL}/collection/items`, {
    method: "POST",
    headers: headers(token, { "Idempotency-Key": idempotencyKey }),
    body: JSON.stringify({ cigar_id: cigarId, quantity: 1 }),
  });
  return json<Collection>(res, "adicionar ao humidor");
}

export async function getCollection(token: string): Promise<Collection> {
  return json<Collection>(await fetch(`${BASE_URL}/collection`, { headers: headers(token) }), "humidor");
}

export async function getCatalog(token: string): Promise<CatalogEntry[]> {
  return json<CatalogEntry[]>(
    await fetch(`${BASE_URL}/catalog`, { headers: headers(token) }),
    "catálogo",
  );
}

export async function ask(token: string, q: string): Promise<AskResult> {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({ q }),
  });
  return json<AskResult>(res, "assistente");
}

export async function getTastings(token: string, cigarId?: string): Promise<TastingNote[]> {
  const qs = cigarId ? `?cigar_id=${encodeURIComponent(cigarId)}` : "";
  return json<TastingNote[]>(
    await fetch(`${BASE_URL}/tasting${qs}`, { headers: headers(token) }),
    "degustações",
  );
}

export async function addTasting(token: string, input: TastingInput): Promise<TastingNote> {
  const res = await fetch(`${BASE_URL}/tasting`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({
      cigar_id: input.cigarId,
      rating: input.rating,
      flavors: input.flavors,
      occasion: input.occasion,
      note: input.note,
    }),
  });
  return json<TastingNote>(res, "salvar degustação");
}

// Slug → rótulo amigável ("cigar:cohiba-siglo-vi" → "Cohiba Siglo Vi").
export function cigarLabel(id: string): string {
  return id
    .replace(/^cigar:/, "")
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export const TIER_NAMES: Record<number, string> = {
  1: "Cache",
  2: "KG",
  3: "Haiku",
  4: "RAG",
  5: "Opus",
};

export const STRENGTH_PT: Record<string, string> = {
  mild: "Suave",
  medium: "Médio",
  "medium-full": "Médio-Forte",
  full: "Forte",
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
