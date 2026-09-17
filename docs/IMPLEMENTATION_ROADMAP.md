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

## PHASE 3 — Consumer Identity (Km de Fumaça / Passaporte) (✅ concluída nesta sessão)
- ✅ `packages/scoring` (puro, sem I/O, sem LLM): `compute_experience_score`,
  `compute_knowledge_score`, `compute_consumer_status`, `compute_streak`, `compute_badges` —
  fórmula considera diversidade (países/marcas) e documentação real (nota escrita), não só
  quantidade bruta ("requisito explícito do prompt mestre").
- ✅ `GET /profile`: substitui o cálculo 100% client-side por agregação server-side sobre
  `tasting_notes` + `collections` (todas, Fase 2) + KG — fecha o débito do audit §11.2
  ("gamificação sem backend, sem consistência cross-device, sem defesa contra manipulação").
- ✅ Mobile: `profile.tsx` troca `insights.ts` local por `useProfile()`; `insights.ts` perde as
  funções agora redundantes, mantém só `shareSummary`.
- **Adiado, com motivo em `docs/DATA_MODEL.md`**: `REPUTATION_SCORE`/`INFLUENCE_SCORE` (sem dado
  social — Fase 7) e tabela `user_scores`+job (calculado sob demanda por ora, barato na escala
  atual).
- Validado: pytest (136 passed contra Postgres real, era 125 ao fim da Fase 2) · 7 evals PASS ·
  `tsc --noEmit`/`expo config` limpos · smoke HTTP ao vivo confirmando a fórmula exata (score,
  status e progresso calculados à mão bateram com a resposta da API) e isolamento entre usuários.
- **Fora de escopo (registrado, não feito)**: redesenho visual da tela de perfil para tom
  "passaporte" (menos barra de progresso, mais dossiê) — trabalho de design, não de dados; o JSX
  desta fase só trocou a fonte do dado.

## PHASE 4 — Location Intelligence (✅ primeiro slice concluído nesta sessão)
Correção de rota registrada: eu disse antes que essa fase "precisava de decisão de vendor pra
planejar" — errado. `GeocodingProvider` como Protocol+Fake (mesmo padrão de `LLMProvider`) não
precisa saber o vendor pra existir, só pra ligar o adaptador real depois.

- ✅ `LocationRepo` (novo Protocol em `packages/knowledge`) + tabelas `establishments`,
  `product_availability` — migration `0005_location`, primeira desde a Fase 1.
- ✅ Novo pacote `packages/location`: `haversine_km`+`find_nearby` (candidate generation → filtro
  de distância → exclui `unavailable` → ranking por confiabilidade+distância) + `GeocodingProvider`
  Protocol + `FakeGeocodingProvider`.
- ✅ `POST /establishments`, `POST /establishments/{id}/availability` (usuário comum só reporta
  `community_reported`/`unavailable`, nunca `confirmed`), `GET /nearby` (lat/lng ou address).
- **Adiado, com motivo em `docs/DATA_MODEL.md`**: `PlacesProvider` (sem chamador — nada faz
  descoberta automática ainda), `MapsProvider` (concern client-side, sem backend), `user_locations`
  persistida (lat/lng por requisição, minimização de dados), adaptador real de geocoding (pendente
  de decisão de vendor — a única peça que realmente esperava essa decisão), mobile (precisa de
  `expo-location`, inverificável sem simulador).
- Validado: pytest (153 passed contra Postgres real, era 146 sem Postgres) · 7 evals PASS · smoke
  HTTP ao vivo confirmando ranking por distância e exclusão de `unavailable`.

## PHASE 5 — AI/RAG (⏸ adiada, sem dado real ainda — não pulada silenciosamente)
Revisada antes de planejar a Fase 6: sem trabalho real a fazer. Knowledge Base já existe e já
está isolada; User Data já nunca entra no RAG (invariante já respeitada, não tarefa pendente);
Community Knowledge explicitamente precisa de "volume real de experiências" que ainda não existe
(só dado de teste). Ver `docs/DATA_MODEL.md` §Fase 5 para o detalhamento. Retomar quando houver
uso real em produção — não antes.

## PHASE 6 — Recommendation Engine (✅ v1 concluída nesta sessão)
- ✅ Novo pacote `packages/recommendation` (puro, sem I/O/LLM): candidate generation (catálogo
  menos o que o usuário já tem/avaliou) → pontuação por afinidade de marca/país/força (de charutos
  avaliados ≥4★ ou já possuídos) → ranking determinístico.
- ✅ `GET /recommendations` — agrega `list_tastings`+`list_collections` (já existentes desde as
  Fases 2/3) + lookups no KG, sem tocar `packages/knowledge` nem `services/orchestrator`.
- **Desvio deliberado do texto original desta fase**: **não** criei `RequestKind.RECOMMEND` no
  Supervisor — v1 é 100% determinístico, rotear pela cascata violaria "não usar agente quando
  função determinística resolve" (mesmo raciocínio que manteve `/nearby` fora do Supervisor na
  Fase 4). Também **não** ficou bloqueada pelos `ANALYTICS_EVENT`s de view/search/save (que
  seguem não implementados, sem mobile emitindo) — usei sinal explícito já real (ratings,
  collections) em vez de esperar pelo sinal implícito.
- **Adiado, com motivo em `docs/DATA_MODEL.md`**: fallback de popularidade (precisa de query
  cross-user nova em `OltpRepository`, hoje escopado por usuário) — usuário sem histórico recebe
  `[]`, honesto em vez de fabricado. Re-rank por Sonnet/RAG — sem necessidade real hoje.
- Validado: pytest (163 passed contra Postgres real, era 156 sem Postgres) · 7 evals PASS · smoke
  HTTP ao vivo — usuário avaliou Cohiba Robustos 5★, recebeu outros Cohiba/Cuba/medium-full
  ranqueados com `reasons` explícitas; usuário sem histórico recebeu `[]`.

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
