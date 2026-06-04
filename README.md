# CHARUTEI

Plataforma **AI-First** para apreciadores de charutos. A inteligência vive no backend (conhecimento +
vetores + eventos + agentes); o app mobile é apenas um cliente.

> **Princípio inviolável:** *"LLM é o último recurso, não o primeiro."* Toda requisição desce pela
> **cascata de inteligência** e para no degrau mais barato:
> `cache → KG/SQL → Haiku/embeddings → Sonnet+RAG → Opus (gated)`.

## Pré-requisitos
- macOS com **OrbStack** (Docker leve) — ou Docker Engine compatível.
- **uv** (gerenciador Python) com Python **3.12**.
- Node 20+ (para o app Expo, a partir da S6).

## Passo a passo (dev local)
```bash
# 1. Bootstrap de tooling (instala/checa OrbStack + uv + Python 3.12)
./scripts/bootstrap.sh

# 2. Subir o plano de dados local (Postgres+pgvector, Redis)
docker compose -f infra/docker-compose.yml up -d

# 3. Instalar dependências do workspace
uv sync --all-packages --dev

# 4. Configurar ambiente (sem segredos por padrão — usa provedores FAKE)
cp .env.example .env

# 5. Rodar a verificação
uv run ruff check .
uv run pytest -q
```

## Estrutura
Monorepo modular monolith. Ver `CLAUDE.md` (princípios/convenções) e `docs/PROGRESS.md` (avanço por slice).

```
apps/mobile  services/{api,orchestrator,agents,workers}  packages/{knowledge,cache,contracts}
infra  evals  docs
```

## Roadmap (slices)
S0 Fundação · S1 Conhecimento · S2 Cascata · S3 Band Recognition · S4 Eventos ·
S5 Assistant+RAG · S6 Mobile · S7 Evals & CI.

Custos e modelos referenciados são preços de lista de jun/2026 e devem ser revalidados.
