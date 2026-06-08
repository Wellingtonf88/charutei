"use client";

import { useEffect, useMemo, useState } from "react";
import { getCatalog, STRENGTH_PT, type CatalogEntry } from "@/lib/api";

const FLAG: Record<string, string> = {
  Cuba: "🇨🇺",
  Nicarágua: "🇳🇮",
  Nicaragua: "🇳🇮",
  "República Dominicana": "🇩🇴",
  Honduras: "🇭🇳",
  "Estados Unidos": "🇺🇸",
};

const STRENGTH_ORDER = ["mild", "medium", "medium-full", "full"];

function StrengthDots({ strength }: { strength: string | null }) {
  const idx = strength ? STRENGTH_ORDER.indexOf(strength) : -1;
  return (
    <div className="flex gap-0.5">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className={`w-2 h-2 rounded-full ${i <= idx ? "bg-amber-400" : "bg-zinc-700"}`}
        />
      ))}
    </div>
  );
}

export default function CatalogPage() {
  const [all, setAll] = useState<CatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterCountry, setFilterCountry] = useState("");
  const [filterStrength, setFilterStrength] = useState("");

  useEffect(() => {
    getCatalog()
      .then(setAll)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar catálogo."),
      )
      .finally(() => setLoading(false));
  }, []);

  const countries = useMemo(
    () => [...new Set(all.map((c) => c.country).filter(Boolean))].sort() as string[],
    [all],
  );

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return all.filter((c) => {
      const matchSearch =
        !q || c.label.toLowerCase().includes(q) || (c.brand ?? "").toLowerCase().includes(q);
      const matchCountry = !filterCountry || c.country === filterCountry;
      const matchStrength = !filterStrength || c.strength === filterStrength;
      return matchSearch && matchCountry && matchStrength;
    });
  }, [all, search, filterCountry, filterStrength]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">
          Catálogo <span className="text-amber-400">de Charutos</span>
        </h1>
        <p className="text-zinc-500 mt-1 text-sm">
          {all.length} SKUs verificados · 5 origens · harmonizações curadas por especialistas
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nome ou marca…"
          className="flex-1 min-w-48 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-sm
                     placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
        />
        <select
          value={filterCountry}
          onChange={(e) => setFilterCountry(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-300
                     focus:outline-none focus:border-amber-500 transition-colors"
        >
          <option value="">Todas as origens</option>
          {countries.map((c) => (
            <option key={c} value={c}>
              {FLAG[c] ?? ""} {c}
            </option>
          ))}
        </select>
        <select
          value={filterStrength}
          onChange={(e) => setFilterStrength(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-300
                     focus:outline-none focus:border-amber-500 transition-colors"
        >
          <option value="">Todas as intensidades</option>
          {STRENGTH_ORDER.map((s) => (
            <option key={s} value={s}>
              {STRENGTH_PT[s] ?? s}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-4 py-3">
          {error} — certifique-se que o BFF está rodando em{" "}
          <code className="font-mono">localhost:8000</code>
        </p>
      )}

      {loading && <p className="text-zinc-600 text-sm">Carregando catálogo…</p>}

      {!loading && !error && (
        <>
          <p className="text-xs text-zinc-600">
            {filtered.length} de {all.length} charutos
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((c) => (
              <div
                key={c.id}
                className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3
                           hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-zinc-200 leading-tight">{c.label}</h3>
                  <span className="text-lg flex-shrink-0">{FLAG[c.country ?? ""] ?? "🌍"}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">{c.brand ?? "—"}</span>
                  <StrengthDots strength={c.strength} />
                </div>

                {c.strength && (
                  <div className="text-xs text-zinc-600">
                    {STRENGTH_PT[c.strength] ?? c.strength}
                  </div>
                )}

                {c.pairings.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {c.pairings.slice(0, 3).map((p) => (
                      <span
                        key={p}
                        className="text-xs px-2 py-0.5 rounded-full bg-amber-950/40
                                   border border-amber-900/50 text-amber-500"
                      >
                        {p}
                      </span>
                    ))}
                    {c.pairings.length > 3 && (
                      <span className="text-xs text-zinc-600">
                        +{c.pairings.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
