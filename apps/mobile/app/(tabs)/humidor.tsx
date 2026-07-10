// Humidor — a coleção do usuário, com aging (descanso) por charuto. Card → ficha.
import { Link, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, View } from "react-native";

import { cigarLabel, CollectionItem } from "../../src/api/client";
import { useCollection } from "../../src/api/hooks";
import { AddedMap, daysSince, getAddedMap, REST_DAYS } from "../../src/store/aging";
import { colors, space } from "../../src/theme";
import { Card, Chip, ErrorText, Screen, Text } from "../../src/ui";

export default function Humidor() {
  const { data, isLoading, isError, error, refetch } = useCollection();
  const [aging, setAging] = useState<AddedMap>({});

  useFocusEffect(
    useCallback(() => {
      void refetch();
      void getAddedMap().then(setAging);
    }, [refetch]),
  );

  const items = data?.items ?? [];

  return (
    <Screen>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" }}>
        <Text variant="display" color={colors.gold}>
          Humidor
        </Text>
        <Text variant="caption" color={colors.textMuted}>
          {items.length} {items.length === 1 ? "charuto" : "charutos"}
        </Text>
      </View>

      {isLoading && <Text variant="body" color={colors.textFaint}>Carregando…</Text>}
      {isError && <ErrorText>{error.message}</ErrorText>}

      {!isLoading && items.length === 0 && (
        <Card>
          <Text variant="heading">Humidor vazio</Text>
          <Text variant="body" color={colors.textMuted}>
            Identifique uma anilha na aba Identificar para começar sua coleção.
          </Text>
        </Card>
      )}

      <View style={{ gap: space.md }}>
        {items.map((item: CollectionItem) => {
          const iso = aging[item.cigar_id];
          const days = iso ? daysSince(iso) : null;
          const rested = days !== null && days >= REST_DAYS;
          return (
            <Link key={item.id} href={`/cigar/${encodeURIComponent(item.cigar_id)}`} asChild>
              <Pressable>
                <Card>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                    <Text variant="heading" style={{ flex: 1 }}>
                      {cigarLabel(item.cigar_id)}
                    </Text>
                    {item.quantity > 1 && (
                      <Text variant="label" color={colors.gold}>
                        ×{item.quantity}
                      </Text>
                    )}
                  </View>
                  {days !== null && (
                    <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                      <Text variant="caption" color={colors.textMuted}>
                        descansando há {days} {days === 1 ? "dia" : "dias"}
                      </Text>
                      {rested && <Chip label="pronto" tone="gold" />}
                    </View>
                  )}
                </Card>
              </Pressable>
            </Link>
          );
        })}
      </View>
    </Screen>
  );
}
