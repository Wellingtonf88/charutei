// Cliente do BFF do CHARUTEI. O app é apenas um cliente — a inteligência vive no backend.
import Constants from "expo-constants";

const BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ?? "http://localhost:8000";

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

export type CollectionItem = { id: string; collection_id: string; cigar_id: string; quantity: number };
export type Collection = { id: string; user_id: string; name: string; items: CollectionItem[] };

function authHeaders(token: string, extra?: Record<string, string>): Record<string, string> {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(extra ?? {}) };
}

// Reconhece a anilha. No MVP, visual_text/ocr_text alimentam o pipeline determinístico;
// em produção, a imagem é enviada e o embedding vem do Voyage multimodal.
export async function recognizeBand(
  token: string,
  input: { ref: string; visualText?: string; ocrText?: string | null },
): Promise<RecognitionResult> {
  const res = await fetch(`${BASE_URL}/bands/recognize`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ ref: input.ref, visual_text: input.visualText ?? "", ocr_text: input.ocrText ?? null }),
  });
  if (!res.ok) throw new Error(`recognize falhou: ${res.status}`);
  return (await res.json()) as RecognitionResult;
}

export async function addToCollection(
  token: string,
  cigarId: string,
  idempotencyKey: string,
): Promise<Collection> {
  const res = await fetch(`${BASE_URL}/collection/items`, {
    method: "POST",
    headers: authHeaders(token, { "Idempotency-Key": idempotencyKey }),
    body: JSON.stringify({ cigar_id: cigarId, quantity: 1 }),
  });
  if (!res.ok) throw new Error(`adicionar à coleção falhou: ${res.status}`);
  return (await res.json()) as Collection;
}

export async function getCollection(token: string): Promise<Collection> {
  const res = await fetch(`${BASE_URL}/collection`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`coleção falhou: ${res.status}`);
  return (await res.json()) as Collection;
}
