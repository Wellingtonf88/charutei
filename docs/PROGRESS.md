# PROGRESS — MVP do CHARUTEI

Registro de avanço por slice vertical (S0–S8). Princípio reitor: **"LLM é o último recurso."**

## Legenda de status
✅ concluído · 🚧 em andamento · ⬜ pendente

| Slice | Descrição | Status |
|---|---|---|
| S0 | Fundação (scaffold, docker-compose, CI, CLAUDE.md) | ✅ |
| S1 | Conhecimento (OLTP + KG relacional + interfaces) | ✅ |
| S2 | Cascata (Router + Registry + Governance + cache + Langfuse) | ✅ |
| S3 | Band Recognition Agent | ✅ |
| S4 | Eventos (outbox + worker + DLQ) | ✅ |
| S5 | Assistant + RAG mínimo | ✅ |
| S6 | Mobile (Expo) + BFF | ✅ |
| S7 | Evals & CI (gates) | ✅ |
| S8 | Cigar Intelligence — ingestão de catálogo de SKU no KG | ✅ |
| S9 | Adaptadores reais: Anthropic + Voyage + Gemini | ✅ |
| S10 | Embeddings reais no pgvector + eval ANN | ✅ |
| S11w | Frontend web (Next.js) para demo de investidores | ✅ |
| S13 | Multi-agêntico — fundação do laço agêntico (tool-use) | ✅ |
| S14 | Multi-agêntico — ferramentas MCP + AnthropicToolRunner real | ✅ |
| S15 | Multi-agêntico — Supervisor (roteador determinístico) + gating | ✅ |
| S16 | Multi-agêntico — laço ligado no Assistant + /ask + eval | ✅ |
| S11 | Auth real — SupabaseAuthProvider (JWT HS256) | ✅ |

---

## F2 — Engajamento & retenção do app mobile (✅)
**Contexto:** camada que faz o usuário voltar. **Local-first no device** — a versão sincronizada
no backend (tasting/aging no Postgres) toca `packages/knowledge` → **plan-gated (F2.5)**.

**Entregue** (`apps/mobile`):
- **Sommelier contextual**: botão "Recomendar do meu humidor" monta a pergunta a partir da coleção
  e chama `/ask`.
- **Tasting notes** (AsyncStorage): na ficha do charuto — rating (estrelas), sabores (chips),
  ocasião e nota; histórico por charuto. Primitivos `Stars`/`SelectChip` no design system.
- **Aging tracker**: registra a entrada no humidor, mostra "descansando há N dias" na ficha e no
  humidor, e **agenda notificação local de descanso** (30 dias) via `expo-notifications` (Expo Go).
- Humidor e Descobrir com cards clicáveis → ficha.

**Validação:** `tsc --noEmit` limpo · `expo config` OK. Deps: async-storage, expo-notifications.
**Simulador pendente.** Próximo: **F2.5** (sync backend de tasting/aging — plan-gated) e **F3**
(perfil de paladar, compartilhamento, gamificação).

---

## F1 — Core experience do app mobile (✅)
**Entregue** (`apps/mobile`):
- **Identificar (hero moment):** câmera (`expo-camera`) → foto (`data_b64`, pronto p/ Voyage
  multimodal em produção) + hint de marca (modo demo) → **card revelado com animação** (`Reveal`:
  fade+slide+scale, `Animated` nativo) + candidatos ranqueados + link "Ver ficha". Haptics no scan/adição.
- **Ficha do charuto** (`app/cigar/[id]`): marca/país/força + harmonizações (chips) + adicionar ao humidor.
- **Descobrir:** filtros por país e força (pills roláveis) + busca; card clicável → ficha.
- Design system ganhou o primitivo `Reveal` (sem dep nova).

**Validação:** `tsc --noEmit` limpo · `expo config` OK · 10 rotas. Correção de tipos: `data` do
React Query fixado na fronteira (const tipado) para `find`/`map` ganharem tipo real. **Simulador pendente.**

---

## F0 — Fundação do app mobile (produto) (✅)
**Contexto:** auditoria de produto mostrou o backend production-hardened mas o mobile — o produto
final — como protótipo single-file (`App.tsx`, 155 linhas, componentes nativos crus, sem navegação
nem design). F0 monta a fundação de um app de verdade.

**Entregue** (`apps/mobile`):
- **Navegação `expo-router`**: `app/_layout` (providers) + gate de sessão + `login` + **5 abas**
  (Identificar · Sommelier · Humidor · Descobrir · Perfil).
- **Design system**: `src/theme.ts` (tokens — paleta tabaco/âmbar premium) + `src/ui` (primitivos
  Screen/Text/Button/Card/Chip/Field/StrengthDots com haptics).
- **Estado servidor**: React Query (`src/api/client` + `hooks`) — recognize/collection/catalog/ask.
- **Auth persistente**: `expo-secure-store` (sobrevive a restart) via `AuthContext`.
- **5 telas funcionais** já ligadas ao BFF (inclui o **Sommelier IA `/ask`** — antes ausente no
  mobile — e o **catálogo 417** em Descobrir).
- Deps: `expo-router`, `@tanstack/react-query`, `expo-secure-store`, `expo-haptics`, safe-area/screens.

**Validação:** `tsc --noEmit` limpo · `expo config` OK · 9 rotas registradas. **Execução em
simulador pendente** (requer device iOS/Android — fora deste ambiente).

**Salto de exposição:** o mobile passou de ~30% para expor reconhecimento + assistente IA + catálogo
417 + humidor. Próximo: **F1** (câmera→visão + hero moment de revelação; filtros; detalhe do charuto).

---

## S21 — Artefatos de deploy (P1) (✅)
**Contexto:** faltava caminho de publicação. Entregues e **validados por build local**.

**Entregue:**
- **`infra/Dockerfile.api`** — imagem do BFF multi-stage (uv), **non-root**, ~296MB. Instala o
  workspace + extras `serve`+`postgres`; providers reais opt-in. Build a partir da raiz do repo.
- **`.dockerignore`** — enxuga o contexto (só workspace Python + `data/` + `evals/datasets` do seed).
- **`infra/docker-compose.prod.yml`** — stack self-hosted BFF + Postgres + Redis (persistência
  durável; healthchecks; env de segurança/providers comentadas).
- **`apps/web/vercel.json`** + **`docs/DEPLOY.md`** — deploy do web (Vercel, Root=`apps/web`,
  `NEXT_PUBLIC_API_URL`) + runbook completo (env, providers reais, checklist de produção, limitações).

**Validação (build + run local):** imagem builda; container sobe (lifespan semeia+ingere **417 SKUs**
in-memory); `/healthz` ✓, `/catalog` 417, `/ask` **KG ancorado (tier 2, 2 citações)**; roda como
usuário `app` (non-root).

**Correções durante a validação:** faltava `README.md` (exigido pelo build do pacote raiz) e
`evals/datasets/cigars_seed.json` (o seed do KG lê de `<root>/evals/datasets`) — ambos incluídos.

**Limitações documentadas:** `uv.lock` não versionado → builds não 100% reprodutíveis (pinar p/
prod); acoplamento do seed a `evals/datasets` (mover p/ `packages/knowledge` é plan-gated).

---

## S20 — Cobertura de testes no CI (P2) (✅)
**Contexto:** auditoria apontou ausência de métrica de cobertura. Fechado com piso no CI.

**Entregue:**
- `pytest-cov` no grupo `dev`; config `[tool.coverage.*]` no pyproject (`source = packages, services`;
  omite tests/migrations; `fail_under = 85`, `show_missing`, `skip_covered`).
- CI e `scripts/verify.sh` rodam `pytest --cov --cov-report=term-missing` → **build reprova abaixo de 85%**.

**Medição:** cobertura atual **90.9%** (2845 statements). Piso 85% dá margem anti-flaky; os adaptadores
reais (Anthropic/Voyage/Gemini/MCP) só rodam sob chave (skipif) e contam como não-cobertos no CI.
Simulação do ambiente do CI (sem `mcp`): **90.1%** — folga confortável sobre o piso.

---

## S19 — Endurecimento de segurança do BFF (P1) (✅)
**Contexto:** auditoria apontou `allow_origins=["*"]` e `FakeAuthProvider` por default como riscos
de produção. Fechados, mantendo dev/CI sem fricção.

**Entregue** ([security.py](services/api/src/charutei_api/security.py) + [app.py](services/api/src/charutei_api/app.py) + [auth.py](services/api/src/charutei_api/auth.py)):
- **CORS por env** (`CHARUTEI_CORS_ORIGINS` CSV) — **nunca `*`**; default localhost em dev, `[]` em
  produção (força config explícita).
- **Guard de produção**: `CHARUTEI_ENV=production` sem `SUPABASE_JWT_SECRET` → **fail-fast** no boot
  (recusa FakeAuthProvider, que aceitaria qualquer token). Validado ao vivo.
- **Rate limiting**: middleware de **janela deslizante em memória** por cliente (token ou IP);
  `/healthz` isento; `429` + `Retry-After`. Configurável (`CHARUTEI_RATE_LIMIT`/`_WINDOW_S`; `0`
  desabilita). 1ª camada — multi-réplica exige store compartilhado (Redis).
- `.env.example` documenta as novas variáveis.

**Testes/evals:** ruff ✓ · format ✓ · mypy ✓ · **pytest 108 passed, 12 skipped** (+10 segurança) ·
**7 gates PASS**. Cobre CORS (dev/env/prod), guard de produção (raise), rate limiter (janela,
disable) e **429 end-to-end** no BFF.

---

## S18 — Persistência durável (Postgres) no BFF (P0.2) (✅)
**Contexto:** auditoria apontou que o BFF era 100% in-memory — coleção/humidor **se perdiam no
restart** e não escalavam além de 1 processo. Postgres já existia em `packages/knowledge` mas não
estava ligado ao BFF.

**Entregue:**
- **`build_context`** ([context.py](services/api/src/charutei_api/context.py)) seleciona a
  persistência por env (espelha `build_providers`/`build_auth_provider`): `DATABASE_URL` presente →
  **`PostgresKnowledgeGraph` + `PostgresOltp`** (KG + OLTP duráveis, commit por operação); ausente →
  in-memory. Semeia+ingere os 410 SKUs **só no primeiro boot** (guard por KG vazio → restart é ~1s).
  Índices derivados (catálogo vetorial do reconhecimento + corpus RAG) seguem in-memory,
  reconstruídos do KG a cada boot. Normaliza o prefixo `postgresql+psycopg://` do `.env.example`.
- **Lifecycle** ([app.py](services/api/src/charutei_api/app.py), [main.py](services/api/src/charutei_api/main.py)):
  contexto montado no **lifespan** do FastAPI (não mais `asyncio.run` no import) — a conexão Postgres
  nasce no loop do uvicorn e é fechada no shutdown (`AppContext.aclose`). Handlers leem o contexto via
  dependência `get_ctx` (`app.state.ctx`), desacoplando criação do app da construção do contexto.
- Teste de integração `test_api_postgres.py` (skipif sem `CHARUTEI_TEST_DATABASE_URL`).

**Validação ao vivo (Postgres do compose):** 1º boot semeou **417 SKUs** no Postgres; adicionei item
à coleção → **restart do BFF** (2º boot ~1s) → **coleção sobreviveu** (cohiba-robustos qty 2) e
catálogo persistido. Teste durável passa com DSN `postgresql://` e `postgresql+psycopg://`.

**Testes/evals:** ruff ✓ · format ✓ · mypy ✓ · **pytest 98 passed, 12 skipped** (+1 integração
durável) · **7 gates PASS** (in-memory default inalterado).

**Limitação documentada (escala):** **uma conexão por processo** — concorrência alta exige pool +
checkout por request (refatora os repos de `packages/knowledge` → plan-gated). `idempotency_keys`
segue in-memory (dedupe some no restart). Suficiente para MVP/demo durável.

---

## S17 — Mockup demo-ready (BFF rico + UI do Assistente) (✅)
**Contexto:** validação do mockup apontou 3 lacunas P0 — o BFF servia só 32 charutos (seed) e
RAG vazio (perguntas gerais escalavam ao laço Opus sem fonte), e o web não expunha o `/ask`.

**Entregue:**
- **BFF** ([context.py](services/api/src/charutei_api/context.py)): no `build_context`, ingere o
  **catálogo completo** via `CigarIntelligence` (`parse_catalog_csv` + `CatalogIngestor`) → **417
  SKUs** no KG; e **indexa o corpus** `data/docs/cigar_docs.json` no `DocumentStore` (RAG ancorado).
  Ambos best-effort (guardados por `.exists()`; `CHARUTEI_DATA_DIR` sobrescreve o caminho). Deps
  `charutei-cigar-intelligence` no `api`; corpus copiado p/ `data/docs/`.
- **Web** ([apps/web](apps/web/)): `ask()` no `api.ts`; nova página **`/ask`** mostrando o **degrau
  da cascata** que resolveu (KG/RAG/Opus) + custo + citações, com perguntas-exemplo clicáveis. Link
  "Assistente" na nav; footer 117→410.

**Validação ao vivo (USE_FAKE_PROVIDERS):** catálogo **417 SKUs** · `/ask` "armazenar humidor" →
**tier 4 (RAG) ancorado** com 3 citações (antes: tier 5 "sem fonte") · `/ask` harmonização → tier 2
(KG). Web: `tsc --noEmit` ✓.

**Testes/evals:** ruff ✓ · mypy ✓ · **pytest 98 passed, 11 skipped** · **7 gates PASS** (sem regressão).

**Fronteiras restantes (P1):** prosa gerada é placeholder sem `ANTHROPIC_API_KEY` (KG dá respostas
reais); deploy (Vercel + BFF hospedado); match de label exato no KG (charuto com nome não-exato cai
no RAG). Mobile Expo segue dependente de simulador.

---

## Manutenção — tipos da S9 (Voyage/Gemini) resolvidos (✅)
Os 6 erros de mypy que surgiam **com o extra `providers` instalado** (SDKs Voyage/Gemini com
tipagem incompleta no boundary) foram eliminados sem `# type: ignore` (que `strict` +
`warn_unused_ignores` quebrariam no CI sem o extra):
- correção real nossa: `parts: list[dict]` → `list[dict[str, Any]]`; coerção explícita dos
  embeddings para `list[list[float]]`/`list[float]` (evita `no-any-return`);
- override de mypy `follow_imports = "skip"` para `voyageai.*`/`google.genai.*` (boundary de
  terceiros tratado como `Any`; inerte quando o extra não está instalado).
- Resultado: `uv run mypy packages services` limpo **com e sem** o extra `providers`.

## S11 — Auth real: SupabaseAuthProvider (JWT HS256) (✅)
**Entregue:**
- **`SupabaseAuthProvider.verify()`** ([auth.py](services/api/src/charutei_api/auth.py)): valida o
  access token do Supabase em **HS256** com o JWT secret do projeto (`pyjwt` lazy-import). Exige
  `sub`+`exp`, confere `aud` (default `authenticated`) e expiração; retorna `AuthUser(id=sub,
  email)` ou `None` (assinatura inválida/expirado/aud divergente/claim ausente).
- **`build_auth_provider()`**: liga o real por env (`SUPABASE_JWT_SECRET`, `SUPABASE_JWT_AUD`) —
  senão `FakeAuthProvider` (dev/CI). Espelha `build_providers`. `AppContext` passa a usá-lo.
- Dep `pyjwt>=2.8` no pacote `api`.

**Testes/evals:** ruff ✓ · mypy ✓ · **pytest 98 passed, 11 skipped** (+7 auth; `importorskip("jwt")`
mantém hermético) · **7 gates PASS**. Cobre token válido, vazio, assinatura inválida, expirado,
audience errada, `sub` ausente, e a seleção da fábrica por env.

**Próximas:** S12 (validar Expo em simulador) · ligar `AnthropicToolRunner` real em staging (chave) ·
resolver os 8 typings pré-existentes da S9.

---

## S16 — Multi-agêntico: laço ligado no Assistant (✅) — refatoração concluída
**Entregue:**
- **Assistant** ([assistant.py](services/agents/assistant/src/charutei_assistant/assistant.py)):
  `default_spec` agora com `allow_agentic_loop=True`. Quando habilitado, monta `CigarTools(kg,
  _DocStoreRetriever)` + `build_cigar_tools` e injeta o `tool_runner` na `Cascade` —
  `FakeToolRunner` em CI/dev, `AnthropicToolRunner(build_mcp_server(...))` com providers reais.
  `_DocStoreRetriever` adapta o `DocumentStore` ao Protocol `DocRetriever` (RAG → `rag_search`).
  O laço só dispara no degrau Opus gated (cache/KG/RAG inalterados).
- **BFF**: `Assistant` montado no `AppContext` (registry/governance compartilhados com o Supervisor),
  registrado como handler `assistant`; novo **`POST /ask`** despacha via
  `supervisor.dispatch(RequestKind.ASSISTANT_TEXT, q)`. `api` passa a depender de `charutei-assistant`.
- **Eval `agentic_loop_groundedness`** (7º gate): cenário forçado de escalada → laço ancora 100%
  das respostas (3/3) com citações + custo; registrado no CLI e no pytest dos gates.
- **CLAUDE.md** atualizado: stack de agentes reflete a realidade (Supervisor + tool runner
  `anthropic` + MCP in-process; LangGraph = swap de escala).

**Testes/evals:** ruff ✓ · mypy ✓ · **pytest 91 passed, 11 skipped** (+2 BFF `/ask`) ·
**7 gates PASS** (sem regressão: `cascade_efficiency` segue 100% sem Opus, $0.00018/msg).

**Resultado:** CHARUTEI agora é **multi-agêntico** (Supervisor + especialistas) com laço de tool-use
real (Opus + MCP) **gated no topo da cascata** — "LLM é o último recurso" preservado e provado por
teste de invariante (loop nunca roda em cache/KG/RAG) + gate de groundedness do laço.

**Próximas (fora desta refatoração):** S11 `SupabaseAuthProvider.verify()` (JWT) · S12 validar Expo ·
ligar `AnthropicToolRunner` real com chave em staging.

---

## S15 — Multi-agêntico: Supervisor + gating do laço (✅)
**Entregue:**
- **`AgentSpec.allow_agentic_loop`** (default `False`): gating por capability de quem pode usar o
  laço agêntico — só `assistant` ligará na S16.
- **`supervisor.py`**: `Supervisor` (roteador **determinístico, sem LLM**) + `RequestKind`
  (`BAND_IMAGE`/`ASSISTANT_TEXT`/`CATALOG_INGEST`). `route(kind)` resolve a capability no
  `AgentRegistry` e aplica o **kill-switch** (`GovernanceError` se desabilitada); `dispatch(kind,
  payload)` chama o handler do especialista. O tipo de payload desambigua o agente; a
  classificação fina de intenção continua em `router.classify` na cascata (sem duplicação).
- **Refactor do BFF**: `AppContext` monta um `Supervisor` e registra `band_recognition →
  band_agent.recognize`; `POST /bands/recognize` agora despacha via `ctx.supervisor.dispatch(
  RequestKind.BAND_IMAGE, ...)` — wiring centralizado, handlers desacoplados dos agentes.

**Testes/evals:** ruff ✓ · mypy ✓ · **pytest 88 passed, 11 skipped** (+6) · **6 gates PASS**
(sem regressão; BFF segue reconhecendo anilha via Supervisor).

**Próxima slice:** S16 — ligar o laço no Assistant (`build_cigar_tools` + `build_mcp_server`/
`FakeToolRunner` na `Cascade`, gated por `allow_agentic_loop`), `/ask` no BFF + eval
`agentic_loop_groundedness`, e atualizar o CLAUDE.md (LangGraph→tool runner Anthropic+MCP).

---

## S14 — Multi-agêntico: ferramentas MCP + runner real (✅)
**Entregue:**
- **`mcp_tools.py`**: `CigarTools` (fonte única, determinística, **sem LLM**) com 4 ferramentas
  read-only envolvendo KG/RAG — `kg_query`, `harmonize`, `compare`, `rag_search`; todas devolvem
  `ToolResult` **com citações**. `DocRetriever` (Protocol) evita o Orchestrator importar o pacote
  `assistant` (direção de dependência correta — RAG entra por injeção na S16).
- **`build_cigar_tools()`** → `list[AgentTool]` (caminho `FakeToolRunner`, CI) ·
  **`build_mcp_server()`** → servidor MCP in-process (FastMCP), mesma lógica exposta como tools MCP.
- **`AnthropicToolRunner`** (laço manual: controle de FinOps — soma `usage` por iteração + extrai
  citações de cada `tool_result`): Opus orquestra as tools via sessão MCP **in-memory** (sem rede,
  sem subprocess). `anthropic`/`mcp` lazy-import (extra `providers`). `opus-4.8` + thinking adaptive
  + effort high.
- Deps: `anthropic[mcp]>=0.40` + `mcp>=1.0` no extra `providers`.

**Verificação:** a **camada MCP é local** → testada sem chave (servidor sobe, lista 4 tools, executa
`call_tool` e devolve `ToolResult` serializado com citação). Só o loop Opus end-to-end exige chave
(`skipif` — padrão da S9). No CI sem o extra `providers`, o teste da camada MCP é pulado via
`importorskip("mcp")` — hermético.

**Testes/evals:** ruff ✓ · mypy ✓ (arquivos novos `agent_loop.py`/`mcp_tools.py`) ·
**pytest 82 passed, 11 skipped** (+6) · **6 gates PASS** (sem regressão).
**Nota:** com o extra `providers` instalado, o mypy expõe 8 erros **pré-existentes da S9**
(`providers.py` Voyage/Gemini) — mascarados no CI por `ignore_missing_imports`; fora do escopo da S14.

**Próxima slice:** S15 — `Supervisor` (roteador determinístico de agentes) + `AgentSpec.allow_agentic_loop`
+ refactor do `AppContext` para despachar via Supervisor.

---

## S13 — Multi-agêntico: fundação do laço agêntico (✅)
**Contexto:** início da refatoração para arquitetura multi-agêntica (Supervisor + especialistas,
**loop só no topo**), via tool runner do SDK `anthropic` + MCP — preservando "LLM é o último recurso".
Plano completo das slices S13–S16 aprovado.

**Entregue:**
- **`agent_loop.py`**: interface `ToolRunner` (Protocol) + `AgentTool` (ferramenta read-only
  determinística, sem LLM) + `AgentRunResult`/`ToolCallTrace`/`ToolResult` + `FakeToolRunner`
  (loop determinístico para CI: invoca cada ferramenta, agrega trechos, cita as fontes; tokens/custo
  reais por modelo). `build_tool_runner(use_fake)` simétrico a `build_providers` (real entra na S14).
- **`Cascade`**: `tool_runner`/`tools` opcionais (`None` ⇒ comportamento atual byte-a-byte). O loop
  roda **apenas no ramo de escalada Opus gated** de `_generate`; cada ferramenta vira `TraceRecord`
  filho (`tool:<name>`) sob o mesmo `trace_id`. Degraus 1–4 inalterados.
- Exports no `__init__`.

**Invariante de custo (testado):** o loop **nunca** é invocado quando cache/KG/RAG resolvem
(espião `_SpyToolRunner` ⇒ `calls==0` no degrau determinístico; `calls==1` só na escalada Opus).

**Testes/evals:** ruff ✓ · mypy ✓ (arquivos novos) · **pytest 76 passed, 10 skipped** (+4 testes) ·
**6 gates PASS** (sem regressão; loop não roda no dataset de eval, distribuição inalterada).

**Próxima slice:** S14 — `mcp_tools.py` (kg_query/rag_search/harmonize/compare envolvendo KG/RAG)
+ `AnthropicToolRunner` real (tool runner + MCP, `skipif` sem chave).

---

## S11w — Frontend web: demo para investidores (✅)
**Entregue:**
- **BFF**: CORS liberado; `GET /catalog` expõe todos os charutos do KG (label, brand, country,
  strength, pairings). `AppContext` agora carrega `kg: KnowledgeGraphRepo`.
- **`apps/web/`** — Next.js 15 + Tailwind, proxy `/api/**` → BFF:
  - **Scan** (landing): hero, 5 fixtures de demo, reconhecimento via `visual_text`, resultado com
    confiança, tier (SMALL/MEDIUM/LARGE), custo USD, candidatos ranqueados, botão "Adicionar ao Humidor".
  - **Humidor**: lista de coleção persistida na sessão BFF.
  - **Catálogo**: grid com filtro por país/intensidade, badges de pairings, pontos de intensidade.

**Para rodar localmente (demo):**
```bash
# Terminal 1 — BFF
uv run --extra serve --package charutei-api uvicorn charutei_api.main:app --port 8000

# Terminal 2 — Web
cd apps/web && npm run dev   # → http://localhost:3001
```

**Testes/evals:** ruff ✓ · **pytest 72 passed, 10 skipped** · **6 gates PASS** (sem regressão).

**Próxima slice:** S11 — `SupabaseAuthProvider.verify()` (JWT real) + S12 — validar Expo mobile.

---

## S10 — Embeddings reais no pgvector + eval ANN (✅)
**Entregue:**
- **`evals/embedding_ann_quality.py`**: gate `rank1_accuracy ≥ 0.90`. Semeia todos os charutos
  do KG curado em `InMemoryVectorRepository` via `FakeEmbeddingProvider` (BOW), depois verifica
  que ANN rank-1 de cada embedding é o próprio charuto. CI-safe (sem API key, sem Postgres).
  Registrado no CLI `python -m evals` e no pytest `tests/test_evals_gates.py`.
- **`scripts/seed_embeddings.py`**: materializa embeddings reais (Voyage `voyage-4-lite`) no
  pgvector para todos os nós `cigar` do KG Postgres. Idempotente (upsert por `kind+item_id`),
  batch de 50 textos, suporta `--dry-run`. Requer `VOYAGE_API_KEY` + `DATABASE_URL`.
- Mecânica: `kind="cigar_text"`, `item_id=cigar_node.id` (ex.: `cigar:cohiba-siglo-vi`).

**Para rodar com providers reais:**
```bash
DATABASE_URL=postgresql://charutei:charutei@localhost:5432/charutei \
VOYAGE_API_KEY=... \
uv run python scripts/seed_embeddings.py
```

**Testes/evals:** ruff ✓ · **pytest 72 passed, 10 skipped** · **6 gates PASS** (novo gate ANN).

**Próxima slice:** S11 — `SupabaseAuthProvider.verify()` (JWT real).

---

## S9 — Adaptadores reais: Anthropic + Voyage + Gemini (✅)
**Entregue:**
- **`AnthropicLLMProvider`**: usa `anthropic.AsyncAnthropic` (lazy import). Mapeia IDs internos
  (`haiku-4.5` / `sonnet-4.6` / `opus-4.8`) → IDs do SDK (`claude-haiku-4-5` / `claude-sonnet-4-6` /
  `claude-opus-4-8`). Custo calculado via `LLM_PRICING`.
- **`VoyageEmbeddingProvider`**: `voyageai.AsyncClient.embed()` (lazy import). Texto, `voyage-4-lite`.
- **`VoyageImageEmbeddingProvider`**: `voyageai.AsyncClient.multimodal_embed()` (lazy import).
  Multimodal, `voyage-multimodal-4`. Suporta base64, URL ou fallback para `visual_text`.
- **`GeminiVisionProvider`**: `google.genai.Client` (lazy import). Mapeia `gemini-3-flash` →
  `gemini-2.0-flash`. Prompt em português + inline_data para imagem (quando disponível).
- **`build_providers(use_fake=False)`** → `AnthropicLLMProvider + VoyageEmbeddingProvider + build_tracer()`.
- **`build_band_providers(use_fake=False)`** → `VoyageImageEmbeddingProvider + FakeOCRProvider + GeminiVisionProvider`.
- `NotImplementedError` removido de ambas as fábricas.
- **Testes de integração** (`services/orchestrator/tests/test_providers_integration.py`): 7 testes com
  `pytest.mark.skipif` quando chaves ausentes — compatível com CI sem chaves.

**Testes/evals:** ruff ✓ · mypy ✓ · **pytest 71 passed, 3 skipped** (sem regressão) · **5 gates PASS**.

**Próxima slice:** S10 — Materializar embeddings reais (Voyage → pgvector) + eval `embedding_ann_quality`.

---

## S8 — Cigar Intelligence: ingestão de catálogo de SKU (✅)
**Entregue:**
- Agente `services/agents/cigar_intelligence` (no workspace uv). **Sem LLM** — ingestão 100% determinística,
  alinhada ao princípio "LLM é o último recurso" (enriquecimento do KG por catálogo verificado, não por geração).
- **`catalog.py`**: parser CSV → `CatalogRecord` (Pydantic). Valida força (`mild/medium/medium-full/full`);
  campos incertos (ex.: fábrica) ficam `null` — **nunca se inventa dado**.
- **`ingest.py`** `CatalogIngestor`: dedup por SKU canônico → **detecção de conflito de fato de alta
  confiança → fila HITL** (nunca sobrescreve em silêncio; `apply_conflicts=True` força) → upsert idempotente
  de nós/arestas → harmonização por **regra de força** (não por SKU) → evento `sku.detectado` (outbox).
- **`review.py`**: `ReviewQueue` (Protocol) + `InMemoryReviewQueue` para conflitos (HITL).
- **Dados**: `data/catalog/cigars.csv` — **109 SKUs reais verificados** (Cuba 50 · Nicarágua 26 · Rep.
  Dominicana 23 · Honduras 10), dentro da meta de 100–300 da S1. Campos incertos (ex.: fábrica em todos;
  vitola de Plasencia Alma Fuerte / LFD Andalusian Bull / LFD Chisel) ficam `null`.
- **`scripts/ingest_catalog.py`**: ingestão in-memory (semeado) + `--postgres`.

**Reconciliação com o seed:** 24 SKUs do catálogo coincidem com o seed curado (S1) e **enriquecem** nós
existentes; 3 divergências de força (Montecristo No. 4, Partagás Lusitanias, Hoyo Epicure No. 2) caíram na
fila HITL e foram **alinhadas ao seed curado** (fonte de verdade) — força é avaliação debatível, não se
inventa divergência. Resultado: 0 conflitos residuais.

**Testes/evals:** ruff ✓ · format ✓ · mypy (5 arquivos novos) ✓ · **pytest 70 passed, 3 skipped** (repo
inteiro) · **4 gates PASS** (cascata/band/groundedness/custo, sem regressão).

**Ingestão (in-memory):** `32 (seed) → 117 (catálogo)` · `created=85, updated=24, unchanged=0, conflicts=0` ·
HITL: 0 itens.

**Ingestão (Postgres real):** migrations `0002_events (head)` aplicadas · `32 (seed) → 117` ·
`created=85, updated=24, unchanged=0, conflicts=0` · 117 nós `cigar`, 45 marcas, 27 vitolas, 267 arestas
`pairs_with`. Testes de integração Postgres: 3 passed.

**Eval `catalog_coverage` (gate S8):** `catalog_coverage=1.0 · required_edges_pct=1.0 · pairing_coverage=1.0 · vitola_null_ok=1.0`
— registrado em `evals/catalog_coverage.py`, exposto no CLI (`python -m evals catalog_coverage`) e no pytest
(`tests/test_evals_gates.py`).

**Testes/evals finais (S8 completa):** ruff ✓ · format ✓ · mypy ✓ · **pytest 71 passed, 3 skipped** · **5 gates PASS**.

## S7 — Evals & CI (✅) — MVP COMPLETO
**Entregue:**
- **4 gates do Anexo C** rodando como **eval CLI** (`python -m evals`, sai !=0 ao reprovar) **e como pytest**
  (`tests/test_evals_gates.py`) — regressão de qualidade/custo falha o build por dois caminhos.
- Teste da semântica de saída (`tests/test_evals_cli.py`): gate reprovado → exit code ≠ 0.
- **`scripts/verify.sh`**: Definition of Done local (lint + format + tipos + testes + 4 gates).
- **`docs/ACCEPTANCE.md`**: os 6 critérios de aceite mapeados a evidências reproduzíveis.
- README com runbook completo (bootstrap → docker compose → migrações → BFF → app → evals).

**Testes/evals:** ruff ✓ · format ✓ · mypy (44 arquivos) ✓ · **pytest 61 passed, 3 skipped** · **4 gates PASS**.

**Resultado do MVP (todos os critérios mensuráveis):** reconhecimento 90% sem visão; assistente 100% sem
Opus com groundedness 100%; custo **$0.00018/msg** (limite $0,005); CI com lint+testes+evals+gitleaks;
`docker compose up` sobe Postgres+Redis. Fronteiras honestas (Langfuse real, providers reais, simulador
mobile, seed 100–300) documentadas em `docs/ACCEPTANCE.md`.

## S6 — Mobile (Expo) + BFF (✅)
**Entregue:**
- **BFF FastAPI** (`services/api`): `POST /bands/recognize`, `POST /collection/items` (com **Idempotency-Key**),
  `GET /collection`, `GET /healthz`. Auth via `Authorization: Bearer`. Escritas publicam eventos (outbox).
- **Auth atrás de interface** (`AuthProvider`): `FakeAuthProvider` (dev/CI, qualquer token) + stub
  `SupabaseAuthProvider` (JWT real ligado quando houver chaves). Padrão do projeto — sem chave no MVP.
- **AppContext**: monta band agent (catálogo do KG) + OLTP + outbox + auth uma vez; troca p/ Postgres/Supabase
  é injeção, sem mudar handlers. Entrypoint `charutei_api.main:app` p/ `uvicorn`.
- **App Expo** (`apps/mobile`): fluxo login → captura (expo-camera) → reconhecimento → adicionar à coleção;
  cliente da API (`src/api.ts`). **Entregue como código — não executado em simulador neste ambiente.**

**Testes/evals:** ruff ✓ · format ✓ · mypy (43 arquivos) ✓ · **pytest 55 passed, 3 skipped** · 4 evals PASS.

**Validação real:** BFF subiu via `uvicorn` e respondeu HTTP de verdade — `/bands/recognize` reconheceu
`cigar:partagas-serie-d-no-4` (conf. 1.0, tier 3, sem visão), coleção adicionou/listou, sem auth → 401.

**Decisões/registros:** Supabase Auth real e captura via react-native-vision-camera (dev build) ficam como
ligação por env/produção; o app mobile precisa de simulador iOS/Android para execução (fora deste ambiente).

## S5 — Assistant + RAG mínimo (✅)
**Entregue:**
- **`services/agents/assistant`**: orquestra pela cascata cache → **KG (fato)** → **RAG (Sonnet)** →
  Opus (gated), sempre **com citações**.
- **`KGAssistantResolver`** (degrau 2): detecta o charuto citado (via `nodes_by_type`) e responde
  harmonização/ficha pelo grafo, sem LLM, com citações de nós do KG.
- **RAG mínimo** (`rag.py`): `DocumentStore` (corpus indexado) + `RagGenerator` — recuperação híbrida →
  **rerank** lexical → **compressão extrativa** → geração com citações dos documentos.
- **Hook `Generator`** na cascata: a geração virou plugável (RAG injeta contexto/citações sem mudar o motor).
- Corpus `evals/datasets/cigar_docs.json` (conhecimento geral real); `nodes_by_type` adicionado ao KG
  (interface + in-memory + Postgres).
- **Evals novos** no CI: `assistant_groundedness` e `cost_per_interaction` (os 4 gates do Anexo C ativos).

**Testes/evals:** ruff ✓ · format ✓ · mypy (38 arquivos) ✓ · **pytest 50 passed, 3 skipped** · **4 evals PASS**.

**Métricas (11 consultas):** **100% sem Opus** · custo médio **$0.00018/msg** (limite $0,005 ✓) ·
**groundedness 100%** (11/11 ancoradas) · distribuição: KG 64% · RAG/Sonnet 36%.

**Decisão de design:** a confiança que governa o gating de Opus reflete **se a resposta está ancorada**
(achou fonte → confiança alta, sem Opus), não o score bruto de retrieval — Opus fica como último recurso
quando o RAG não encontra base.

## S4 — Eventos (✅)
**Entregue:**
- **`packages/events`**: `Event`/`Delivery`/`DeadLetter` + `EventType` (anilha.cadastrada, imagem.enviada,
  sku.detectado, colecao.alterada). Interfaces `EventBus`/`Outbox`/`ProcessedRegistry` + `RetryPolicy`.
- **In-memory**: `InMemoryEventBus` (poll/ack/nack → retry/backoff → **DLQ**), `InMemoryOutbox`
  (publicação idempotente), `InMemoryProcessedRegistry` (dedupe por `event_id`).
- **Durável (Postgres)**: `PostgresOutbox`/`PostgresProcessedRegistry` + tabelas `outbox`/`processed_events`
  (migração **0002_events**), com `ON CONFLICT` (idempotência) e publicação transacional.
- **Embedding Worker** (`services/workers/embedding`): consome `imagem.enviada`/`sku.detectado`, embeda via
  provider (interface, sem SDK direto), **cache por hash de conteúdo** (não re-embeda), **idempotente**
  (marca antes do ack), falha → **retry/DLQ**. Materializa no `VectorRepository`.

**Testes/evals:** ruff ✓ · format ✓ · mypy (34 arquivos) ✓ · **pytest 46 passed, 3 skipped** ·
integração Postgres (KG/vector/outbox) **3 testes** passam no DB real · evals PASS.

**Validação real:** migração 0002 aplicada no Postgres do OrbStack (tabelas `outbox`/`processed_events`);
teste de integração do outbox passou contra o banco.

**Fora do MVP (registrado):** pgmq/Redis Streams e Kafka são o swap de produção do `EventBus` (mesma
interface); **Batch API (-50%)** entra no job offline de catálogo (Cigar Intelligence) — fora do MVP.

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
Instrumentadas via `Tracer` (Langfuse na produção). Assistente no dataset de eval: **100% sem Opus**,
custo médio **$0.00018/msg**, **groundedness 100%**, 64% no degrau determinístico (KG) e 36% RAG/Sonnet.
Band Recognition: acurácia 100%, 90% sem visão.

## Expansão do catálogo — C2GO OffCuba (2026-06-09)
**Fonte:** PDF "Charutos 2GO OffCuba 05.05.26" — ~700 SKUs de charutos premium não-cubanos.

**Entregue:**
- `scripts/parse_c2go_catalog.py`: parser com mapeamentos de marca → país e keywords de capa → intensidade.
  Dedup idempotente por slug contra entradas existentes.
- `data/catalog/cigars.csv`: **+301 novas entradas** · total **410 SKUs**.
  Marcas cobertas: A. Fuente, AJ Fernandez, Alec Bradley, Avo, Brick House, Buena Vista, CAO, Davidoff,
  Diamond Crown, Don Diego, Don Emmanuel, Drew Estate, EP Carrillo, Espinosa, Flor de Copan, Flor de Oliva,
  Fratello, Gurkha, Joya de Nicaragua, La Aurora, Luis Martinez, Macanudo, My Father, Mombacho, Montosa,
  NUB, Oliva, Parcero Brasil, Perla del Mar, Quorum, Reposado, Dunbarton T&T (Steve Saka), Vegafina.

**Ingestão (in-memory):** `32 (seed) → 417` · `created=385, updated=25, unchanged=0, conflicts=0` · HITL: 0.

**Gates (sem regressão):** 6 gates PASS · pytest 72 passed, 10 skipped.
