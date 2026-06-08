"use client";

import { useEffect, useState } from "react";
import { cigarLabel, getCollection, type Collection } from "@/lib/api";

export default function HumidorPage() {
  const [collection, setCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCollection()
      .then(setCollection)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar coleção."),
      )
      .finally(() => setLoading(false));
  }, []);

  const items = collection?.items ?? [];

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            Humidor <span className="text-amber-400">Digital</span>
          </h1>
          <p className="text-zinc-500 mt-1 text-sm">
            Sua coleção pessoal de charutos.
          </p>
        </div>
        {!loading && !error && (
          <div className="text-right">
            <div className="text-2xl font-bold text-amber-400">{items.length}</div>
            <div className="text-xs text-zinc-500">
              {items.length === 1 ? "charuto" : "charutos"}
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-4 py-3">
          {error} — certifique-se que o BFF está rodando em{" "}
          <code className="font-mono">localhost:8000</code>
        </p>
      )}

      {loading && (
        <div className="text-zinc-600 text-sm">Carregando coleção…</div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center">
          <div className="text-4xl mb-3">&#9670;</div>
          <p className="text-zinc-500 text-sm">
            Humidor vazio. Identifique um charuto e adicione à coleção.
          </p>
          <a
            href="/"
            className="inline-block mt-4 text-amber-400 hover:text-amber-300 text-sm underline"
          >
            Identificar agora
          </a>
        </div>
      )}

      {items.length > 0 && (
        <div className="grid gap-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-xl border border-zinc-800
                         bg-zinc-900 px-5 py-4"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-amber-900/40 border border-amber-800
                                flex items-center justify-center text-amber-400 text-xs font-bold">
                  {cigarLabel(item.cigar_id).charAt(0)}
                </div>
                <div>
                  <div className="font-medium text-zinc-200">
                    {cigarLabel(item.cigar_id)}
                  </div>
                  <div className="text-xs text-zinc-600 font-mono">{item.cigar_id}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-amber-400">{item.quantity}</div>
                <div className="text-xs text-zinc-600">
                  {item.quantity === 1 ? "unidade" : "unidades"}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
