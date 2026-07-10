// Identificar — o hero moment. Câmera → foto (data_b64) → visão → card revelado com animação.
// Modo demo (providers fake): a "visão" não lê pixels; o campo de marca abaixo alimenta o
// pipeline determinístico. Em produção (Voyage multimodal), a própria imagem identifica.
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Haptics from "expo-haptics";
import { Link } from "expo-router";
import { useRef, useState } from "react";
import { StyleSheet, View } from "react-native";

import { cigarLabel, RecognitionResult, TIER_NAMES } from "../../src/api/client";
import { useAddToCollection, useRecognize } from "../../src/api/hooks";
import { colors, radius, space } from "../../src/theme";
import { Button, Card, Chip, ErrorText, Field, Reveal, Screen, Text } from "../../src/ui";

export default function Scan() {
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [hint, setHint] = useState("");
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [added, setAdded] = useState(false);
  const recognize = useRecognize();
  const add = useAddToCollection();

  async function run(dataB64?: string, ref?: string) {
    setResult(null);
    setAdded(false);
    const res = await recognize.mutateAsync({
      ref: ref ?? `scan-${Date.now()}`,
      visualText: hint.trim() || undefined,
      dataB64,
    });
    setResult(res);
    void Haptics.notificationAsync(
      res.cigar_id && !res.needs_human
        ? Haptics.NotificationFeedbackType.Success
        : Haptics.NotificationFeedbackType.Warning,
    );
  }

  async function capture() {
    const photo = await cameraRef.current?.takePictureAsync({ base64: true, quality: 0.5 });
    await run(photo?.base64 ?? undefined, photo?.uri);
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

      {/* Câmera com moldura de alinhamento da anilha */}
      <View style={styles.cameraWrap}>
        {permission?.granted ? (
          <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
        ) : (
          <View style={styles.cameraPlaceholder}>
            <Text variant="body" color={colors.textMuted}>
              Permita a câmera para escanear a anilha.
            </Text>
            <Button title="Permitir câmera" onPress={requestPermission} variant="secondary" />
          </View>
        )}
        <View pointerEvents="none" style={styles.frame} />
      </View>

      <Button
        title="Escanear anilha"
        onPress={capture}
        loading={recognize.isPending}
        disabled={!permission?.granted}
      />

      <Text variant="caption" color={colors.textFaint}>
        MARCA / VITOLA (ajuda no modo demo)
      </Text>
      <Field
        value={hint}
        onChangeText={setHint}
        placeholder="ex.: Cohiba Robustos"
        onSubmitEditing={() => run()}
      />

      {recognize.isError && <ErrorText>{recognize.error.message}</ErrorText>}

      {result && (
        <Reveal trigger={result}>
          <Card>
            {result.cigar_id && !result.needs_human ? (
              <>
                <View style={styles.row}>
                  <Text variant="title" style={{ flex: 1 }}>
                    {cigarLabel(result.cigar_id)}
                  </Text>
                  <Chip label={TIER_NAMES[result.tier_resolved] ?? "?"} tone="gold" />
                </View>
                <View style={styles.chips}>
                  <Chip label={`confiança ${(result.confidence * 100).toFixed(0)}%`} />
                  <Chip label={result.used_vision_llm ? "com visão" : "sem visão"} />
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
                <Link
                  href={`/cigar/${encodeURIComponent(result.cigar_id)}`}
                  style={{ color: colors.gold, fontWeight: "600", fontSize: 13 }}
                >
                  Ver ficha →
                </Link>
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
                  Não deu para reconhecer com confiança. Descreva a marca e a vitola acima.
                </Text>
              </>
            )}
          </Card>
        </Reveal>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  cameraWrap: {
    height: 300,
    borderRadius: radius.lg,
    overflow: "hidden",
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  cameraPlaceholder: { alignItems: "center", gap: space.md, padding: space.lg },
  frame: {
    position: "absolute",
    left: "12%",
    right: "12%",
    top: "38%",
    bottom: "38%",
    borderWidth: 2,
    borderColor: colors.gold,
    borderRadius: radius.md,
  },
  row: { flexDirection: "row", alignItems: "center", gap: space.sm },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: space.sm, alignItems: "center" },
});
