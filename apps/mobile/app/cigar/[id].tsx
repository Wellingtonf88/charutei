// Ficha do charuto. Busca no catálogo em cache (React Query); acessível do scan e do Descobrir.
import * as Haptics from "expo-haptics";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Pressable, View } from "react-native";

import { CatalogEntry, cigarLabel, STRENGTH_PT } from "../../src/api/client";
import { useAddToCollection, useCatalog } from "../../src/api/hooks";
import { colors, space } from "../../src/theme";
import { Button, Card, Chip, Screen, StrengthDots, Text } from "../../src/ui";

const FLAG: Record<string, string> = {
  Cuba: "🇨🇺",
  Nicarágua: "🇳🇮",
  Nicaragua: "🇳🇮",
  "República Dominicana": "🇩🇴",
  Honduras: "🇭🇳",
  "Estados Unidos": "🇺🇸",
};

export default function CigarDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const cigarId = decodeURIComponent(id ?? "");
  const { data } = useCatalog();
  const add = useAddToCollection();
  const [added, setAdded] = useState(false);

  const cigars: CatalogEntry[] = data ?? [];
  const cigar = cigars.find((c) => c.id === cigarId);
  const title = cigar?.label ?? cigarLabel(cigarId);

  async function onAdd() {
    await add.mutateAsync(cigarId);
    setAdded(true);
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  }

  return (
    <Screen>
      <Stack.Screen options={{ headerShown: false }} />
      <Pressable onPress={() => router.back()}>
        <Text variant="label" color={colors.gold}>
          ‹ Voltar
        </Text>
      </Pressable>

      <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
        <Text variant="display" style={{ flex: 1 }}>
          {title}
        </Text>
        <Text variant="display">{FLAG[cigar?.country ?? ""] ?? "🌍"}</Text>
      </View>

      {cigar ? (
        <>
          <Card>
            <Row label="Marca" value={cigar.brand ?? "—"} />
            <Row label="País" value={cigar.country ?? "—"} />
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text variant="caption" color={colors.textFaint}>
                INTENSIDADE
              </Text>
              <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
                <Text variant="body" color={colors.textMuted}>
                  {cigar.strength ? (STRENGTH_PT[cigar.strength] ?? cigar.strength) : "—"}
                </Text>
                <StrengthDots strength={cigar.strength} />
              </View>
            </View>
          </Card>

          {cigar.pairings.length > 0 && (
            <Card>
              <Text variant="caption" color={colors.textFaint}>
                HARMONIZAÇÕES
              </Text>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
                {cigar.pairings.map((p) => (
                  <Chip key={p} label={p} tone="gold" />
                ))}
              </View>
            </Card>
          )}
        </>
      ) : (
        <Text variant="body" color={colors.textMuted}>
          Carregando ficha…
        </Text>
      )}

      {added ? (
        <Text variant="label" color={colors.success}>
          ✓ Adicionado ao humidor
        </Text>
      ) : (
        <Button title="Adicionar ao humidor" onPress={onAdd} loading={add.isPending} />
      )}
    </Screen>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
      <Text variant="caption" color={colors.textFaint}>
        {label.toUpperCase()}
      </Text>
      <Text variant="body">{value}</Text>
    </View>
  );
}
