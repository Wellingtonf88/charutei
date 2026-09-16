# PROJECT_UPGRADE_AUDIT — Charutei → Consumer Intelligence Platform

**Data:** 2026-09-16 · **Branch:** `feat/production-hardening` · **Autor:** auditoria técnica (Claude Code)

Este documento é o degrau 0 (obrigatório) antes de qualquer mudança de código para o upgrade
"AI-First Consumer Intelligence Platform". Nada aqui foi inferido sem leitura direta do código —
dois agentes de exploração leram backend e mobile ponta a ponta; os achados abaixo citam arquivo/linha.

## 1. Arquitetura atual

Modular monolith fiel ao CLAUDE.md, sem desvios materiais:

- **Supervisor determinístico** (`services/orchestrator/src/charutei_orchestrator/supervisor.py`) —
  roteia por `RequestKind` (BAND_IMAGE, ASSISTANT_TEXT, CATALOG_INGEST) para capabilities registradas,
  aplica kill-switch via `Governance`. Zero LLM neste componente.
- **Cascade** (`cascade.py`) — motor de 5 degraus: cache exato/semântico → KG/SQL determinístico →
  geração Sonnet → escalonamento Opus *gated* por confiança + autorização. Tracing por etapa.
- **Laço agêntico** roda **só** dentro do degrau Opus (`agent_loop.py` + `mcp_tools.py`), com ferramentas
  read-only (KG/RAG) via MCP in-process. `FakeToolRunner` (CI) e `AnthropicToolRunner` (real) coexistem
  atrás de `build_tool_runner()`, chaveado por `USE_FAKE_PROVIDERS`.
- **Router** (`router.py`) — classificação de intenção por regex, sem LLM.

Conclusão: a arquitetura descrita no CLAUDE.md **não é aspiracional — já está implementada e testada**.

## 2. Stack

Backend: Python 3.12, FastAPI (single-file router em `services/api/src/charutei_api/app.py`), uv workspace.
Mobile: Expo (~54) + expo-router (~6) + React 19 + React Native 0.81. Web: Next.js 15 (demo/investidor).
Dados: Postgres 16 + pgvector, Redis (cache backend). Auth: Supabase JWT (HS256) real no backend;
mobile ainda usa `FakeAuthProvider`-compatível (login por token, sem SDK Supabase no app).
Modelos: Anthropic (Haiku/Sonnet/Opus), Voyage (embeddings + multimodal), Gemini Flash (visão) — todos
atrás de `Protocol` + `Fake*`, chaveados por `USE_FAKE_PROVIDERS`. Observabilidade: Langfuse self-host real.
CI: ruff + mypy + pytest + evals + gitleaks + cobertura ≥85%.

## 3. Estrutura do repositório

```
apps/{mobile,web}                 clientes (mobile = produto real; web = demo)
services/{api,orchestrator,agents/*,workers/embedding}
packages/{knowledge,cache,contracts,events}
evals/  infra/  docs/  scripts/  data/
```
`packages/knowledge` concentra todo acesso a dados atrás de `KnowledgeGraphRepo` / `VectorRepository` /
`OltpRepository`, com impl in-memory e Postgres testadas contra a mesma interface — exatamente o padrão
que o upgrade deve seguir para novos domínios (location, recommendation, etc).

## 4. Banco de dados — inventário completo (não recriar)

**OLTP:** `users`, `bands` (log de reconhecimento), `collections` (1 humidor/usuário, id hardcoded
`col:{user_id}` — sem multi-humidor), `collection_items` (com `created_at` para aging), `tasting_notes`
(rating, flavors[], occasion, note).

**KG relacional:** `kg_nodes` (tipos: BRAND, FACTORY, VITOLA, STRENGTH, COUNTRY, CIGAR, PAIRING),
`kg_edges` (rels: MADE_BY, PRODUCED_AT, HAS_VITOLA, HAS_STRENGTH, FROM_COUNTRY, PAIRS_WITH), `kg_version`
(invalida cache por bump de versão).

**Vetor:** `embeddings(kind, item_id, embedding, metadata)` — kinds observados: `band`, `cigar_text`.
Sem dimensão fixa ainda; índice HNSW não criado (aguarda consolidar dimensão).

**Eventos:** `outbox` (transactional outbox) + `processed_events` (idempotência). Só 4 `EventType`:
`anilha.cadastrada`, `imagem.enviada`, `sku.detectado`, `colecao.alterada` — nenhum evento de tasting,
gamificação ou social.

**Confirmado: nenhum conceito de localização/geo/estabelecimento/disponibilidade existe.** Nenhuma
lat/lng, endereço, loja, inventário por local ou check-in. Área 100% greenfield.

**Confirmado: gamificação/perfil/nível/badge (F3) é 100% client-side.** `apps/mobile/src/features/insights.ts`
calcula tudo a partir de dados já buscados via `/tasting` — zero persistência de servidor, zero API.
Qualquer leaderboard, consistência cross-device ou anti-fraude exige trabalho novo, não reuso.

## 5. APIs (BFF — `services/api`)

`GET /healthz` (sem auth) · `GET /catalog` (sem auth, projeta KG) · `POST /bands/recognize` (auth) ·
`POST /ask` (auth, dispara cascade) · `POST/GET /tasting` (auth) · `POST /collection/items` (auth,
idempotente via header, **mas store de idempotência é `set` em memória — não sobrevive a restart/réplica**)
· `GET /collection` (auth). CORS por env, rate limit sliding-window, guard de produção exige
`SUPABASE_JWT_SECRET`.

## 6. Frontend (mobile — produto real)

5 tabs: Identificar (câmera/visão), Sommelier (Q&A single-turn, não é thread persistida), Humidor
(coleção + aging), Descobrir (catálogo/filtros), Perfil (paladar/nível/badges/share). Detalhe do charuto
com formulário de tasting notes. Stack: TanStack React Query para server state (sem Redux/Zustand);
Context só para auth; `src/store/aging.ts` não é um store genérico, é um helper de lembrete local.

**Design system já existe** (`theme.ts` + `src/ui/index.tsx`, tokens centralizados, todas as telas
compõem só de primitivos) — mas a paleta atual é **charcoal/tobacco + dourado** ("clube de charutos à
noite"), não navy. Re-tema é edição pontual em `theme.ts`, não retrabalho de telas.

**Gamificação (F3)** é visualmente contida (sem confete/toast/XP bar ruidoso), mas ainda usa tropos
convencionais (barra de progresso de nível, grade de badges com emoji) — candidata a refinamento editorial,
não a reconstrução.

`apps/web` é um demo funcional para investidores (Next.js), **duplica** o client de API do mobile sem
compartilhar design tokens — dívida de duplicação a registrar, não a resolver neste momento.

## 7. Backend — estado por agente

- **assistant**: LLM-based (Sonnet default, Opus gated), resolver determinístico do KG antes de gerar.
- **band_recognition**: híbrido — embedding+ANN → OCR → visão (Gemini, gated) → `needs_human`. Atinge
  90% sem visão no eval atual (fake providers).
- **cigar_intelligence**: 100% determinístico, offline/batch, HITL via `ReviewQueue` antes de sobrescrever
  fatos conflitantes. Harmonização é tabela fixa por força (`_STRENGTH_PAIRINGS`), não por SKU.

## 8–9. IA/ML atual

Cascata + agentes acima são a totalidade da IA/ML do produto hoje. Não há recommendation engine,
não há candidate generation/ranking, não há event tracking de produto (view/click/dwell), não há
embeddings de experiência/avaliação (só de anilha e texto de catálogo).

## 10. Estado das funcionalidades (per slice, confirmado por `git log` + `docs/PROGRESS.md`)

S0–S21 (fundação → cascata → band recognition → eventos → assistant/RAG → mobile/BFF → evals/CI →
Supabase auth real → adaptadores reais → persistência Postgres → segurança/CORS/rate-limit →
deploy artifacts) + mobile F0–F3 (fundação → câmera/visão → engajamento → tasting/aging duráveis →
perfil/gamificação/compartilhamento) — **todas concluídas e testadas**. `pytest`: 111 passed, 12 skipped
(skips = testes de integração Postgres sem banco vivo neste ambiente). `ruff`: limpo. `mypy`: 2 erros,
ambos em `scripts/langfuse_demo.py` (script de demo, não biblioteca).

## 11. Débitos técnicos identificados

1. ~~Idempotency-key store de `/collection/items` é em memória — não durável, não multi-réplica.~~
   **Corrigido na Fase 1** (`idempotency_keys` durável em Postgres, ver `IMPLEMENTATION_ROADMAP.md`).
1b. ~~**Achado durante a Fase 1**: `context.py` montava `outbox=InMemoryOutbox()` incondicionalmente
   (mesmo com Postgres ligado); `publish_pending()` nunca era chamado em produção;
   `CatalogIngestor(kg)` não recebia `outbox`, então `sku.detectado` nunca era emitido;
   `docker-compose.prod.yml` não implanta o `EmbeddingWorker`. O pipeline de eventos não era
   funcional ponta a ponta.~~ **Corrigido na Fase 1**: `PostgresOutbox`/`PostgresProcessedRegistry`
   agora são usados quando `DATABASE_URL` está setado; `CatalogIngestor` recebe `outbox`; e como
   só o BFF é implantado hoje, o `EmbeddingWorker` roda **dentro do próprio processo do BFF**
   (`services/api/src/charutei_api/context.py::pump_events`, chamado por um loop de fundo no
   lifespan do FastAPI a cada `CHARUTEI_EVENT_PUMP_INTERVAL_S` segundos — default 5s). Validado
   ao vivo: 386 eventos `sku.detectado` presos no outbox (de um teste de integração anterior)
   foram drenados em 8s por um servidor real contra Postgres, sem erros, com shutdown gracioso.
   **Decisão registrada**: rodar o worker in-process (não um serviço separado) é consistente com
   "modular monolith" e com a topologia de deploy atual (um único container); se/quando o BFF
   escalar para múltiplas réplicas, isso processará eventos em duplicidade sem problema
   (idempotência via `ProcessedRegistry`), mas desperdiça trabalho — nesse ponto o worker deve
   virar um processo/serviço próprio consumindo de um `EventBus` compartilhado (Redis
   Streams/pgmq, já previsto no CLAUDE.md como swap de escala). Documentado, não implementado
   agora (não há 2ª réplica hoje).
2. Gamificação sem backend — sem consistência cross-device, sem defesa contra manipulação client-side.
3. Uma única collection ("humidor") por usuário, id hardcoded — sem suporte a múltiplas listas.
4. `embeddings` sem dimensão fixa / sem índice HNSW — ANN não indexado em escala.
5. `@react-native-async-storage/async-storage` presente no mobile mas não usado em lugar nenhum.
6. ~~`app.json` do mobile aponta IP LAN hardcoded — não é config por ambiente.~~ **Corrigido na
   Fase 1** (`EXPO_PUBLIC_API_BASE_URL`).
7. Auth do mobile ainda não fala com Supabase de verdade (client usa token opaco; backend já valida JWT
   real — a lacuna é só do lado do app).
8. `apps/web` duplica o client de API sem compartilhar tokens de design com o mobile.
9. Cobertura de eventos é só banda/catálogo — nenhum evento de tasting, coleção (além de um tipo genérico),
   social ou de produto (view/click/save) existe para alimentar recomendação futura.
10. **Achado durante a Fase 1**: `vector_repo` (embeddings de `cigar_text`/`band`) continua
    `InMemoryVectorRepository` mesmo em modo Postgres — agora que o worker efetivamente materializa
    embeddings (item 1b corrigido), eles são perdidos a cada restart do BFF. Não bloqueia a Fase 1
    (o gargalo corrigido era "nunca materializa", não "materializa mas não persiste").
    **Investigado, não é uma troca de uma linha**: a mesma instância de `vector_repo` serve dois
    usos com ciclos de vida diferentes — (a) o catálogo de banda (`BAND_KIND`, via
    `build_band_catalog`) é **deliberadamente** reconstruído do zero a cada boot (documentado em
    `context.py`: "não são estado durável, são cache de recuperação") e roda **incondicionalmente**,
    fora do guard `if not kg.nodes_by_type(CIGAR)`; (b) os embeddings `cigar_text` do worker
    (`CIGAR_TEXT_KIND`) são de fato event-driven e só regenerados quando `sku.detectado` é reemitido
    (ou seja, só no primeiro boot com KG vazio, em modo durável). Trocar ingenuamente `vector_repo`
    por `PostgresVectorRepository` faria (a) reprocessar ~410 chamadas reais ao provider de imagem
    a cada restart do BFF (custo/latência real com `USE_FAKE_PROVIDERS=false`), contradizendo o
    design documentado. Fix correto: dois repositórios (BAND_KIND in-memory sempre; CIGAR_TEXT_KIND
    Postgres quando durável) — vira slice própria, não uma correção pontual.

## 12. Riscos

- **Escopo do prompt mestre vs. realidade do repo**: o prompt pede uma plataforma completa de Consumer
  Intelligence com Location Intelligence, Recommendation Engine, Monetização e B2B — isso é várias
  iniciativas de meses, não um "upgrade" de uma sessão. Tratar tudo como um único slice monolítico violaria
  o próprio princípio do projeto (`Definition of Done` por slice, testável, documentado).
- **Duplicar o que já existe**: KG, cascata, agentes, evals e design system já cobrem boa parte do que o
  prompt mestre pede sob nomes diferentes (ex.: "Consumer Graph" ≈ `kg_nodes/kg_edges` + OLTP hoje
  desconectados — o gap real é *ligar* tasting/collection ao KG, não recriar um grafo).
- **Gamificação server-side e Location Intelligence** tocam autenticação, privacidade de localização e
  consistência de dados — exigem migrations e ADRs, não apenas código de app.

## 13. Componentes reutilizáveis (não recriar)

`Supervisor`/`Cascade`/`Governance`/`Registry`, `KnowledgeGraphRepo`/`VectorRepository`/`OltpRepository` +
impls, `packages/events` (outbox/idempotência/retry/DLQ), `packages/cache` (exato+semântico, invalidação
por versão do KG), `packages/contracts`, design system mobile (`theme.ts` + `src/ui`), toda a infra de
evals/CI, auth backend (Supabase JWT real), band recognition, assistant+RAG.

## 14. Componentes que precisam de refatoração (não substituição)

- `/collection/items` idempotency store → mover para Postgres (mesmo padrão de `processed_events`).
- Modelo de `collections` → suportar múltiplas listas sem quebrar o humidor único existente.
- Gamificação → extrair `insights.ts` (lógica já reusável) para um serviço de score no backend.
- `EventType` → expandir cobrindo tasting/coleção/social/produto sem quebrar consumidores atuais do worker.

## 15. Lacunas frente à arquitetura-alvo (ver `TARGET_ARCHITECTURE.md`)

Location Intelligence (100% greenfield), Recommendation Engine (candidate/ranking/re-rank — não existe),
Event Tracking de produto (view/click/save/dwell — não existe), Reputação/Km de Fumaça server-side (não
existe), Monetização/Sponsored (não existe), B2B/Brand Intelligence (não existe), auth real no mobile
(gap pontual), RAG separado em Knowledge/User/Community (hoje só há um corpus de conhecimento geral).
