// Primitivos de UI do CHARUTEI — a base do design system (consomem src/theme).
// Telas montam só com estes componentes; trocar a lib de estilo depois = mexer só aqui.
import { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text as RNText,
  TextInput,
  TextProps,
  View,
  ViewProps,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";

import { colors, font, radius, space } from "../theme";

type Variant = keyof typeof font;

export function Text({
  variant = "body",
  color = colors.text,
  style,
  ...rest
}: TextProps & { variant?: Variant; color?: string }) {
  return <RNText style={[font[variant], { color }, style]} {...rest} />;
}

export function Screen({
  children,
  scroll = true,
  ...rest
}: ViewProps & { children: ReactNode; scroll?: boolean }) {
  const inner = (
    <View style={styles.screenInner} {...rest}>
      {children}
    </View>
  );
  return (
    <SafeAreaView style={styles.screen} edges={["top", "left", "right"]}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {inner}
        </ScrollView>
      ) : (
        inner
      )}
    </SafeAreaView>
  );
}

export function Card({ children, style, ...rest }: ViewProps & { children: ReactNode }) {
  return (
    <View style={[styles.card, style]} {...rest}>
      {children}
    </View>
  );
}

export function Button({
  title,
  onPress,
  variant = "primary",
  loading = false,
  disabled = false,
}: {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "ghost";
  loading?: boolean;
  disabled?: boolean;
}) {
  const isDisabled = disabled || loading;
  const press = () => {
    if (isDisabled) return;
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress();
  };
  return (
    <Pressable
      onPress={press}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.btn,
        styles[`btn_${variant}`],
        pressed && !isDisabled && styles.btnPressed,
        isDisabled && styles.btnDisabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "primary" ? colors.bg : colors.gold} />
      ) : (
        <Text
          variant="label"
          color={variant === "primary" ? colors.bg : colors.gold}
          style={styles.btnLabel}
        >
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export function Chip({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "gold" }) {
  return (
    <View style={[styles.chip, tone === "gold" && styles.chipGold]}>
      <Text variant="caption" color={tone === "gold" ? colors.gold : colors.textMuted}>
        {label}
      </Text>
    </View>
  );
}

export function Field({
  value,
  onChangeText,
  placeholder,
  autoCapitalize = "none",
  onSubmitEditing,
}: {
  value: string;
  onChangeText: (t: string) => void;
  placeholder?: string;
  autoCapitalize?: "none" | "sentences";
  onSubmitEditing?: () => void;
}) {
  return (
    <TextInput
      style={styles.field}
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor={colors.textFaint}
      autoCapitalize={autoCapitalize}
      onSubmitEditing={onSubmitEditing}
      returnKeyType="send"
    />
  );
}

// Intensidade em pontos (mild→full) — leitura instantânea, reaproveitada no card e no catálogo.
const STRENGTH_ORDER = ["mild", "medium", "medium-full", "full"];
export function StrengthDots({ strength }: { strength: string | null }) {
  const idx = strength ? STRENGTH_ORDER.indexOf(strength) : -1;
  return (
    <View style={styles.dots}>
      {[0, 1, 2, 3].map((i) => (
        <View key={i} style={[styles.dot, i <= idx && styles.dotOn]} />
      ))}
    </View>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  return (
    <Text variant="caption" color={colors.danger}>
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  scrollContent: { flexGrow: 1 },
  screenInner: { flex: 1, padding: space.xl, gap: space.lg },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.md,
  },
  btn: {
    height: 50,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: space.lg,
  },
  btn_primary: { backgroundColor: colors.gold },
  btn_secondary: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  btn_ghost: { backgroundColor: "transparent" },
  btnPressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  btnDisabled: { opacity: 0.4 },
  btnLabel: { letterSpacing: 0.3 },
  chip: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipGold: { backgroundColor: "rgba(212,162,78,0.12)", borderColor: colors.goldSoft },
  field: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    color: colors.text,
    fontSize: font.body.fontSize,
  },
  dots: { flexDirection: "row", gap: space.xs },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.border },
  dotOn: { backgroundColor: colors.gold },
});
