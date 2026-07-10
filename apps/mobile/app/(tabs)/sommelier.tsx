// Sommelier IA — o assistente (/ask). Mostra o degrau da cascata que resolveu (KG/RAG/Opus)
// como sinal de confiança + as fontes citadas (groundedness). Diferencial do produto.
import { useState } from "react";
import { View } from "react-native";

import { AskResult, cigarLabel, TIER_NAMES } from "../../src/api/client";
import { useAsk, useCollection } from "../../src/api/hooks";
import { colors, space } from "../../src/theme";
import { Button, Card, Chip, ErrorText, Field, Screen, Text } from "../../src/ui";

const EXAMPLES = [
  "Com o que harmoniza o Cohiba Robustos?",
  "Como armazenar charutos no humidor?",
  "Qual a diferença entre um charuto suave e encorpado?",
];

export default function Sommelier() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const ask = useAsk();
  const { data: collection } = useCollection();

  async function send(question: string) {
    const text = question.trim();
    if (!text) return;
    setResult(null);
    setResult(await ask.mutateAsync(text));
  }

  // Recomendação contextual: monta a pergunta a partir do humidor do usuário.
  async function recommendFromHumidor() {
    const items = collection?.items ?? [];
    if (items.length === 0) {
      await send("Sou iniciante e quero montar meu humidor. Que charuto você recomenda para começar?");
      return;
    }
    const names = items.slice(0, 8).map((i: { cigar_id: string }) => cigarLabel(i.cigar_id));
    await send(
      `Tenho estes charutos no meu humidor: ${names.join(", ")}. ` +
        "Com base nisso, recomende uma harmonização e um próximo charuto para eu experimentar.",
    );
  }

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Sommelier
      </Text>
      <Text variant="body" color={colors.textMuted}>
        Pergunte sobre harmonização, ficha técnica ou armazenamento. Toda resposta cita a fonte.
      </Text>

      <Field
        value={q}
        onChangeText={setQ}
        placeholder="Faça uma pergunta…"
        autoCapitalize="sentences"
        onSubmitEditing={() => send(q)}
      />
      <Button title="Perguntar" onPress={() => send(q)} loading={ask.isPending} disabled={!q.trim()} />
      <Button
        title="✨ Recomendar do meu humidor"
        onPress={recommendFromHumidor}
        variant="secondary"
        loading={ask.isPending}
      />

      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.sm }}>
        {EXAMPLES.map((ex) => (
          <View key={ex} style={{ flexBasis: "100%" }}>
            <Text
              variant="caption"
              color={colors.gold}
              onPress={() => {
                setQ(ex);
                void send(ex);
              }}
            >
              › {ex}
            </Text>
          </View>
        ))}
      </View>

      {ask.isError && <ErrorText>{ask.error.message}</ErrorText>}

      {result && (
        <Card>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Chip
              label={TIER_NAMES[result.tier_resolved] ?? "?"}
              tone={result.tier_resolved <= 2 ? "gold" : "neutral"}
            />
            <Text variant="caption" color={colors.textFaint}>
              ${result.cost_usd.toFixed(5)}
            </Text>
          </View>
          <Text variant="body" color={colors.text}>
            {result.needs_human
              ? "Não encontrei base suficiente para responder com segurança."
              : result.answer}
          </Text>
          {result.citations.length > 0 && (
            <View style={{ gap: space.xs, borderTopColor: colors.border, borderTopWidth: 1, paddingTop: space.sm }}>
              <Text variant="caption" color={colors.textFaint}>
                FONTES
              </Text>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
                {result.citations.map((c) => (
                  <Chip key={c.source_id} label={c.title ?? c.source_id} />
                ))}
              </View>
            </View>
          )}
        </Card>
      )}
    </Screen>
  );
}
