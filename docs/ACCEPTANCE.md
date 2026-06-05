# Critérios de aceite do MVP — evidências

Mapa dos 6 critérios mensuráveis do prompt mestre para a evidência no repositório.
Reproduza tudo com `./scripts/verify.sh` (+ `docker compose up` para o ambiente).

| # | Critério | Meta | Resultado | Evidência |
|---|---|---|---|---|
| 1 | Reconhecimento de anilha end-to-end | ≥80% resolvido **sem** LLM de visão | **90% sem visão**, acurácia 100% | eval `band_recognition`; `services/agents/band_recognition` |
| 2 | Assistente com citações; tráfego barato | ≥70% por cache/KG/Haiku (**sem Opus**) | **100% sem Opus**, groundedness 100% | evals `cascade_efficiency` + `assistant_groundedness` |
| 3 | Observabilidade de IA (tier/custo) | custo/req e % por tier | **instrumentado** via `Tracer`/`TraceRecord` + `cascade_metrics` | `services/orchestrator/{providers,metrics}.py` |
| 4 | Custo médio do assistente | ≤ ~US$0,005/mensagem | **$0.00018/msg** | eval `cost_per_interaction` |
| 5 | CI verde | lint + testes + evals + segredos | configurado | `.github/workflows/ci.yml` (ruff/mypy/pytest/evals/gitleaks) |
| 6 | Ambiente local sobe com um comando | `docker compose up` + README | Postgres+Redis sobem; runbook | `infra/docker-compose.yml`, `README.md`, `docs/BOOTSTRAP.md` |

## Observações de fronteira do MVP (honestas)
- **Critério 3 — Langfuse:** a *instrumentação* (tokens, custo, tier resolvido, latência por etapa) está
  pronta atrás da interface `Tracer`; os **dashboards** exigem ligar o Langfuse real por env
  (`LANGFUSE_*`). No MVP usamos `FakeTracer` (inspecionável em teste).
- **Acurácia de visão/RAG real:** os providers são `Fake*` determinísticos (zero custo/chave). Os números
  acima medem a **lógica da cascata** (roteamento, thresholds, gating, citações). Acurácia absoluta exige
  Voyage/Gemini/Anthropic reais — ligação por slice via `.env` (`USE_FAKE_PROVIDERS=false`).
- **App mobile:** entregue como código (`apps/mobile`); execução exige simulador iOS/Android (fora do CI).
- **Seed do KG:** 32 charutos reais e de alta confiança; chegar a 100–300 SKUs exige catálogo verificado
  (registrado em `docs/PROGRESS.md`), não fabricação.
