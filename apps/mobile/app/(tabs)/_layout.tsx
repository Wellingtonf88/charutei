// Navegação principal por abas. Guard: sem sessão, volta ao login.
import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { ComponentProps } from "react";

import { useAuth } from "../../src/auth/context";
import { colors } from "../../src/theme";

type IoniconName = ComponentProps<typeof Ionicons>["name"];

function tab(name: IoniconName) {
  return ({ color, size }: { color: string; size: number }) => (
    <Ionicons name={name} color={color} size={size} />
  );
}

export default function TabsLayout() {
  const { token, loading } = useAuth();
  if (!loading && !token) return <Redirect href="/login" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.gold,
        tabBarInactiveTintColor: colors.textFaint,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
        },
        tabBarLabelStyle: { fontSize: 11 },
      }}
    >
      <Tabs.Screen
        name="scan"
        options={{ title: "Identificar", tabBarIcon: tab("scan-outline") }}
      />
      <Tabs.Screen
        name="sommelier"
        options={{ title: "Sommelier", tabBarIcon: tab("sparkles-outline") }}
      />
      <Tabs.Screen
        name="humidor"
        options={{ title: "Humidor", tabBarIcon: tab("albums-outline") }}
      />
      <Tabs.Screen
        name="discover"
        options={{ title: "Descobrir", tabBarIcon: tab("compass-outline") }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: "Perfil", tabBarIcon: tab("person-outline") }}
      />
    </Tabs>
  );
}
