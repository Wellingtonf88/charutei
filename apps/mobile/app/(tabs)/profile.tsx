// Perfil — passaporte de experiências (Km de Fumaça). Scores/status/badges vêm do backend
// (Fase 3 do upgrade: calculados no servidor, consistentes entre dispositivos, não
// manipuláveis pelo cliente) via GET /profile.
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Share, View } from "react-native";

import { ProfileBadge } from "../../src/api/client";
import { useProfile } from "../../src/api/hooks";
import { useAuth } from "../../src/auth/context";
import { shareSummary } from "../../src/features/insights";
import { colors, radius, space } from "../../src/theme";
import { Button, Card, Chip, Screen, Stars, Text } from "../../src/ui";

export default function Profile() {
  const { signOut } = useAuth();
  const profile = useProfile().data;

  async function logout() {
    await signOut();
    router.replace("/login");
  }

  async function share() {
    if (profile) await Share.share({ message: shareSummary(profile) });
  }

  if (!profile) {
    return (
      <Screen>
        <Text variant="display" color={colors.gold}>
          Perfil
        </Text>
        <Text variant="body" color={colors.textMuted}>
          Carregando seu passaporte de experiências…
        </Text>
      </Screen>
    );
  }

  const { consumer_status: status } = profile;

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Perfil
      </Text>

      {/* Status */}
      <Card>
        <Text variant="caption" color={colors.textFaint}>
          STATUS
        </Text>
        <Text variant="title" color={colors.gold}>
          {status.name}
        </Text>
        <View style={{ height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceAlt }}>
          <View
            style={{
              height: 8,
              width: `${Math.round(status.progress * 100)}%`,
              borderRadius: radius.pill,
              backgroundColor: colors.gold,
            }}
          />
        </View>
        <Text variant="caption" color={colors.textMuted}>
          {status.next_threshold
            ? `${status.combined_score}/${status.next_threshold} para o próximo status`
            : "status máximo"}
        </Text>
      </Card>

      {/* Estatísticas */}
      <View style={{ flexDirection: "row", gap: space.md }}>
        <Stat value={profile.humidor_size} label="humidor" />
        <Stat value={profile.distinct_countries} label="países" />
        <Stat value={profile.total_tastings} label="degustações" />
        <Stat value={profile.streak_days} label="dias seguidos" />
      </View>

      {/* Paladar */}
      <Card>
        <Text variant="caption" color={colors.textFaint}>
          SEU PALADAR
        </Text>
        {profile.total_tastings > 0 ? (
          <>
            <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
              <Stars value={Math.round(profile.avg_rating)} size={18} />
              <Text variant="caption" color={colors.textMuted}>
                média {profile.avg_rating.toFixed(1)}
              </Text>
            </View>
            {profile.top_flavors.length > 0 && (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
                {profile.top_flavors.map((f) => (
                  <Chip key={f} label={f} tone="gold" />
                ))}
              </View>
            )}
          </>
        ) : (
          <Text variant="body" color={colors.textMuted}>
            Registre degustações (na ficha de um charuto) para revelar seu perfil de paladar.
          </Text>
        )}
      </Card>

      {/* Conquistas */}
      <Card>
        <Text variant="caption" color={colors.textFaint}>
          CONQUISTAS
        </Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.md }}>
          {profile.badges.map((b) => (
            <BadgeView key={b.id} badge={b} />
          ))}
        </View>
      </Card>

      <Button title="Compartilhar meu paladar" onPress={share} />
      <Button title="Sair" onPress={logout} variant="secondary" />
    </Screen>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <View style={{ flex: 1 }}>
      <Text variant="title" color={colors.gold}>
        {value}
      </Text>
      <Text variant="caption" color={colors.textMuted}>
        {label}
      </Text>
    </View>
  );
}

function BadgeView({ badge }: { badge: ProfileBadge }) {
  const tint = badge.earned ? colors.gold : colors.textFaint;
  return (
    <View style={{ width: 96, alignItems: "center", gap: space.xs, opacity: badge.earned ? 1 : 0.5 }}>
      <View
        style={{
          width: 52,
          height: 52,
          borderRadius: radius.pill,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: badge.earned ? "rgba(212,162,78,0.12)" : colors.surfaceAlt,
          borderWidth: 1,
          borderColor: badge.earned ? colors.goldSoft : colors.border,
        }}
      >
        <Ionicons name={badge.icon as keyof typeof Ionicons.glyphMap} size={24} color={tint} />
      </View>
      <Text variant="caption" color={badge.earned ? colors.text : colors.textFaint} style={{ textAlign: "center" }}>
        {badge.label}
      </Text>
    </View>
  );
}
