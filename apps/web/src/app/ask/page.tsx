"use client";

import { useState } from "react";
import { ask, type AskResult } from "@/lib/api";

// Degrau da cascata que resolveu (charutei_contracts.Tier) → rótulo amigável + cor.
const TIER: Record<number, { name: string; hint: string; cls: string }> = {
  1: { name: "Cache", hint: "resposta em cache", cls: "bg-zinc-700/40 border-zinc-600 text-zinc-300" },
  2: { name: "KG", hint: "grafo de conhecimento · sem LLM", cls: "bg-emerald-950/40 border-emerald-800 text-emerald-400" },
  3: { name: "Haiku", hint: "modelo pequeno", cls: "bg-sky-950/40 border-sky-800 text-sky-400" },
  4: { name: "RAG · Sonnet", hint: "recuperação + geração", cls: "bg-indigo-950/40 border-indigo-800 text-indigo-300" },
  5: { name: "Opus · agêntico", hint: "laço de ferramentas (último recurso)", cls: "bg-amber-950/40 border-amber-800 text-amber-400" },
};

const EXAMPLES = [
  "Com o que harmoniza o Cohiba Robustos?",
  "Qual o país do Davidoff Grand Cru No. 3?",
  "Como devo armazenar meus charutos no humidor?",
  "Como cortar e acender um charuto corretamente?",
];

export default function AskPage() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(question: string) {
    const text = question.trim();
    if (!text || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await ask(text));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao consultar o assistente.");
    } finally {
      setLoading(false);
    }
  }

  const tier = result ? TIER[result.tier_resolved] ?? TIER[5] : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">
          Assistente <span className="text-amber-400">de Charutos</span>
        </h1>
        <p className="text-zinc-500 mt-1 text-sm">
          Cascata cost-aware: <span className="text-emerald-500">KG</span> →{" "}
          <span className="text-indigo-400">RAG</span> →{" "}
          <span className="text-amber-500">Opus agêntico</span>. A resposta sempre cita as fontes.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(q);
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Pergunte sobre harmonização, ficha técnica, armazenamento…"
          className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm
                     placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !q.trim()}
          className="px-5 py-2 rounded-lg bg-amber-500 text-zinc-950 text-sm font-semibold
                     hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "…" : "Perguntar"}
        </button>
      </form>

      {/* Exemplos clicáveis */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => {
              setQ(ex);
              submit(ex);
            }}
            className="text-xs px-3 py-1.5 rounded-full border border-zinc-800 bg-zinc-900
                       text-zinc-400 hover:border-amber-700 hover:text-amber-500 transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-4 py-3">
          {error} — confirme que o BFF está em <code className="font-mono">localhost:8000</code>
        </p>
      )}

      {result && tier && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${tier.cls}`}>
              {tier.name}
            </span>
            <span className="text-xs text-zinc-600">{tier.hint}</span>
            <span className="ml-auto text-xs font-mono text-zinc-500">
              ${result.cost_usd.toFixed(5)}
            </span>
          </div>

          <p className="text-zinc-200 leading-relaxed whitespace-pre-wrap">
            {result.needs_human
              ? "Não encontrei base suficiente — encaminhado para revisão humana."
              : result.answer}
          </p>

          {result.citations.length > 0 && (
            <div className="border-t border-zinc-800 pt-3 space-y-1">
              <p className="text-xs text-zinc-600 uppercase tracking-wide">Fontes</p>
              <ul className="flex flex-wrap gap-1.5">
                {result.citations.map((c) => (
                  <li
                    key={c.source_id}
                    title={c.snippet ?? undefined}
                    className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-400"
                  >
                    {c.title ?? c.source_id}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
