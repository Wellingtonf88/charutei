// Login. Demo: qualquer token entra (FakeAuthProvider no BFF). Produção: fluxo Supabase.
import { router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";

import { useAuth } from "../src/auth/context";
import { colors, space } from "../src/theme";
import { Button, ErrorText, Field, Screen, Text } from "../src/ui";

export default function Login() {
  const { signIn } = useAuth();
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enter() {
    if (!token.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await signIn(token.trim());
      router.replace("/(tabs)/scan");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen scroll={false}>
      <View style={{ flex: 1, justifyContent: "center", gap: space.lg }}>
        <View style={{ alignItems: "center", gap: space.sm, marginBottom: space.xl }}>
          <Text variant="display" color={colors.gold}>
            CHARUTEI
          </Text>
          <Text variant="body" color={colors.textMuted}>
            O sommelier de charutos no seu bolso.
          </Text>
        </View>
        <Text variant="label" color={colors.textMuted}>
          Seu token de acesso
        </Text>
        <Field
          value={token}
          onChangeText={setToken}
          placeholder="dev: qualquer texto"
          onSubmitEditing={enter}
        />
        {error && <ErrorText>{error}</ErrorText>}
        <Button title="Entrar" onPress={enter} loading={busy} disabled={!token.trim()} />
      </View>
    </Screen>
  );
}
