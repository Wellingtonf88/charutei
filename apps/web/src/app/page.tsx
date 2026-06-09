"use client";

import { useEffect, useRef, useState } from "react";
import {
  addToCollection,
  cigarLabel,
  getCatalog,
  recognizeBand,
  STRENGTH_PT,
  TIER_NAMES,
  type CatalogEntry,
  type RecognitionResult,
} from "@/lib/api";

const DEMO_FIXTURES = [
  { label: "Cohiba Siglo VI", query: "Cohiba Siglo VI" },
  { label: "Montecristo No. 2", query: "Montecristo No. 2" },
  { label: "Partagás Serie D No. 4", query: "Partagás Serie D No. 4" },
  { label: "Romeo y Julieta Churchill", query: "Romeo y Julieta Churchill" },
  { label: "Arturo Fuente", query: "Arturo Fuente Gran Reserva Churchill" },
];

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 85 ? "text-emerald-400" : pct >= 60 ? "text-amber-400" : "text-red-400";
  return <span className={`font-bold text-xl ${color}`}>{pct}%</span>;
}

function TierBadge({ tier }: { tier: number }) {
  const name = TIER_NAMES[tier] ?? `tier-${tier}`;
  const colors: Record<string, string> = {
    SMALL: "bg-emerald-900/40 text-emerald-400 border-emerald-700",
    MEDIUM: "bg-amber-900/40 text-amber-400 border-amber-700",
    LARGE: "bg-red-900/40 text-red-400 border-red-700",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border font-mono ${
        colors[name] ?? "bg-zinc-800 text-zinc-400 border-zinc-600"
      }`}
    >
      {name}
    </span>
  );
}

const FLAG: Record<string, string> = {
  Cuba: "🇨🇺",
  Nicarágua: "🇳🇮",
  Nicaragua: "🇳🇮",
  "República Dominicana": "🇩🇴",
  Honduras: "🇭🇳",
  "Estados Unidos": "🇺🇸",
};

export default function ScanPage() {
  const [query, setQuery] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [cigarInfo, setCigarInfo] = useState<CatalogEntry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Carrega catálogo em background para lookup de pairings após reconhecimento
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  useEffect(() => {
    getCatalog().then(setCatalog).catch(() => null);
  }, []);

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      setImagePreview(dataUrl);
      // Remove o prefixo "data:image/jpeg;base64," para ficar só o base64
      setImageB64(dataUrl.split(",")[1] ?? null);
    };
    reader.readAsDataURL(file);
    setResult(null);
    setAdded(false);
  }

  function clearImage() {
    setImagePreview(null);
    setImageB64(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function onRecognize() {
    if (!query.trim() && !imageB64) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setCigarInfo(null);
    setAdded(false);
    try {
      const r = await recognizeBand(query.trim(), imageB64 ?? undefined);
      setResult(r);
      if (r.cigar_id) {
        const match = catalog.find((c) => c.id === r.cigar_id) ?? null;
        setCigarInfo(match);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao reconhecer.");
    } finally {
      setLoading(false);
    }
  }

  async function onAddToHumidor() {
    if (!result?.cigar_id) return;
    try {
      await addToCollection(result.cigar_id, `web-${result.cigar_id}-${Date.now()}`);
      setAdded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao adicionar.");
    }
  }

  const canRecognize = (query.trim().length > 0 || imageB64 !== null) && !loading;

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="text-center space-y-3 pt-4">
        <div className="inline-flex items-center gap-2 text-amber-400 text-sm font-medium tracking-widest uppercase mb-2">
          <span>&#9670;</span> Powered by AI
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
          Identifique qualquer{" "}
          <span className="text-amber-400">charuto</span> pela anilha
        </h1>
        <p className="text-zinc-400 max-w-xl mx-auto text-lg">
          IA de custo mínimo — cascata determinística antes de qualquer LLM. 117 charutos,
          5 origens, harmonizações curadas.
        </p>
      </section>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 text-center">
        {[
          { value: "117", label: "Charutos catalogados" },
          { value: "≥ 90%", label: "Acurácia band recognition" },
          { value: "$0.00", label: "Custo médio / identificação" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <div className="text-2xl font-bold text-amber-400">{s.value}</div>
            <div className="text-xs text-zinc-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Input */}
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 space-y-4">
        <h2 className="font-semibold text-zinc-300">Identificar anilha</h2>

        {/* Foto da anilha */}
        <div>
          <p className="text-xs text-zinc-500 mb-2">Foto da anilha</p>
          {imagePreview ? (
            <div className="relative inline-block">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imagePreview}
                alt="Anilha"
                className="h-36 w-auto rounded-lg border border-zinc-700 object-cover"
              />
              <button
                onClick={clearImage}
                className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-zinc-700
                           hover:bg-zinc-600 text-zinc-300 text-xs flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ) : (
            <label className="flex items-center gap-3 w-fit cursor-pointer rounded-lg border
                              border-dashed border-zinc-700 hover:border-amber-600 px-4 py-3
                              text-sm text-zinc-500 hover:text-amber-400 transition-colors">
              <span className="text-xl">📷</span>
              <span>Tirar / enviar foto</span>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={onFileChange}
              />
            </label>
          )}
          {imageB64 && (
            <p className="text-xs text-zinc-600 mt-1">
              Com API keys reais, Voyage multimodal + Gemini Flash processam a imagem.
            </p>
          )}
        </div>

        {/* Demo fixtures */}
        <div>
          <p className="text-xs text-zinc-500 mb-2">Ou use um exemplo de demo</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_FIXTURES.map((f) => (
              <button
                key={f.label}
                onClick={() => setQuery(f.query)}
                className="text-xs px-3 py-1 rounded-full border border-zinc-700 text-zinc-400
                           hover:border-amber-500 hover:text-amber-400 transition-colors"
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Texto da anilha */}
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && canRecognize && onRecognize()}
            placeholder='Texto da anilha (ex: "Cohiba Siglo VI")…'
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm
                       placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
          />
          <button
            onClick={onRecognize}
            disabled={!canRecognize}
            className="px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950
                       font-semibold text-sm disabled:opacity-40 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? "…" : "Reconhecer"}
          </button>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-4 py-2">
            {error} — certifique-se que o BFF está rodando em{" "}
            <code className="font-mono">localhost:8000</code>
          </p>
        )}
      </section>

      {/* Resultado */}
      {result && (
        <section className="rounded-2xl border border-amber-800/40 bg-zinc-900 p-6 space-y-5">
          {/* Cabeçalho: nome + métricas */}
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                Charuto identificado
              </p>
              <h3 className="text-2xl font-bold text-amber-300">
                {result.cigar_id ? cigarLabel(result.cigar_id) : "Não identificado"}
              </h3>
              {cigarInfo && (
                <div className="flex items-center gap-3 mt-1 text-sm text-zinc-400">
                  {cigarInfo.brand && <span>{cigarInfo.brand}</span>}
                  {cigarInfo.country && (
                    <span>
                      {FLAG[cigarInfo.country] ?? ""} {cigarInfo.country}
                    </span>
                  )}
                  {cigarInfo.strength && (
                    <span className="text-zinc-500">
                      {STRENGTH_PT[cigarInfo.strength] ?? cigarInfo.strength}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="text-right space-y-1 flex-shrink-0">
              <div className="flex items-center gap-2 justify-end">
                <span className="text-xs text-zinc-500">Confiança</span>
                <ConfidenceBadge value={result.confidence} />
              </div>
              <div className="flex items-center gap-2 justify-end">
                <span className="text-xs text-zinc-500">Tier</span>
                <TierBadge tier={result.tier_resolved} />
              </div>
              <div className="text-xs text-zinc-600">
                custo:{" "}
                <span className="text-emerald-500 font-mono">
                  ${result.cost_usd.toFixed(6)}
                </span>
              </div>
            </div>
          </div>

          {/* Harmonizações */}
          {cigarInfo && cigarInfo.pairings.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
                Harmonizações recomendadas
              </p>
              <div className="flex flex-wrap gap-2">
                {cigarInfo.pairings.map((p) => (
                  <span
                    key={p}
                    className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full
                               bg-amber-950/40 border border-amber-800/60 text-amber-300"
                  >
                    🥃 {p}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Alertas */}
          {result.used_vision_llm && (
            <div className="text-xs text-amber-600 bg-amber-950/30 border border-amber-900
                            rounded px-3 py-1.5">
              Fallback: Gemini Flash acionado para reconhecimento de imagem
            </div>
          )}
          {result.needs_human && (
            <div className="text-xs text-red-400 bg-red-950/30 border border-red-900 rounded
                            px-3 py-1.5">
              Baixa confiança — requer revisão humana (HITL)
            </div>
          )}

          {/* Candidatos */}
          {result.candidates.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
                Candidatos top-{result.candidates.length}
              </p>
              <div className="space-y-1.5">
                {result.candidates.map((c, i) => (
                  <div
                    key={c.cigar_id}
                    className={`flex items-center justify-between text-sm rounded px-3 py-1.5
                      ${i === 0
                        ? "bg-amber-950/30 border border-amber-900/50"
                        : "bg-zinc-800"
                      }`}
                  >
                    <span className={i === 0 ? "text-amber-300" : "text-zinc-400"}>
                      {i === 0 ? "★ " : ""}
                      {c.label ?? cigarLabel(c.cigar_id)}
                    </span>
                    <span className="font-mono text-xs text-zinc-500">
                      {(c.score * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ação */}
          {result.cigar_id && (
            <button
              onClick={onAddToHumidor}
              disabled={added}
              className="w-full py-2.5 rounded-lg border border-amber-700 text-amber-400
                         hover:bg-amber-950/40 font-medium text-sm transition-colors
                         disabled:opacity-50 disabled:cursor-default"
            >
              {added ? "✓ Adicionado ao Humidor" : "Adicionar ao Humidor"}
            </button>
          )}
        </section>
      )}
    </div>
  );
}
