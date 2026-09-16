# DATA_MODEL — Fase 2 (Experience Engine)

Schema exato após a Fase 2 do upgrade (ver `docs/IMPLEMENTATION_ROADMAP.md`). Complementa o
inventário do `docs/PROJECT_UPGRADE_AUDIT.md` §4 com o que mudou nesta fase.

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

## Mobile

Nenhuma mudança de contrato para quem já consome `/collection` (singular) e `/collection/items`
sem `collection_id` — 100% retrocompatível. UI para criar/trocar collections é trabalho de
produto/design separado, fora desta fase.
