# CHARUTEI — Contexto para o Claude Code

## Princípio inviolável
**"LLM é o último recurso."** Toda lógica passa pela cascata e para no degrau mais barato:
`cache → KG/SQL → Haiku/embeddings → Sonnet+RAG → Opus (gated)`.
Nenhuma chamada a LLM/embedding fora do Orchestrator.

## Stack (tier de fundação — não trocar sem aprovação)
Mobile: Expo. Backend: FastAPI (modular monolith). Agentes: LangGraph + Claude Agent SDK + MCP.
Modelos: Haiku 4.5 / Sonnet 4.6 / Opus 4.8 + Gemini Flash (visão). Embeddings: Voyage 4.
Dados: Postgres + pgvector. Cache/eventos: Redis + pgmq/Streams. Obs.: Langfuse.

## Decisão de arquitetura — Knowledge Graph
KG é **relacional** no MVP (`kg_nodes`, `kg_edges`) **atrás de `KnowledgeGraphRepo`**.
Apache AGE não roda no Postgres gerenciado do Supabase; swap p/ AGE/Neo4j na escala é troca de
implementação, não reescrita. Harmonizações/fichas resolvem por SQL determinístico (degrau 2), sem LLM.

## Convenções
- Acesso a dados SEMPRE atrás de interfaces em `packages/knowledge` (swap p/ Qdrant/Neo4j depois).
- Contratos de agente em `packages/contracts` (Pydantic). Eventos idempotentes + outbox.
- Default de geração = Sonnet; Opus só por gating de confiança + flag + log de custo.
- Prompt caching + Batch API obrigatórios em jobs offline; embedding cache por hash de conteúdo.
- Provedores externos atrás de interface com impl `Fake*`; `USE_FAKE_PROVIDERS` controla CI.
- Sem segredos em código (.env gitignored + .env.example). LGPD: memória resumida, nunca bruta.

## Definition of Done (por slice)
Código + testes verdes + eval relevante passando + conventional commit + `docs/PROGRESS.md` atualizado.
Pausar e reportar ao fim de cada slice (≤10 linhas: mudanças, testes/evals, % por tier, próxima slice).

## Sempre planejar antes de editar `services/orchestrator/` e `packages/knowledge/`.

## Comandos
- Ambiente: `./scripts/bootstrap.sh` → `docker compose -f infra/docker-compose.yml up -d`
- Testes: `uv run pytest` · Lint: `uv run ruff check .` · Tipos: `uv run mypy .`
