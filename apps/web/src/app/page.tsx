"use client";

import { useState } from "react";
import {
  addToCollection,
  cigarLabel,
  recognizeBand,
  STRENGTH_PT,
  TIER_NAMES,
  type RecognitionResult,
} from "@/lib/api";

const DEMO_FIXTURES = [
  { label: "Cohiba Siglo VI", query: "Cohiba Siglo VI" },
  { label: "Montecristo No. 2", query: "Montecristo No. 2" },
  { label: "Partagás Serie D", query: "Partagás Serie D No. 4" },
  { label: "Arturo Fuente", query: "Arturo Fuente Gran Reserva Churchill" },
  { label: "Oliva Serie V", query: "Oliva Serie V Double Toro" },
];

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 85 ? "text-emerald-400" : pct >= 60 ? "text-amber-400" : "text-red-400";
  return <span className={`font-bold text-xl ${color}`}>{pct}%</span>;
}

function TierBadge({ tier }: { tier: number }) {
  const name = TIER_NAMES[tier] ?? String(tier);
  const colors: Record<string, string> = {
    SMALL: "bg-emerald-900/40 text-emerald-400 border-emerald-700",
    MEDIUM: "bg-amber-900/40 text-amber-400 border-amber-700",
    LARGE: "bg-red-900/40 text-red-400 border-red-700",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border font-mono ${colors[name] ?? "bg-zinc-800 text-zinc-400 border-zinc-600"}`}
    >
      {name}
    </span>
  );
}

export default function ScanPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState(false);

  async function onRecognize() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setAdded(false);
    try {
      const r = await recognizeBand(query.trim());
      setResult(r);
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

        {/* Demo fixtures */}
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

        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onRecognize()}
            placeholder='Ex: "Cohiba Siglo VI" ou texto da anilha...'
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm
                       placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
          />
          <button
            onClick={onRecognize}
            disabled={loading || !query.trim()}
            className="px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950
                       font-semibold text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "..." : "Reconhecer"}
          </button>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-4 py-2">
            {error} — certifique-se que o BFF está rodando em{" "}
            <code className="font-mono">localhost:8000</code>
          </p>
        )}
      </section>

      {/* Result */}
      {result && (
        <section className="rounded-2xl border border-amber-800/40 bg-zinc-900 p-6 space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                Charuto identificado
              </p>
              <h3 className="text-2xl font-bold text-amber-300">
                {result.cigar_id ? cigarLabel(result.cigar_id) : "Não identificado"}
              </h3>
            </div>
            <div className="text-right space-y-1">
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

          {result.used_vision_llm && (
            <div className="text-xs text-amber-600 bg-amber-950/30 border border-amber-900 rounded px-3 py-1.5">
              Fallback: Gemini Flash acionado para reconhecimento de imagem
            </div>
          )}

          {result.needs_human && (
            <div className="text-xs text-red-400 bg-red-950/30 border border-red-900 rounded px-3 py-1.5">
              Baixa confiança — requer revisão humana (HITL)
            </div>
          )}

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
                      ${i === 0 ? "bg-amber-950/30 border border-amber-900/50" : "bg-zinc-800"}`}
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
