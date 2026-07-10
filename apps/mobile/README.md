# CHARUTEI — App Mobile (Expo)

O **produto final**. Cliente do BFF (a inteligência vive no backend). Arquitetura de app de
verdade a partir da F0: **expo-router** (abas), **design system** próprio, **React Query**
(estado servidor) e **auth persistente** (secure-store).

## Rodar
```bash
# 1. Suba o BFF (na raiz do repo)
uv run --extra serve uvicorn charutei_api.main:app --port 8000

# 2. Instale e rode o app
cd apps/mobile
npm install
npx expo start           # Expo Go (iOS/Android) ou simulador
```

Configure a URL da API em `app.json` (`extra.apiBaseUrl`). Simulador iOS: `http://localhost:8000`;
device físico: o IP da sua máquina.

## Arquitetura (F0)
```
app/                      # rotas (expo-router)
  _layout.tsx             # providers: React Query + Auth + SafeArea
  index.tsx              # gate de sessão → login ou tabs
  login.tsx
  (tabs)/                # Identificar · Sommelier · Humidor · Descobrir · Perfil
src/
  theme.ts               # design tokens (paleta tabaco/âmbar)
  ui/                     # primitivos (Screen/Text/Button/Card/Chip/Field/StrengthDots)
  api/client.ts          # cliente do BFF (recognize/collection/catalog/ask)
  api/hooks.ts           # hooks React Query
  auth/context.tsx       # sessão persistida (expo-secure-store)
```

## Telas (F0)
- **Identificar** — reconhece a anilha (texto → pipeline) e revela o card do charuto.
- **Sommelier** — o assistente IA (`/ask`): resposta + degrau da cascata (KG/RAG/Opus) + fontes.
- **Humidor** — a coleção do usuário.
- **Descobrir** — catálogo (417 SKUs) com busca.
- **Perfil** — sessão, progresso e logout.

## Roadmap
- **F1**: câmera → foto → visão (`data_b64`) + animação de revelação (hero moment); catálogo com
  filtros; detalhe do charuto.
- **F2**: Sommelier contextual ao humidor; tasting notes; aging tracker + push.
- **F3**: perfil de paladar, compartilhamento de tasting card, gamificação.

## Notas
- **Auth**: token livre em dev (FakeAuthProvider no BFF); produção usa Supabase (JWT, já validado no BFF).
- **Status**: F0 valida por `tsc --noEmit` + `expo config`; **execução em simulador pendente** (requer
  device/simulador iOS/Android fora deste ambiente).
