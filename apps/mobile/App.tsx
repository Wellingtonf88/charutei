// CHARUTEI — app mobile (cliente). Fluxo: login → captura de anilha → resultado → coleção.
// O app não tem inteligência: delega tudo ao BFF, que aciona a cascata cost-aware no backend.
import { CameraView, useCameraPermissions } from "expo-camera";
import { StatusBar } from "expo-status-bar";
import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Button,
  FlatList,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  addToCollection,
  getCollection,
  recognizeBand,
  type Collection,
  type RecognitionResult,
} from "./src/api";

type Screen = "login" | "capture" | "result" | "collection";

export default function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [token, setToken] = useState("");
  const [bandText, setBandText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [collection, setCollection] = useState<Collection | null>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  async function onRecognize() {
    setBusy(true);
    setError(null);
    try {
      let ref = `capture-${Date.now()}`;
      if (cameraRef.current) {
        const photo = await cameraRef.current.takePictureAsync({ quality: 0.6 });
        if (photo?.uri) ref = photo.uri;
      }
      const res = await recognizeBand(token, { ref, visualText: bandText });
      setResult(res);
      setScreen("result");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onAdd() {
    if (!result?.cigar_id) return;
    setBusy(true);
    setError(null);
    try {
      const col = await addToCollection(token, result.cigar_id, `add-${result.cigar_id}-${Date.now()}`);
      setCollection(col);
      setScreen("collection");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function openCollection() {
    setBusy(true);
    try {
      setCollection(await getCollection(token));
      setScreen("collection");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="auto" />
      <Text style={styles.title}>CHARUTEI</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      {busy && <ActivityIndicator />}

      {screen === "login" && (
        <View style={styles.block}>
          <Text>Entre com seu token (dev: qualquer texto).</Text>
          <TextInput style={styles.input} value={token} onChangeText={setToken} placeholder="token" autoCapitalize="none" />
          <Button title="Entrar" onPress={() => token.trim() && setScreen("capture")} />
        </View>
      )}

      {screen === "capture" && (
        <View style={styles.block}>
          {permission?.granted ? (
            <CameraView ref={cameraRef} style={styles.camera} facing="back" />
          ) : (
            <Button title="Permitir câmera" onPress={requestPermission} />
          )}
          <Text>Texto da anilha (MVP: simula o que a visão/OCR lê):</Text>
          <TextInput style={styles.input} value={bandText} onChangeText={setBandText} placeholder="ex.: Cohiba Robustos" />
          <Button title="Reconhecer anilha" onPress={onRecognize} disabled={busy} />
          <Button title="Minha coleção" onPress={openCollection} />
        </View>
      )}

      {screen === "result" && result && (
        <View style={styles.block}>
          <Text style={styles.subtitle}>Resultado</Text>
          <Text>charuto: {result.cigar_id ?? "—"}</Text>
          <Text>confiança: {(result.confidence * 100).toFixed(0)}%</Text>
          <Text>precisou de humano: {result.needs_human ? "sim" : "não"}</Text>
          <Text>usou visão (LLM): {result.used_vision_llm ? "sim" : "não"}</Text>
          {result.cigar_id && !result.needs_human ? (
            <Button title="Adicionar à coleção" onPress={onAdd} disabled={busy} />
          ) : (
            <Text style={styles.error}>Anilha não identificada com confiança — revise manualmente.</Text>
          )}
          <Button title="Nova captura" onPress={() => setScreen("capture")} />
        </View>
      )}

      {screen === "collection" && (
        <View style={styles.block}>
          <Text style={styles.subtitle}>Meu humidor</Text>
          <FlatList
            data={collection?.items ?? []}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <Text>• {item.cigar_id} (x{item.quantity})</Text>
            )}
            ListEmptyComponent={<Text>Coleção vazia.</Text>}
          />
          <Button title="Voltar" onPress={() => setScreen("capture")} />
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, gap: 12 },
  title: { fontSize: 28, fontWeight: "700", textAlign: "center" },
  subtitle: { fontSize: 20, fontWeight: "600" },
  block: { gap: 10 },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10 },
  camera: { height: 280, borderRadius: 12, overflow: "hidden" },
  error: { color: "#b00020" },
});
