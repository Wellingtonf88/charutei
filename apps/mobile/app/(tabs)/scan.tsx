// Identificar anilha. F0: entrada por texto (pipeline determinístico) + card revelado.
// F1: câmera → foto → visão (data_b64) + animação de revelação (hero moment).
import * as Haptics from "expo-haptics";
import { useState } from "react";
import { View } from "react-native";

import { cigarLabel, RecognitionResult, TIER_NAMES } from "../../src/api/client";
import { useAddToCollection, useRecognize } from "../../src/api/hooks";
import { colors, space } from "../../src/theme";
import { Button, Card, Chip, ErrorText, Field, Screen, Text } from "../../src/ui";

export default function Scan() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const recognize = useRecognize();
  const add = useAddToCollection();
  const [added, setAdded] = useState(false);

  async function onScan() {
    if (!text.trim()) return;
    setResult(null);
    setAdded(false);
    const res = await recognize.mutateAsync({ ref: `scan-${Date.now()}`, visualText: text.trim() });
    setResult(res);
    void Haptics.notificationAsync(
      res.cigar_id && !res.needs_human
        ? Haptics.NotificationFeedbackType.Success
        : Haptics.NotificationFeedbackType.Warning,
    );
  }

  async function onAdd() {
    if (!result?.cigar_id) return;
    await add.mutateAsync(result.cigar_id);
    setAdded(true);
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  }

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Identificar
      </Text>
      <Text variant="body" color={colors.textMuted}>
        Descreva a anilha (ou, em breve, aponte a câmera) e a IA reconhece o charuto.
      </Text>

      <Field
        value={text}
        onChangeText={setText}
        placeholder="ex.: Cohiba Robustos"
        onSubmitEditing={onScan}
      />
      <Button
        title="Reconhecer anilha"
        onPress={onScan}
        loading={recognize.isPending}
        disabled={!text.trim()}
      />
      {recognize.isError && <ErrorText>{recognize.error.message}</ErrorText>}

      {result && (
        <Card>
          {result.cigar_id && !result.needs_human ? (
            <>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text variant="title">{cigarLabel(result.cigar_id)}</Text>
                <Chip label={`${TIER_NAMES[result.tier_resolved] ?? "?"}`} tone="gold" />
              </View>
              <View style={{ flexDirection: "row", gap: space.sm }}>
                <Chip label={`confiança ${(result.confidence * 100).toFixed(0)}%`} />
                <Chip label={result.used_vision_llm ? "com visão" : "sem visão"} />
                <Chip label={`$${result.cost_usd.toFixed(5)}`} />
              </View>
              {result.candidates.length > 1 && (
                <View style={{ gap: space.xs }}>
                  <Text variant="caption" color={colors.textFaint}>
                    OUTROS CANDIDATOS
                  </Text>
                  {result.candidates.slice(1, 4).map((c) => (
                    <Text key={c.cigar_id} variant="caption" color={colors.textMuted}>
                      {c.label ?? cigarLabel(c.cigar_id)} · {(c.score * 100).toFixed(0)}%
                    </Text>
                  ))}
                </View>
              )}
              {added ? (
                <Text variant="label" color={colors.success}>
                  ✓ Adicionado ao humidor
                </Text>
              ) : (
                <Button title="Adicionar ao humidor" onPress={onAdd} loading={add.isPending} />
              )}
            </>
          ) : (
            <>
              <Text variant="heading">Anilha não identificada</Text>
              <Text variant="body" color={colors.textMuted}>
                Não deu para reconhecer com confiança. Tente descrever a marca e a vitola.
              </Text>
            </>
          )}
        </Card>
      )}
    </Screen>
  );
}
