// Cliente do BFF CHARUTEI. Todas as chamadas passam pelo proxy /api do Next.js.
// Em demo mode, usa o token "demo" — FakeAuthProvider aceita qualquer bearer.

const BASE = "/api";
const DEMO_TOKEN = "demo";

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
};
export type Collection = {
  id: string;
  user_id: string;
  name: string;
  items: CollectionItem[];
};

export type CatalogEntry = {
  id: string;
  label: string;
  strength: string | null;
  brand: string | null;
  country: string | null;
  pairings: string[];
};

function headers(extra?: Record<string, string>): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${DEMO_TOKEN}`,
    ...extra,
  };
}

export async function recognizeBand(
  visualText: string,
  dataB64?: string,
): Promise<RecognitionResult> {
  const res = await fetch(`${BASE}/bands/recognize`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      ref: `web-${Date.now()}`,
      visual_text: visualText,
      ...(dataB64 ? { data_b64: dataB64 } : {}),
    }),
  });
  if (!res.ok) throw new Error(`recognize: ${res.status}`);
  return res.json() as Promise<RecognitionResult>;
}

export async function addToCollection(
  cigarId: string,
  idempotencyKey: string,
): Promise<Collection> {
  const res = await fetch(`${BASE}/collection/items`, {
    method: "POST",
    headers: headers({ "Idempotency-Key": idempotencyKey }),
    body: JSON.stringify({ cigar_id: cigarId, quantity: 1 }),
  });
  if (!res.ok) throw new Error(`add item: ${res.status}`);
  return res.json() as Promise<Collection>;
}

export async function getCollection(): Promise<Collection> {
  const res = await fetch(`${BASE}/collection`, { headers: headers() });
  if (!res.ok) throw new Error(`collection: ${res.status}`);
  return res.json() as Promise<Collection>;
}

export async function getCatalog(): Promise<CatalogEntry[]> {
  const res = await fetch(`${BASE}/catalog`, { headers: headers() });
  if (!res.ok) throw new Error(`catalog: ${res.status}`);
  return res.json() as Promise<CatalogEntry[]>;
}

export type Citation = { source_id: string; title: string | null; snippet: string | null };
export type AskResult = {
  answer: string | null;
  tier_resolved: number;
  cost_usd: number;
  citations: Citation[];
  needs_human: boolean;
};

export async function ask(q: string): Promise<AskResult> {
  const res = await fetch(`${BASE}/ask`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ q }),
  });
  if (!res.ok) throw new Error(`ask: ${res.status}`);
  return res.json() as Promise<AskResult>;
}

// Slug → label amigável ("cigar:cohiba-siglo-vi" → "Cohiba Siglo Vi")
export function cigarLabel(id: string): string {
  return id
    .replace(/^cigar:/, "")
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// Tier.SMALL=3, Tier.MEDIUM=4, Tier.LARGE=5 (IntEnum em charutei_contracts)
export const TIER_NAMES: Record<number, string> = { 3: "SMALL", 4: "MEDIUM", 5: "LARGE" };

export const STRENGTH_PT: Record<string, string> = {
  mild: "Suave",
  medium: "Médio",
  "medium-full": "Médio-Forte",
  full: "Forte",
};
