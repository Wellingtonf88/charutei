# Deploy — CHARUTEI

Artefatos: **BFF** (imagem Docker) + **web** (Vercel). Padrão seguro: providers fake + auth fake
em dev; produção liga persistência, auth real e CORS estrito por env.

## BFF (FastAPI) via Docker

Build a partir da **raiz do repo** (a imagem precisa do workspace uv completo):

```bash
docker build -f infra/Dockerfile.api -t charutei-bff .
# demo standalone (in-memory, fake providers):
docker run --rm -p 8000:8000 charutei-bff
curl localhost:8000/healthz    # {"status":"ok"}
```

### Stack completa (BFF + Postgres + Redis, persistência durável)

```bash
docker compose -f infra/docker-compose.prod.yml up --build
```

O BFF sobe com `DATABASE_URL` apontando para o Postgres do compose → KG (417 SKUs, semeados no
1º boot) e coleção **persistem** entre restarts.

### Variáveis de ambiente

| Var | Efeito | Default |
|---|---|---|
| `DATABASE_URL` | Postgres (KG+OLTP duráveis). Vazio → in-memory | vazio |
| `USE_FAKE_PROVIDERS` | `false` liga LLM/embeddings reais (imagem precisa de `--extra providers`) | `true` |
| `ANTHROPIC_API_KEY` / `VOYAGE_API_KEY` / `GEMINI_API_KEY` | chaves dos providers reais | vazio |
| `CHARUTEI_ENV` | `production` ativa padrões estritos + **fail-fast de auth** | vazio |
| `SUPABASE_JWT_SECRET` / `SUPABASE_JWT_AUD` | auth real (JWT HS256) | vazio / `authenticated` |
| `CHARUTEI_CORS_ORIGINS` | origens permitidas (CSV) — nunca `*` | localhost (dev) / `[]` (prod) |
| `CHARUTEI_RATE_LIMIT` / `CHARUTEI_RATE_WINDOW_S` | rate limit por cliente (`0` desliga) | `300` / `60` |
| `CHARUTEI_DATA_DIR` | caminho do catálogo/corpus | `/app/data` (na imagem) |

### Providers reais (opcional)

A imagem padrão instala só `serve`+`postgres` (roda com fake). Para LLMs reais, adicione
`--extra providers` ao `uv sync` no [Dockerfile](../infra/Dockerfile.api), rebuild, e rode com
`USE_FAKE_PROVIDERS=false` + as chaves.

## Web (Next.js) via Vercel

1. Novo projeto Vercel apontando para este repo; **Root Directory = `apps/web`** (ver
   [vercel.json](../apps/web/vercel.json)).
2. Env `NEXT_PUBLIC_API_URL` = URL pública do BFF (o proxy `/api/**` em `next.config.mjs` a usa).
3. Deploy — build `npm run build` (Next.js 15).

## Checklist de produção

- [ ] `DATABASE_URL` (Postgres gerenciado) — não usar in-memory.
- [ ] `CHARUTEI_ENV=production` + `SUPABASE_JWT_SECRET` (sem isso o BFF **recusa subir**).
- [ ] `CHARUTEI_CORS_ORIGINS` = domínio do web (nunca `*`).
- [ ] Chaves de provider + `USE_FAKE_PROVIDERS=false` (se quiser IA real).
- [ ] TLS/HTTPS no gateway à frente do BFF.

## Limitações conhecidas (escala)

- Rate limit é **in-memory por processo** → múltiplas réplicas exigem store compartilhado (Redis).
- BFF usa **uma conexão Postgres por processo** → alta concorrência exige pool + checkout por
  request (refatora `packages/knowledge`).
- `uv.lock` não é versionado → builds não são 100% reprodutíveis (pinar para produção).
