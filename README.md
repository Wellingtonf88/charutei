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

# 5. Verificação completa (lint + tipos + testes + os 4 gates de eval)
./scripts/verify.sh
```

## Banco de dados (migrações)
O schema (OLTP + KG relacional + vetor + eventos) é versionado em Alembic:
```bash
DATABASE_URL=postgresql+psycopg://charutei:charutei@localhost:5432/charutei \
  uv run --extra postgres alembic -c packages/knowledge/alembic.ini upgrade head
```
Os testes de integração Postgres rodam quando há banco:
```bash
CHARUTEI_TEST_DATABASE_URL=postgresql://charutei:charutei@localhost:5432/charutei \
  uv run --extra postgres pytest -q
```

## Rodar o BFF e o app
```bash
# API (BFF) em http://localhost:8000
uv run --extra serve uvicorn charutei_api.main:app --port 8000

# App mobile (Expo) — ver apps/mobile/README.md
cd apps/mobile && npm install && npx expo start
```

## Evals (gates de qualidade e custo)
```bash
uv run python -m evals            # roda os 4 gates; sai !=0 se algum reprovar
```
Os 4 gates (Anexo C) e seu mapeamento aos critérios de aceite estão em
[`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md).

## Estrutura
Monorepo modular monolith. Ver `CLAUDE.md` (princípios/convenções) e `docs/PROGRESS.md` (avanço por slice).

```
apps/mobile  services/{api,orchestrator,agents,workers}  packages/{knowledge,cache,contracts}
infra  evals  docs
```

## Roadmap (slices) — todas concluídas
S0 Fundação · S1 Conhecimento · S2 Cascata · S3 Band Recognition · S4 Eventos ·
S5 Assistant+RAG · S6 Mobile+BFF · S7 Evals & CI. Status detalhado em `docs/PROGRESS.md`.

## Provedores reais (por slice)
Por padrão `USE_FAKE_PROVIDERS=true` (zero custo/chave). Para ligar serviços reais, preencha a chave
necessária em `.env` e defina `USE_FAKE_PROVIDERS=false`. Nenhum SDK é chamado fora do Orchestrator —
trocar fake↔real é injeção de implementação.

Custos e modelos referenciados são preços de lista de jun/2026 e devem ser revalidados.
