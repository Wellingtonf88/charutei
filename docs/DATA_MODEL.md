# DATA_MODEL — Fases 2 e 3 (Experience Engine + Consumer Identity)

Schema exato após as Fases 2 e 3 do upgrade (ver `docs/IMPLEMENTATION_ROADMAP.md`). Complementa o
inventário do `docs/PROJECT_UPGRADE_AUDIT.md` §4 com o que mudou em cada fase.

## Fase 2 (Experience Engine)

## O que NÃO mudou

Nenhuma tabela nova, nenhuma coluna nova, **nenhuma migration nesta fase**. `collections` já
suportava N linhas por `user_id` desde a Fase 1 (S1) — só não havia como a API expor isso. Ver
`packages/knowledge/src/charutei_knowledge/postgres/schema.sql` para o DDL completo (inalterado).

## Collections — de "uma por usuário" para N por usuário

- A collection com id `col:{user_id}` continua sendo, por convenção, o **humidor padrão**:
  criada lazily no primeiro `POST /collection/items` sem `collection_id`, é o que `GET /collection`
  (singular) sempre retorna.
- Collections adicionais têm `id = uuid4().hex` (nunca client-controlled), criadas via
  `POST /collections {"name": str}`.
- `OltpRepository.list_collections(user_id) -> list[Collection]` (novo método) retorna todas —
  humidor padrão + nomeadas.
- `POST /collection/items` aceita `collection_id: str | None` opcional. `None` (comportamento
  atual, o que o mobile envia hoje) → escreve no humidor padrão. Preenchido → valida
  `collection.user_id == user.id` antes de escrever; senão `404` (não distingue "não existe" de
  "não é sua", para não vazar dados de outro usuário).
- Não há flag `is_default` no schema — o humidor padrão é reconhecido só pela convenção de id
  `col:{user_id}`. Suficiente para o MVP; se o mobile um dia precisar diferenciar visualmente,
  isso vira uma coluna então (YAGNI até lá).

## Eventos novos

`EventType` (`packages/events/src/charutei_events/models.py`), convenção `verbo.substantivo` em
português (igual aos 4 existentes — não copiar o inglês do prompt mestre literalmente):

| Evento | Emitido em | Payload |
|---|---|---|
| `colecao.criada` | `POST /collections` | `{user_id, collection_id, name}` |
| `degustacao.registrada` | `POST /tasting` | `{user_id, cigar_id, tasting_id}` |

Nenhum consumidor dedicado ainda (o `EmbeddingWorker` os reconhece e faz ack sem efeito — ver
`packages/knowledge/../charutei_embedding_worker/worker.py::_handle`, fallback "eventos não
relevantes"). Existem para dar à Fase 6 (Recommendation Engine) e à Fase 3 (Km de Fumaça/scoring)
sinal real de "experiência registrada" / "coleção criada" — sem isso, aquelas fases não têm dado
para consumir quando chegar a hora.

## Deliberadamente fora desta fase

`tasting_notes` **não** ganhou `structured_attrs JSONB` / `ai_confidence FLOAT` / `ai_source TEXT`
(cogitado no `TARGET_ARCHITECTURE.md` §3 para atributos inferidos por IA a partir do texto livre da
nota). Não existe hoje nenhum agente que leia texto livre e infira esses atributos — adicionar as
colunas agora seria schema sem leitor/escritor. Entram junto com o agente que as popula, na Fase 5
(AI/RAG), não antes. `tasting_notes` também não foi renomeada para "experiences": é extensão do que
já existe, não reescrita (mesma decisão registrada no `TARGET_ARCHITECTURE.md`).

## Mobile (Fase 2)

Nenhuma mudança de contrato para quem já consome `/collection` (singular) e `/collection/items`
sem `collection_id` — 100% retrocompatível. UI para criar/trocar collections é trabalho de
produto/design separado, fora daquela fase.

## Fase 3 (Consumer Identity — Km de Fumaça)

**Sem migration** — assim como a Fase 2, calcula tudo a partir de tabelas já existentes
(`tasting_notes`, `collection_items` via `collections`). Novo pacote `packages/scoring` (puro, sem
I/O) + novo endpoint `GET /profile`.

### `GET /profile`

Agrega, sob demanda (não materializado — ver decisão abaixo), a partir de
`ctx.oltp.list_tastings(user_id)` + `ctx.oltp.list_collections(user_id)` (soma itens de **todas**
as collections, não só o humidor padrão — "km de fumaça" é a bagagem total) + lookups no KG
(`from_country`/`made_by` por `cigar_id`, mesmo padrão do handler `/catalog`):

| Campo | Origem |
|---|---|
| `total_tastings`, `avg_rating`, `top_flavors`, `distinct_flavors` | `tasting_notes` do usuário |
| `humidor_size` | soma de `collection_items` em todas as collections do usuário |
| `distinct_countries` | países distintos dos charutos no humidor (via KG) |
| `streak_days` | dias consecutivos com degustação (`charutei_scoring.compute_streak`) |
| `experience_score` | `charutei_scoring.compute_experience_score` |
| `knowledge_score` | `charutei_scoring.compute_knowledge_score` |
| `consumer_status` | `charutei_scoring.compute_consumer_status` (nome/índice/progresso) |
| `badges` | `charutei_scoring.compute_badges` (mesmos 6 de antes, agora server-side) |

### Fórmula (v1, deliberadamente simples — constantes em `packages/scoring/.../scoring.py`)

```
EXPERIENCE_SCORE = humidor_size + total_tastings*2 + distinct_countries*3 + distinct_brands*2
                    + min(streak_days, 10)
KNOWLEDGE_SCORE   = tastings_with_notes*3 + distinct_flavors*2
CONSUMER_STATUS   = tier(EXPERIENCE_SCORE + KNOWLEDGE_SCORE) contra STATUS_THRESHOLDS
                    [0, 15, 40, 80] → Novato/Aficionado/Conhecedor/Mestre Charuteiro
```

Por que a soma dos dois scores (e não só `EXPERIENCE_SCORE`) decide o status: o prompt mestre é
explícito — *"quantidade bruta de registros não deve automaticamente significar maior
autoridade"*. Um usuário com muita atividade mas nenhuma nota escrita (knowledge_score baixo) sobe
de status mais devagar que um com atividade moderada e degustações bem documentadas.

### Deliberadamente fora desta fase

- **`REPUTATION_SCORE` / `INFLUENCE_SCORE`**: pedidos no prompt mestre, mas dependem de sinal
  social (seguidores, curtidas, taxa de aceitação de recomendação) que só existe a partir da Fase 7
  (Community Intelligence) — hoje não há uma tabela de follow/like/interação. `GET /profile`
  simplesmente **não inclui** esses campos ainda (não expõe `0`, que seria enganoso: "sem dado" ≠
  "reputação zero"). Entram quando o domínio Community existir.
- **Tabela `user_scores` + job de materialização**: o roadmap original previa isso. Não
  implementado — na escala atual, calcular sob demanda a cada request é barato (mesmas queries que
  já existiam + uns lookups no KG) e evita infraestrutura sem necessidade real (mesma disciplina
  aplicada ao índice HNSW na Fase 1). Vira follow-up quando/se pesar, reaproveitando o padrão de
  job in-process já estabelecido em `pump_events` (Fase 1).

## Mobile (Fase 3)

`apps/mobile/app/(tabs)/profile.tsx` trocou o cálculo local (`insights.ts`) por `useProfile()` →
`GET /profile`. `insights.ts` perdeu `computePalate/computeLevel/computeStreak/computeBadges`
(agora no backend); mantém só `shareSummary` (formatação de texto para o Share nativo).
