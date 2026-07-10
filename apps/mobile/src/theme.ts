// Design tokens do CHARUTEI — linguagem visual premium ("clube de charutos à noite").
// Fonte única de cor/espaçamento/tipografia; os primitivos em src/ui os consomem.
// Trocável por NativeWind/Tamagui depois sem tocar nas telas (só nos primitivos).

export const colors = {
  // Fundos (carvão/tabaco)
  bg: "#14110E",
  surface: "#1E1A15",
  surfaceAlt: "#26211B",
  border: "#3A332A",
  // Marca (âmbar/dourado)
  gold: "#D4A24E",
  goldSoft: "#8A6A2E",
  // Texto
  text: "#F3EEE4",
  textMuted: "#A79B87",
  textFaint: "#6E6455",
  // Estados
  danger: "#E5766B",
  success: "#7FB389",
  // Degraus da cascata (KG/RAG/Opus) — cores semânticas reutilizadas no Sommelier
  tierKg: "#7FB389",
  tierRag: "#8AA0D4",
  tierOpus: "#D4A24E",
} as const;

export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
} as const;

export const font = {
  // Serifada editorial para títulos; sans do sistema para dados (F0 usa system; fontes
  // customizadas (Fraunces) entram na F1 via expo-font).
  display: { fontSize: 30, fontWeight: "700" as const, letterSpacing: 0.2 },
  title: { fontSize: 22, fontWeight: "700" as const },
  heading: { fontSize: 18, fontWeight: "600" as const },
  body: { fontSize: 15, fontWeight: "400" as const },
  label: { fontSize: 13, fontWeight: "600" as const },
  caption: { fontSize: 12, fontWeight: "400" as const },
} as const;

export const theme = { colors, space, radius, font } as const;
export type Theme = typeof theme;
