# PROGRESS — MVP do CHARUTEI

Registro de avanço por slice vertical (S0–S7). Princípio reitor: **"LLM é o último recurso."**

## Legenda de status
✅ concluído · 🚧 em andamento · ⬜ pendente

| Slice | Descrição | Status |
|---|---|---|
| S0 | Fundação (scaffold, docker-compose, CI, CLAUDE.md) | ✅ |
| S1 | Conhecimento (OLTP + KG relacional + interfaces) | ✅ |
| S2 | Cascata (Router + Registry + Governance + cache + Langfuse) | ⬜ |
| S3 | Band Recognition Agent | ⬜ |
| S4 | Eventos (outbox + worker + DLQ) | ⬜ |
| S5 | Assistant + RAG mínimo | ⬜ |
| S6 | Mobile (Expo) | ⬜ |
| S7 | Evals & CI (gates) | ⬜ |

---

## S1 — Conhecimento (✅)
**Entregue:**
- `packages/knowledge`: interfaces (Protocols) `KnowledgeGraphRepo`, `VectorRepository`, `OltpRepository`.
- Modelos de domínio (`KGNode`/`KGEdge`, `NodeType`/`EdgeRel`, `User`/`Band`/`Collection`/`CollectionItem`).
- Impl **in-memory** (testada) e impl **Postgres** (SQL puro + pgvector via `::vector`) — mesmas interfaces.
- KG **relacional**: `kg_nodes`/`kg_edges`/`kg_version` + `embeddings`; `schema.sql` (fonte) + **Alembic** `0001_initial`.
- Seed curado de **32 charutos reais** (`evals/datasets/cigars_seed.json`) + loader idempotente `seed_knowledge_graph`.

**Testes/evals:** ruff ✓ · format ✓ · mypy (12 arquivos) ✓ · **pytest 11 passed, 1 skipped** (integração
Postgres pula sem `CHARUTEI_TEST_DATABASE_URL`).

**Pendência de verificação (não bloqueia S1):** aplicar Alembic e rodar o teste de integração exigem
Postgres no ar (OrbStack) — `docker compose up` + `uv run --extra postgres alembic ... upgrade head`.

**Próximos passos registrados (controlados, não inventar dados):**
- Expandir o seed para 100–300 SKUs ingerindo de **catálogo verificado** (Habanos S.A., Halfwheel,
  Cigar Aficionado). Campos incertos (ex.: fábrica por SKU) permanecem `null` até confirmação.
- Enriquecimento automático do KG por evento entra na S4+ (Cigar Intelligence — fora do MVP atual).

## S0 — Fundação (✅)
**Entregue:**
- uv workspace (`pyproject.toml` raiz + `packages/contracts`), Python 3.12, ruff/pytest/mypy.
- `packages/contracts`: `Tier`, `CascadeResult`, `Citation` + smoke test.
- `infra/docker-compose.yml`: Postgres (`pgvector/pgvector:pg16`) + Redis, com healthchecks.
- `.env.example` (sem segredos), `USE_FAKE_PROVIDERS=true`.
- `CLAUDE.md` (ajustado p/ KG relacional), `.claude/commands/` (new-agent, cost-check, slice-done), `settings.json`.
- CI (`.github/workflows/ci.yml`): lint + format + mypy + pytest + gitleaks; job de evals placeholder.
- `scripts/bootstrap.sh` + `docs/BOOTSTRAP.md`.

**Decisões registradas:**
- KG **relacional** no MVP (sem Apache AGE); interface `KnowledgeGraphRepo` permite swap p/ AGE/Neo4j na escala.
- Bootstrap via **OrbStack + uv**; provedores **mockados primeiro**, chave real por slice.

**Próximos passos (fora do MVP, registrados):** Supabase Auth/Storage entram na S6; Apache AGE/Qdrant/Neo4j
só por gatilho de escala.

## Métricas da cascata
_Sem tráfego ainda — instrumentação de tier/custo entra na S2 (Langfuse)._
