// Descobrir — catálogo (417 SKUs) com busca + filtros (país/força). Card → ficha do charuto.
import { Link } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, ScrollView, View } from "react-native";

import { CatalogEntry, STRENGTH_PT } from "../../src/api/client";
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
const STRENGTHS = ["mild", "medium", "medium-full", "full"];

function FilterPill({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress}>
      <View
        style={{
          paddingHorizontal: space.md,
          paddingVertical: space.xs,
          borderRadius: 999,
          borderWidth: 1,
          borderColor: active ? colors.gold : colors.border,
          backgroundColor: active ? "rgba(212,162,78,0.12)" : colors.surfaceAlt,
        }}
      >
        <Text variant="caption" color={active ? colors.gold : colors.textMuted}>
          {label}
        </Text>
      </View>
    </Pressable>
  );
}

export default function Discover() {
  const { data, isLoading, isError, error } = useCatalog();
  const [q, setQ] = useState("");
  const [country, setCountry] = useState<string | null>(null);
  const [strength, setStrength] = useState<string | null>(null);

  const cigars: CatalogEntry[] = data ?? [];

  const countries = useMemo(
    () => [...new Set(cigars.map((c) => c.country).filter(Boolean))].sort() as string[],
    [data],
  );

  const filtered = useMemo<CatalogEntry[]>(() => {
    const query = q.trim().toLowerCase();
    return cigars
      .filter((c: CatalogEntry) => {
        const matchQ =
          !query ||
          c.label.toLowerCase().includes(query) ||
          (c.brand ?? "").toLowerCase().includes(query);
        const matchCountry = !country || c.country === country;
        const matchStrength = !strength || c.strength === strength;
        return matchQ && matchCountry && matchStrength;
      })
      .slice(0, 80);
  }, [data, q, country, strength]);

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Descobrir
      </Text>
      <Text variant="body" color={colors.textMuted}>
        {data ? `${data.length} charutos` : "Catálogo"} · {filtered.length} exibidos
      </Text>

      <Field value={q} onChangeText={setQ} placeholder="Buscar por nome ou marca…" />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles_chips}>
        <FilterPill label="Todos" active={!country} onPress={() => setCountry(null)} />
        {countries.map((c) => (
          <FilterPill
            key={c}
            label={`${FLAG[c] ?? ""} ${c}`.trim()}
            active={country === c}
            onPress={() => setCountry(country === c ? null : c)}
          />
        ))}
      </ScrollView>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles_chips}>
        <FilterPill label="Toda força" active={!strength} onPress={() => setStrength(null)} />
        {STRENGTHS.map((s) => (
          <FilterPill
            key={s}
            label={STRENGTH_PT[s] ?? s}
            active={strength === s}
            onPress={() => setStrength(strength === s ? null : s)}
          />
        ))}
      </ScrollView>

      {isLoading && <Text variant="body" color={colors.textFaint}>Carregando catálogo…</Text>}
      {isError && <ErrorText>{error.message}</ErrorText>}

      <View style={{ gap: space.md }}>
        {filtered.map((c: CatalogEntry) => (
          <Link key={c.id} href={`/cigar/${encodeURIComponent(c.id)}`} asChild>
            <Pressable>
              <Card>
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
            </Pressable>
          </Link>
        ))}
      </View>
    </Screen>
  );
}

const styles_chips = { gap: space.sm, paddingRight: space.lg } as const;
