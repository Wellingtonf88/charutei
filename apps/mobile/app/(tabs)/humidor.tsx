// Humidor — a coleção do usuário. F0: lista themed. F1: estante visual + aging tracker.
import { useFocusEffect } from "expo-router";
import { useCallback } from "react";
import { View } from "react-native";

import { cigarLabel, CollectionItem } from "../../src/api/client";
import { useCollection } from "../../src/api/hooks";
import { colors, space } from "../../src/theme";
import { Card, ErrorText, Screen, Text } from "../../src/ui";

export default function Humidor() {
  const { data, isLoading, isError, error, refetch } = useCollection();

  // Reconsulta ao focar a aba (após adicionar um charuto na tela Identificar).
  useFocusEffect(
    useCallback(() => {
      void refetch();
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
        {items.map((item: CollectionItem) => (
          <Card key={item.id}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text variant="heading">{cigarLabel(item.cigar_id)}</Text>
              {item.quantity > 1 && (
                <Text variant="label" color={colors.gold}>
                  ×{item.quantity}
                </Text>
              )}
            </View>
          </Card>
        ))}
      </View>
    </Screen>
  );
}
