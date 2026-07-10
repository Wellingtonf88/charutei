// Descobrir — catálogo (417 SKUs) com busca. F1: filtros por país/força + "adicionar/wishlist".
import { useMemo, useState } from "react";
import { View } from "react-native";

import { CatalogEntry } from "../../src/api/client";
import { useCatalog } from "../../src/api/hooks";
import { colors, space } from "../../src/theme";
import { Card, Chip, ErrorText, Field, Screen, StrengthDots, Text } from "../../src/ui";

const FLAG: Record<string, string> = {
  Cuba: "🇨🇺",
  Nicarágua: "🇳🇮",
  Nicaragua: "🇳🇮",
  "República Dominicana": "🇩🇴",
  Honduras: "🇭🇳",
  "Estados Unidos": "🇺🇸",
};

export default function Discover() {
  const { data, isLoading, isError, error } = useCatalog();
  const [q, setQ] = useState("");

  const filtered = useMemo<CatalogEntry[]>(() => {
    const all = data ?? [];
    const query = q.trim().toLowerCase();
    if (!query) return all.slice(0, 60); // F0: página inicial; F1 adiciona paginação/filtros
    return all
      .filter(
        (c: CatalogEntry) =>
          c.label.toLowerCase().includes(query) || (c.brand ?? "").toLowerCase().includes(query),
      )
      .slice(0, 60);
  }, [data, q]);

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Descobrir
      </Text>
      <Text variant="body" color={colors.textMuted}>
        {data ? `${data.length} charutos` : "Catálogo"} · busque por nome ou marca.
      </Text>

      <Field value={q} onChangeText={setQ} placeholder="Buscar…" />

      {isLoading && <Text variant="body" color={colors.textFaint}>Carregando catálogo…</Text>}
      {isError && <ErrorText>{error.message}</ErrorText>}

      <View style={{ gap: space.md }}>
        {filtered.map((c) => (
          <Card key={c.id}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text variant="heading" style={{ flex: 1 }}>
                {c.label}
              </Text>
              <Text variant="body">{FLAG[c.country ?? ""] ?? "🌍"}</Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text variant="caption" color={colors.textMuted}>
                {c.brand ?? "—"}
              </Text>
              <StrengthDots strength={c.strength} />
            </View>
            {c.pairings.length > 0 && (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
                {c.pairings.slice(0, 3).map((p) => (
                  <Chip key={p} label={p} tone="gold" />
                ))}
              </View>
            )}
          </Card>
        ))}
      </View>
    </Screen>
  );
}
