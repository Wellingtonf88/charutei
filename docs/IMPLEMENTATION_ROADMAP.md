# IMPLEMENTATION_ROADMAP — Charutei Consumer Intelligence Platform

Continua a numeração de slices existente (`docs/PROGRESS.md` termina em S21 + mobile F3). Cada fase
abaixo é uma sequência de slices, seguindo a Definition of Done do CLAUDE.md (código + testes verdes +
eval relevante + conventional commit + PROGRESS.md atualizado, pausa e reporte ≤10 linhas ao final).
Nenhuma fase começa sem a anterior fechada e testada.

## PHASE 0 — Audit (✅ concluída nesta sessão)
`PROJECT_UPGRADE_AUDIT.md`, `TARGET_ARCHITECTURE.md`, este roadmap.

## PHASE 1 — Foundations (débito técnico bloqueante)
Pré-requisito de tudo que segue, sem valor de produto visível isoladamente:
- ✅ Idempotency-key store de `/collection/items` → Postgres (mesmo padrão de `processed_events`).
  Validado: pytest (117 passed c/ Postgres real), migração `0004_idempotency` aplicada em Postgres
  vivo, smoke test HTTP confirmando que a mesma chave não duplica item mesmo após restart do processo.
- ✅ `app.json` config por ambiente — trocado `extra.apiBaseUrl` hardcoded por
  `EXPO_PUBLIC_API_BASE_URL` (`.env`, padrão Expo, nunca commitado). Validado: `tsc --noEmit` e
  `expo config` limpos.
- ✅ **Pipeline de eventos** (achado durante a Fase 1, corrigido na mesma fase): outbox/idempotência
  Postgres wired em `context.py`, `CatalogIngestor` agora emite `sku.detectado`, e o
  `EmbeddingWorker` roda in-process no BFF via loop de fundo (`pump_events`, lifespan do FastAPI)
  — decisão de desenho registrada no audit (worker separado só quando houver 2ª réplica).
  Validado ao vivo contra Postgres real: 386 eventos presos drenados em 8s, shutdown gracioso.
- Pendente: dimensão fixa + índice HNSW em `embeddings` — **bloqueado por decisão externa**: a
  dimensão real do Voyage-4 (texto vs. multimodal) não pode ser fabricada; requer ADR após
  confirmar contra a API real do provedor (hoje só `Fake*` com `EMBED_DIM=64`).
- Pendente: auth real Supabase no mobile (backend já valida JWT real; app ainda usa token colado
  manualmente). Adiado nesta sessão — é uma feature de UI nova (fluxo de login) que não pode ser
  validada sem simulador/device, ao contrário dos itens acima que foram todos verificados.

## PHASE 2 — Experience Engine (✅ concluída nesta sessão)
- ✅ Multi-collection: `OltpRepository.list_collections`, `POST/GET /collections`,
  `POST /collection/items` aceita `collection_id` opcional (valida propriedade, 404 se não é do
  usuário). Zero migration — `collections` já suportava N por usuário desde a Fase 1 (S1); a
  limitação era só na API. 100% retrocompatível (mobile não muda).
- ✅ `EventType`s novos: `colecao.criada`, `degustacao.registrada` (`POST /tasting` não emitia
  nenhum evento antes desta fase).
- ✅ `docs/DATA_MODEL.md` com o schema exato e a decisão de escopo.
- **Adiado, com motivo registrado em `docs/DATA_MODEL.md`**: colunas `structured_attrs`/
  `ai_confidence`/`ai_source` em `tasting_notes` (schema sem leitor/escritor — não existe agente de
  extração ainda; entra junto com ele na Fase 5) e renomear `tasting_notes`→`EXPERIENCE` (extensão,
  não reescrita).
- Validado: pytest (125 passed contra Postgres real, era 118 ao fim da Fase 1) · 7 evals PASS ·
  smoke HTTP ao vivo confirmando isolamento entre usuários (bob → 404 na collection da alice).

## PHASE 3 — Consumer Identity (Km de Fumaça / Passaporte)
`packages/scoring` (determinístico, configurável, sem LLM) + tabela `user_scores` + job batch.
Move gamificação do client (`insights.ts`) para o backend — client passa a ler `GET /profile/score`
em vez de calcular localmente. Reformular apresentação de badges/nível para tom "passaporte de
experiências" (menos barra de XP, mais dossiê) — trabalho de design, não de dados.

## PHASE 4 — Location Intelligence
`LocationRepo` + `GeocodingProvider`/`MapsProvider`/`PlacesProvider` (Protocol + Fake, sem vendor
escolhido ainda — ADR dedicado no início da fase). Tabelas `establishments`, `product_availability`,
`user_locations` (opt-in). Endpoint "onde encontro X perto de mim" como primeiro caso de uso completo
(candidate generation → filtro de distância → filtro de disponibilidade → ranking).

## PHASE 5 — AI/RAG (separação de corpora)
Separar Knowledge Base / Community Knowledge (User Data permanece fora do RAG, só SQL/KG). Community
Knowledge só entra depois de ter volume real de experiências (depende da Phase 2/3 terem rodado em
produção por um tempo).

## PHASE 6 — Recommendation Engine
`RequestKind.RECOMMEND` novo no Supervisor. Candidate generation por KG+histórico → ranking
determinístico configurável → re-rank Sonnet opcional. Bloqueado por `ANALYTICS_EVENT`s de
view/search/save (parte da Phase 2, mas o consumo desses eventos para recomendação é desta fase).

## PHASE 7 — Community Intelligence
Agente de interpretação de tendências/percepção — só depois de haver volume de experiências e eventos
suficiente para ter o que interpretar (não implementar antes por falta de dado real).

## PHASE 8 — Monetization
`SPONSOR`/`CAMPAIGN`/`SPONSORED_CONTENT`, sempre marcado explicitamente como não-orgânico na resposta.

## PHASE 9 — Optimization
Revisão de custo/latência/cache com dado real de produção (não fake providers), tuning de thresholds de
Opus-gating e cache semântico com base em métricas reais do Langfuse.

## Critério de entrada em cada fase
Testes verdes da fase anterior + evals relevantes passando + `docs/PROGRESS.md` atualizado. Nenhuma
fase é "big bang" — cada uma é decomposta em slices menores no momento de execução, seguindo o padrão
S0–S21 já estabelecido no projeto.

## Próximo passo imediato
Iniciar **Phase 1** (débito técnico bloqueante) — é pré-requisito técnico de todas as fases seguintes e
não depende de nenhuma decisão de produto/negócio pendente.
