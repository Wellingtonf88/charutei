# Observabilidade de IA — Langfuse (self-host) + 5 dashboards

Observabilidade de IA real do CHARUTEI: traces, custo, tokens, tier resolvido, latência por
etapa e scores de qualidade — tudo atrás da interface `Tracer` (nenhum SDK fora do Orchestrator).

## Subir o Langfuse (self-host, OrbStack)
Stack v3 isolada (Postgres/Redis internos para não conflitar com os do CHARUTEI):
```bash
cp infra/langfuse/.env.example infra/langfuse/.env   # ajuste segredos (openssl rand ...)
docker compose -p charutei-langfuse --env-file infra/langfuse/.env \
  -f infra/langfuse/docker-compose.yml up -d
```
- UI/API: **http://localhost:3010** (3000 costuma estar ocupado). Login: `dev@charutei.local` / a senha do `.env`.
- Chaves do projeto são **auto-provisionadas** via `LANGFUSE_INIT_*` (sem setup manual).

## Ligar o tracing no CHARUTEI
`build_tracer()` devolve o `LangfuseTracer` quando há chaves no ambiente; senão, `FakeTracer`.
Funciona **mesmo com providers fake** (tracing real de runs sem custo de LLM):
```bash
export LANGFUSE_HOST=http://localhost:3010 \
       LANGFUSE_PUBLIC_KEY=pk-lf-charutei-dev LANGFUSE_SECRET_KEY=sk-lf-charutei-dev
uv run --extra providers python scripts/langfuse_demo.py   # gera tráfego real → traces
```
O que é enviado: uma **trace por requisição** (tagueada por capability), **generations** com
modelo/tokens/custo/tier, **spans** para cache/KG, e **scores** (groundedness).

## Os 5 dashboards (dashboards-as-code)
Definidos em código em `scripts/langfuse_dashboards.py` (cada painel = uma query da Metrics API)
e exportados em `infra/langfuse/dashboards/*.json`:

| Dashboard | Painéis (métrica / fonte) |
|---|---|
| **FinOps de IA** | custo total; custo por modelo; requisições por capability |
| **Cascata** | distribuição por degrau (observações por `name`: cache/deterministic/generation/vision) |
| **Qualidade & Segurança** | groundedness média (scores-numeric) |
| **Retrieval / RAG** | latência p95 por etapa |
| **Operacional** | observações por nível (erros); latência p50 por etapa |

Render ao vivo / exportar:
```bash
uv run python scripts/langfuse_dashboards.py            # computa os 5 da Metrics API
uv run python scripts/langfuse_dashboards.py --export   # grava as definições JSON
```

## Limitação honesta (descoberta empírica)
A **API pública** do Langfuse v3 **não cria dashboards de UI** (`/api/public/dashboards` → 404);
ela expõe a **Metrics API** (consulta). Por isso:
- os 5 dashboards são **definidos como código** e **computados ao vivo** da Metrics API (reprodutível);
- as definições JSON trazem as queries prontas para **recriar os widgets na UI** (passo manual de poucos
  minutos), ou para automação futura via API interna quando/se exposta.
- Dimensões custom (ex.: `metadata.tier`) não são agregáveis; por isso a **cascata é agregada por
  `name`** da observação, que codifica o passo. Métricas do blueprint sem fonte no Langfuse (recall/
  precision de RAG, lag de fila/DLQ) vêm de outras fontes (evals e o event bus), fora deste painel.

## Encerrar
```bash
docker compose -p charutei-langfuse -f infra/langfuse/docker-compose.yml down        # mantém volumes
docker compose -p charutei-langfuse -f infra/langfuse/docker-compose.yml down -v      # apaga dados
```
