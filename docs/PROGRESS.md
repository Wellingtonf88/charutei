# PROGRESS — MVP do CHARUTEI

Registro de avanço por slice vertical (S0–S7). Princípio reitor: **"LLM é o último recurso."**

## Legenda de status
✅ concluído · 🚧 em andamento · ⬜ pendente

| Slice | Descrição | Status |
|---|---|---|
| S0 | Fundação (scaffold, docker-compose, CI, CLAUDE.md) | ✅ |
| S1 | Conhecimento (OLTP + KG relacional + interfaces) | ✅ |
| S2 | Cascata (Router + Registry + Governance + cache + Langfuse) | ✅ |
| S3 | Band Recognition Agent | ✅ |
| S4 | Eventos (outbox + worker + DLQ) | ⬜ |
| S5 | Assistant + RAG mínimo | ⬜ |
| S6 | Mobile (Expo) | ⬜ |
| S7 | Evals & CI (gates) | ⬜ |

---

## S3 — Band Recognition Agent (✅)
**Entregue:**
- **Contrato** `BandImage` / `BandCandidate` / `BandRecognitionResult` (`{cigar_id, confidence, candidates[], needs_human}`).
- **Providers de visão** atrás de interface: `ImageEmbeddingProvider` (Voyage multimodal), `OCRProvider`,
  `VisionProvider` (Gemini Flash) + `Fake*` determinísticos + `build_band_providers`; pricing de visão.
- **Pipeline** (`services/agents/band_recognition`): embedding → ANN (pgvector) → desempate por OCR →
  fallback de visão **só quando ambíguo e autorizado**. Incerto → `needs_human` (não inventa).
- **Catálogo** indexado no espaço vetorial (`build_band_catalog`). **Governance**: `allow_vision_fallback`
  (gating de visão por autorização). **Registry**: spec do agente.
- **Eval `band_recognition`** no CI (gate: acurácia ≥0,90 e ≥80% sem visão) + dataset versionado.
- **Integração pgvector** validada no banco real (ANN cosseno `<=>` + filtro por metadado).

**Testes/evals:** ruff ✓ · format ✓ · mypy (25 arquivos) ✓ · **pytest 37 passed, 2 skipped** ·
integração Postgres **2 passed** (DB real) · **eval band_recognition PASS**.

**Métricas (10 anilhas de eval):** **acurácia 100%** · **90% resolvido sem LLM de visão** (1/10 via visão).
Ambos os gates de aceite satisfeitos (≥80% sem visão ✓; acurácia ≥0,90 ✓).

**Decisão de design:** removi um threshold de confiança redundante que criava "zona morta"
(0,85–0,92 → `needs_human` indevido). Visão agora é o fallback de qualquer caso não resolvido por
embedding/OCR, gated apenas por autorização no Registry. **Nota:** acurácia real exige Voyage multimodal +
imagens reais; os fakes exercitam a *lógica* do pipeline (thresholds/desempate/gating).

## S2 — Cascata (✅)
**Entregue:**
- **Provedores atrás de interface** (`LLMProvider`/`EmbeddingProvider`/`Tracer`) + `Fake*` determinísticos +
  fábrica `build_providers` (lê `USE_FAKE_PROVIDERS`). Tabela de preços jun/2026 + `llm_cost`.
- **Registry** declarativo (`AgentSpec`: tier máximo, orçamento de tokens, gating de Opus, kill-switch).
- **Governance**: teto de tier, orçamento (degradação graciosa), gating de Opus (confiança+autorização), kill-switch.
- **Router determinístico** (`classify`, sem LLM): harmonização / fato / geral.
- **Cache** `packages/cache`: exato (hash) + semântico (vetorial, threshold conservador), **invalidação por
  versão do KG** (namespace por versão), backends in-memory + Redis.
- **Cascade**: motor `1 cache → 2 KG/SQL → 3/4 geração → 5 Opus(gated)`, tracing por etapa, cache write-back.
- **Métricas** (`cascade_metrics`) + **eval `cascade_efficiency`** no CI (gate ≥70% sem Opus, ≤US$0,005/msg).

**Testes/evals:** ruff ✓ · format ✓ · mypy (21 arquivos) ✓ · **pytest 31 passed, 1 skipped** ·
**eval cascade_efficiency PASS**.

**Métricas da cascata (dataset de eval, 11 consultas):** **100% sem Opus** · custo médio **$0.00007/msg** ·
distribuição: DETERMINISTIC 64% · MEDIUM (Sonnet) 36% · CACHE/SMALL/LARGE 0%. (Limites de aceite: ≥70%
sem Opus ✓ ; ≤US$0,005/msg ✓.)

**Decisões:** provedores reais ainda não ligados — `build_providers(use_fake=False)` falha com mensagem
clara até o adaptador real entrar na slice correspondente (geração na S5, Voyage/visão na S3).

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
Instrumentadas na S2 via `Tracer` (Langfuse na produção). No dataset de eval atual: **100% sem Opus**,
custo médio **$0.00007/msg**, 64% resolvido no degrau determinístico (KG).
