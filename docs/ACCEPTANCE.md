# Critérios de aceite do MVP — evidências

Mapa dos 6 critérios mensuráveis do prompt mestre para a evidência no repositório.
Reproduza tudo com `./scripts/verify.sh` (+ `docker compose up` para o ambiente).

| # | Critério | Meta | Resultado | Evidência |
|---|---|---|---|---|
| 1 | Reconhecimento de anilha end-to-end | ≥80% resolvido **sem** LLM de visão | **90% sem visão**, acurácia 100% | eval `band_recognition`; `services/agents/band_recognition` |
| 2 | Assistente com citações; tráfego barato | ≥70% por cache/KG/Haiku (**sem Opus**) | **100% sem Opus**, groundedness 100% | evals `cascade_efficiency` + `assistant_groundedness` |
| 3 | Observabilidade de IA (tier/custo) | custo/req e % por tier | **Langfuse self-host real**: traces+custo+tier+groundedness ingeridos; 5 dashboards-as-code | `langfuse_tracer.py`, `scripts/langfuse_dashboards.py`, `docs/LANGFUSE.md` |
| 4 | Custo médio do assistente | ≤ ~US$0,005/mensagem | **$0.00018/msg** | eval `cost_per_interaction` |
| 5 | CI verde | lint + testes + evals + segredos | configurado | `.github/workflows/ci.yml` (ruff/mypy/pytest/evals/gitleaks) |
| 6 | Ambiente local sobe com um comando | `docker compose up` + README | Postgres+Redis sobem; runbook | `infra/docker-compose.yml`, `README.md`, `docs/BOOTSTRAP.md` |

## Observações de fronteira do MVP (honestas)
- **Critério 3 — Langfuse:** agora **real** (self-host v3 no OrbStack). Traces, custo, tier, latência e
  scores de groundedness são ingeridos e verificados via API; os 5 dashboards são **dashboards-as-code**
  (Metrics API). Ressalva documentada em `docs/LANGFUSE.md`: a API pública não *cria* dashboards de UI
  (os widgets são recriados na UI a partir das queries exportadas). Em CI/dev sem chaves, cai no `FakeTracer`.
- **Acurácia de visão/RAG real:** os providers são `Fake*` determinísticos (zero custo/chave). Os números
  acima medem a **lógica da cascata** (roteamento, thresholds, gating, citações). Acurácia absoluta exige
  Voyage/Gemini/Anthropic reais — ligação por slice via `.env` (`USE_FAKE_PROVIDERS=false`).
- **App mobile:** entregue como código (`apps/mobile`); execução exige simulador iOS/Android (fora do CI).
- **Seed do KG:** 32 charutos reais e de alta confiança; chegar a 100–300 SKUs exige catálogo verificado
  (registrado em `docs/PROGRESS.md`), não fabricação.
