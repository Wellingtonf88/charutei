// Ficha do charuto — dados do catálogo + aging (descanso) + registro/histórico de degustações.
import * as Haptics from "expo-haptics";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Pressable, View } from "react-native";

import {
  CatalogEntry,
  cigarLabel,
  CollectionItem,
  FLAVORS,
  STRENGTH_PT,
  TastingNote,
} from "../../src/api/client";
import { useAddToCollection, useAddTasting, useCatalog, useCollection, useTastings } from "../../src/api/hooks";
import { daysSince, REST_DAYS } from "../../src/store/aging";
import { colors, space } from "../../src/theme";
import {
  Button,
  Card,
  Chip,
  Field,
  Screen,
  SelectChip,
  Stars,
  StrengthDots,
  Text,
} from "../../src/ui";

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

  // Servidor: aging (created_at do item na coleção) + degustações deste charuto.
  const { data: collection } = useCollection();
  const items: CollectionItem[] = collection?.items ?? [];
  const item = items.find((i) => i.cigar_id === cigarId);
  const tastingsQuery = useTastings(cigarId);
  const tastings: TastingNote[] = tastingsQuery.data ?? [];
  const addTasting = useAddTasting();

  const [rating, setRating] = useState(0);
  const [flavors, setFlavors] = useState<string[]>([]);
  const [occasion, setOccasion] = useState("");
  const [note, setNote] = useState("");

  async function onAdd() {
    await add.mutateAsync(cigarId);
    setAdded(true);
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  }

  function toggleFlavor(f: string) {
    setFlavors((prev) => (prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]));
  }

  async function saveTasting() {
    if (rating === 0) return;
    await addTasting.mutateAsync({ cigarId, rating, flavors, occasion: occasion.trim(), note: note.trim() });
    void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setRating(0);
    setFlavors([]);
    setOccasion("");
    setNote("");
  }

  const restDays = item?.created_at ? daysSince(item.created_at) : null;
  const rested = restDays !== null && restDays >= REST_DAYS;

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

      {/* Aging / descanso */}
      {restDays !== null && (
        <Card>
          <Text variant="caption" color={colors.textFaint}>
            NO HUMIDOR
          </Text>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Text variant="heading">
              {restDays} {restDays === 1 ? "dia" : "dias"} de descanso
            </Text>
            <Chip
              label={rested ? "pronto" : `descansa +${REST_DAYS - restDays}d`}
              tone={rested ? "gold" : "neutral"}
            />
          </View>
        </Card>
      )}

      {cigar && (
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
          {cigar.pairings.length > 0 && (
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
              {cigar.pairings.map((p) => (
                <Chip key={p} label={p} tone="gold" />
              ))}
            </View>
          )}
        </Card>
      )}

      {added ? (
        <Text variant="label" color={colors.success}>
          ✓ Adicionado ao humidor
        </Text>
      ) : (
        <Button title="Adicionar ao humidor" onPress={onAdd} loading={add.isPending} />
      )}

      {/* Registrar degustação */}
      <Card>
        <Text variant="heading">Registrar degustação</Text>
        <Stars value={rating} onChange={setRating} />
        <Text variant="caption" color={colors.textFaint}>
          SABORES
        </Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
          {FLAVORS.map((f) => (
            <SelectChip key={f} label={f} active={flavors.includes(f)} onPress={() => toggleFlavor(f)} />
          ))}
        </View>
        <Field value={occasion} onChangeText={setOccasion} placeholder="Ocasião (ex.: pós-jantar)" autoCapitalize="sentences" />
        <Field value={note} onChangeText={setNote} placeholder="Nota pessoal…" autoCapitalize="sentences" />
        <Button
          title="Salvar degustação"
          onPress={saveTasting}
          disabled={rating === 0}
          loading={addTasting.isPending}
        />
      </Card>

      {/* Histórico */}
      {tastings.length > 0 && (
        <View style={{ gap: space.md }}>
          <Text variant="heading">Suas degustações</Text>
          {tastings.map((t) => (
            <Card key={t.id}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                <Stars value={t.rating} size={16} />
                {t.created_at && (
                  <Text variant="caption" color={colors.textFaint}>
                    {new Date(t.created_at).toLocaleDateString("pt-BR")}
                  </Text>
                )}
              </View>
              {t.flavors.length > 0 && (
                <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
                  {t.flavors.map((f) => (
                    <Chip key={f} label={f} />
                  ))}
                </View>
              )}
              {!!t.occasion && (
                <Text variant="caption" color={colors.textMuted}>
                  {t.occasion}
                </Text>
              )}
              {!!t.note && <Text variant="body">{t.note}</Text>}
            </Card>
          ))}
        </View>
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
