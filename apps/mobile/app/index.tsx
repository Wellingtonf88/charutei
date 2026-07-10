// Porta de entrada: decide entre login e o app conforme a sessão persistida.
import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";

import { useAuth } from "../src/auth/context";
import { colors } from "../src/theme";

export default function Index() {
  const { token, loading } = useAuth();
  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, justifyContent: "center" }}>
        <ActivityIndicator color={colors.gold} />
      </View>
    );
  }
  return <Redirect href={token ? "/(tabs)/scan" : "/login"} />;
}
