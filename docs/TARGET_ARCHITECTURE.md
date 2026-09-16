# TARGET_ARCHITECTURE — Charutei Consumer Intelligence Platform

Base: `PROJECT_UPGRADE_AUDIT.md`. Princípio: **estender**, não substituir. Todo domínio novo entra
atrás de interface em `packages/knowledge`, todo evento novo entra em `packages/events.EventType`,
toda decisão de IA nova entra pelo Supervisor/Cascade existentes — nunca por um caminho paralelo.

## 1. Arquitetura proposta

Modular monolith mantido (seção 22 do prompt mestre confirma: não há justificativa concreta para
microservices agora — volume, equipe e domínio ainda cabem em um monolito modular). Três adições:

1. **Consumer Graph** — liga o KG de catálogo (já existe) ao histórico do usuário (tasting/collection,
   já existe) formalmente, via novas arestas `EdgeRel` (ex.: `EXPERIENCED`, `LOCATED_AT`) em vez de um
   grafo novo. O "Consumer Graph" do prompt mestre **é** `kg_nodes`/`kg_edges` mais um novo `NodeType.USER`
   e `NodeType.LOCATION`/`ESTABLISHMENT` — não uma tecnologia nova.
2. **Location domain** — novos módulos em `packages/knowledge` (`LocationRepo`) + providers abstraídos
   (`GeocodingProvider`/`MapsProvider`/`PlacesProvider`) atrás de interface, com `Fake*` para CI, seguindo
   exatamente o padrão já usado para LLM/embedding/visão.
2. **Scoring service** — novo pacote `packages/scoring` (determinístico, sem LLM) calcula
   EXPERIENCE_SCORE/KNOWLEDGE_SCORE/REPUTATION_SCORE/INFLUENCE_SCORE/CONSUMER_STATUS a partir de eventos
   e dados OLTP existentes — roda como job (mesmo padrão do `EmbeddingWorker`), não como chamada síncrona.

## 2. Domínios (nomenclatura consistente com o código existente)

| Domínio novo | Onde entra | Reaproveita |
|---|---|---|
| `LOCATION` / `ESTABLISHMENT` / `PRODUCT_AVAILABILITY` | `packages/knowledge` (novo `LocationRepo`) | padrão `*Repo` Protocol + Postgres/in-memory |
| `EXPERIENCE` (generalização de `tasting_notes`) | evolução de `tasting_notes`, não substituição | tabela existente ganha colunas opcionais |
| `REPUTATION`/`SCORE` | `packages/scoring` (novo) + tabela `user_scores` | eventos existentes + novos |
| `RECOMMENDATION` | novo capability no Supervisor (`RequestKind.RECOMMEND`) | Cascade, Governance, Registry |
| `ANALYTICS_EVENT` | expansão de `EventType` (packages/events) | outbox/idempotência já existentes |
| `SPONSOR`/`CAMPAIGN` | novo, fase tardia (Phase 8) | — |

## 3. Data model (incremental — ver ADRs para cada migration)

**Sem quebrar nada existente.** Migrations Alembic novas, nunca `ALTER` destrutivo em tabelas com dados:

- `kg_nodes`: novo `NodeType.ESTABLISHMENT`, `NodeType.LOCATION`, `NodeType.EVENT` (mantém padrão
  props JSONB). `kg_edges`: novo `EdgeRel.LOCATED_AT`, `EdgeRel.AVAILABLE_AT`, `EdgeRel.SELLS`.
- Nova tabela `establishments` (OLTP, não KG, porque tem campos operacionais mutáveis: nome, lat, lng,
  endereço, cidade/estado/país, tipo, horário, fonte, confiança, `updated_at`) — mirror do padrão
  `bands`/`tasting_notes`.
- Nova tabela `product_availability` (establishment_id, cigar_id, status ENUM
  `CONFIRMED|RECENTLY_CONFIRMED|COMMUNITY_REPORTED|UNKNOWN|UNAVAILABLE`, source, confidence, price?,
  quantity?, observed_at) — nunca reaproveita "estabelecimento existe" como "produto disponível"
  (requisito explícito do prompt mestre, seção 10).
- Nova tabela `user_locations` (user_id, lat/lng aproximados OU cidade/bairro, precision ENUM,
  captured_at, expires_at) — opt-in, minimização, expiração; nunca lat/lng contínuo sem consentimento
  explícito por feature (requisito seção 11).
- `tasting_notes` ganha colunas opcionais (não quebra linhas existentes): `structured_attrs JSONB`
  (intensidade/complexidade/duração inferidos), `ai_confidence FLOAT NULL`, `ai_source TEXT NULL` —
  texto original do usuário nunca é sobrescrito, só anotado (requisito seção 7).
- Nova tabela `user_scores` (user_id, experience_score, knowledge_score, reputation_score,
  influence_score, consumer_status, computed_at) — materializada por job, não calculada por request.
- `EventType` ganha: `experience_created/updated`, `product_viewed/searched/saved`,
  `recommendation_generated/viewed/clicked/accepted/rejected`, `establishment_viewed`, `store_clicked`,
  `map_opened`, `route_requested`, `event_viewed/joined` — todos passam pelo `outbox`/`ProcessedRegistry`
  existentes, sem infra nova.

Documento detalhado por migration vai em `docs/DATA_MODEL.md` (a criar no início da Fase 2, com o schema
exato, não antecipado aqui para evitar desenhar contra dado que ainda não foi coletado).

## 4. AI Orchestrator — agentes

Manter Supervisor determinístico. Adicionar **apenas os agentes necessários ao MVP do upgrade**, não os
5 do prompt mestre de uma vez:

- **Concierge** = o `assistant` atual, renomeado conceitualmente (já cobre pergunta/descoberta/harmonização).
  Não recriar.
- **Recommendation Agent** (novo, Phase 6) — capability nova no Supervisor, cascade própria:
  cache → regras determinísticas (popularidade/similaridade por KG) → Sonnet re-rank só quando sinal
  determinístico é insuficiente. Opus não deveria nunca ser necessário aqui (violaria "LLM é último
  recurso" se recomendação puro-ML precisasse de LLM generativo).
- **Consumer Intelligence** e **Community Intelligence**: adiadas — hoje não há dado de comportamento
  suficiente (sem event tracking ainda) para um agente ter o que interpretar. Implementar o pipeline de
  eventos primeiro (Phase 2/3); os agentes de interpretação entram só quando há volume real.
- **Brand Intelligence (B2B)**: não implementar agora. Modelo de dados acima (establishments,
  availability, scores) já não impede essa evolução — é o suficiente para "preparar", conforme pedido.

## 5. RAG — três corpora, não um só

Hoje existe um corpus único (`data/docs/cigar_docs.json`). Separar conceitualmente (mesma infra de
`DocumentStore`/`RagGenerator`, filtros por metadata, não pipelines paralelos):

- **Knowledge Base** (existente, expandir): produtos/marcas/categorias/harmonizações/terminologia.
- **User Data**: não vai para RAG — permanece em SQL/KG (`tasting_notes`, `collection_items`), consultado
  pelo resolver determinístico do KG, igual hoje. RAG nunca substitui o banco transacional (regra explícita
  do prompt mestre, seção 15).
- **Community Knowledge** (novo, Phase 7): agregações de tasting notes (ex.: "a comunidade descreve X como
  ___") — só entra em RAG depois que houver volume e um passo de agregação/anonimização determinístico,
  nunca texto bruto de um usuário atribuído a outro sem consentimento.

## 6. Recommendation Engine

Candidate generation (histórico do usuário via KG + `tasting_notes`, popularidade agregada, contexto de
localização quando disponível) → ranking determinístico por regras configuráveis (não ML no MVP — não
"usar ML onde uma regra simples resolve", seção 31) → re-rank opcional por Sonnet só se houver
ambiguidade. Sinais explícitos (rating/save) e implícitos (view/click/dwell) exigem o `ANALYTICS_EVENT`
model (seção 3) — é bloqueante: não há recomendação sem eventos.

## 7. Location Intelligence

`GeocodingProvider`/`MapsProvider`/`PlacesProvider` como Protocols (mesmo padrão de `LLMProvider`), com
`Fake*` para CI e adapter real plugável depois (não escolher vendor agora — decisão adiada até Phase 4,
ADR dedicado). Fluxo: candidate generation (estabelecimentos por marca/produto) → filtro de distância →
filtro de disponibilidade (nunca "existe" = "disponível") → ranking → apresentação. Localização do
usuário é sempre opt-in, aproximada por padrão, com expiração.

## 8. Modelo de eventos

Reaproveita `packages/events` integralmente (outbox transacional, idempotência, retry/DLQ). Só adiciona
`EventType`s (seção 3). Consumidores novos (scoring job, recommendation candidate builder) seguem o
mesmo padrão do `EmbeddingWorker`: idempotente, mark-before-ack, DLQ em falha.

## 9. Segurança e privacidade

- Localização: opt-in explícito por feature, precisão configurável, expiração automática de
  `user_locations`, nunca log de lat/lng exato em texto plano fora da tabela dedicada.
- Gamificação/score server-side: mover cálculo para backend fecha a lacuna de manipulação client-side
  hoje presente (ver auditoria §11.2).
- RAG: filtros de metadata por corpus evitam vazar `User Data` para prompts de Knowledge Base; nunca
  incluir PII bruta em contexto de LLM (resumir, como já manda o CLAUDE.md/LGPD).
- Monetização: `SPONSOR`/`CAMPAIGN` sempre marcado explicitamente na resposta (organic vs. sponsored),
  nunca misturado de forma invisível — requisito direto do prompt mestre.

## 10. Observabilidade

Reaproveita Langfuse já real. Adicionar aos traces existentes: latência/custo do Recommendation Agent,
latência de geo query, retrieval quality por corpus (separar Knowledge/Community no dashboard).

## 11. Escalabilidade

KG relacional continua suficiente (decisão já registrada no CLAUDE.md: Apache AGE não roda no Supabase
gerenciado; swap é implementação, não reescrita). `embeddings` precisa de dimensão fixa + índice HNSW
antes de Location/Recommendation aumentarem volume de ANN — dívida técnica priorizada na Fase 1.

## 12. O que este documento explicitamente NÃO decide agora

Vendor de mapas/geocoding, algoritmo de ranking de recomendação (regras exatas), modelo de precificação
de patrocínio, fórmula exata de Km de Fumaça. Cada um vira um ADR em `docs/ADR/` no início da fase que
o implementa, com as 7 perguntas da seção 32 do prompt mestre respondidas.
