// Perfil — paladar derivado das degustações, nível, conquistas (badges), streak e compartilhar.
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Share, View } from "react-native";

import { CatalogEntry, CollectionItem, TastingNote } from "../../src/api/client";
import { useAllTastings, useCatalog, useCollection } from "../../src/api/hooks";
import { useAuth } from "../../src/auth/context";
import {
  Badge,
  computeBadges,
  computeLevel,
  computePalate,
  computeStreak,
  shareSummary,
} from "../../src/features/insights";
import { colors, radius, space } from "../../src/theme";
import { Button, Card, Chip, Screen, Stars, Text } from "../../src/ui";

export default function Profile() {
  const { signOut } = useAuth();
  const tastings: TastingNote[] = useAllTastings().data ?? [];
  const items: CollectionItem[] = useCollection().data?.items ?? [];
  const catalog: CatalogEntry[] = useCatalog().data ?? [];

  const palate = computePalate(tastings, items, catalog);
  const level = computeLevel(palate);
  const streak = computeStreak(tastings);
  const badges = computeBadges(palate, streak);
  const progress = level.next ? Math.min(1, level.score / level.next) : 1;

  async function logout() {
    await signOut();
    router.replace("/login");
  }

  async function share() {
    await Share.share({ message: shareSummary(palate, level) });
  }

  return (
    <Screen>
      <Text variant="display" color={colors.gold}>
        Perfil
      </Text>

      {/* Nível */}
      <Card>
        <Text variant="caption" color={colors.textFaint}>
          NÍVEL
        </Text>
        <Text variant="title" color={colors.gold}>
          {level.name}
        </Text>
        <View style={{ height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceAlt }}>
          <View
            style={{
              height: 8,
              width: `${Math.round(progress * 100)}%`,
              borderRadius: radius.pill,
              backgroundColor: colors.gold,
            }}
          />
        </View>
        <Text variant="caption" color={colors.textMuted}>
          {level.next ? `${level.score}/${level.next} para o próximo nível` : "nível máximo"}
        </Text>
      </Card>

      {/* Estatísticas */}
      <View style={{ flexDirection: "row", gap: space.md }}>
        <Stat value={palate.humidorSize} label="humidor" />
        <Stat value={palate.distinctCountries} label="países" />
        <Stat value={palate.totalTastings} label="degustações" />
        <Stat value={streak} label="dias seguidos" />
      </View>

      {/* Paladar */}
      <Card>
        <Text variant="caption" color={colors.textFaint}>
          SEU PALADAR
        </Text>
        {palate.totalTastings > 0 ? (
          <>
            <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
              <Stars value={Math.round(palate.avgRating)} size={18} />
              <Text variant="caption" color={colors.textMuted}>
                média {palate.avgRating.toFixed(1)}
              </Text>
            </View>
            {palate.topFlavors.length > 0 && (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.xs }}>
                {palate.topFlavors.map((f) => (
                  <Chip key={f.key} label={`${f.key} · ${f.count}`} tone="gold" />
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
          {badges.map((b) => (
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

function BadgeView({ badge }: { badge: Badge }) {
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
