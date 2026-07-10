// Perfil — sessão, progresso (F3: paladar/badges) e logout.
import { router } from "expo-router";
import { View } from "react-native";

import { useAuth } from "../../src/auth/context";
import { useCollection } from "../../src/api/hooks";
import { colors, space } from "../../src/theme";
import { Button, Card, Screen, Text } from "../../src/ui";

export default function Profile() {
  const { token, signOut } = useAuth();
  const { data } = useCollection();
  const masked = token ? `${token.slice(0, 3)}••••` : "—";

  async function logout() {
    await signOut();
    router.replace("/login");
  }

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Perfil
      </Text>

      <Card>
        <Text variant="caption" color={colors.textFaint}>
          SESSÃO
        </Text>
        <Text variant="heading">{masked}</Text>
      </Card>

      <Card>
        <Text variant="caption" color={colors.textFaint}>
          PROGRESSO
        </Text>
        <View style={{ flexDirection: "row", gap: space.xl }}>
          <View>
            <Text variant="title" color={colors.gold}>
              {data?.items.length ?? 0}
            </Text>
            <Text variant="caption" color={colors.textMuted}>
              no humidor
            </Text>
          </View>
        </View>
      </Card>

      <Button title="Sair" onPress={logout} variant="secondary" />
    </Screen>
  );
}
