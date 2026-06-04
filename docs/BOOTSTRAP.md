# BOOTSTRAP — ambiente de desenvolvimento

O CHARUTEI roda como **modular monolith** em Python 3.12, com Postgres+pgvector e Redis locais via
container. Este guia deixa a máquina pronta para `uv run pytest` e `docker compose up`.

## Por que estas escolhas
- **OrbStack** em vez de Docker Desktop: bem mais leve no Mac, fornece o comando `docker`/`docker compose`.
- **uv** em vez de venv/pip manual: workspace multi-pacote, lockfile rápido, gerencia o Python 3.12
  (o Python do sistema, 3.9, é antigo demais para a stack).

## Passos

### 1. Tooling
```bash
./scripts/bootstrap.sh
```
O script é idempotente. Se ele pedir para abrir o OrbStack uma vez (conclusão da instalação) ou instalar o
Homebrew, faça e rode de novo.

Instalação manual equivalente:
```bash
brew install --cask orbstack   # abra o app uma vez
brew install uv
uv python install 3.12
```

### 2. Plano de dados local
```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps   # postgres e redis healthy
```

### 3. Dependências e ambiente
```bash
uv sync --all-packages --dev
cp .env.example .env     # padrão usa provedores FAKE (sem chaves, sem custo)
```

### 4. Verificação
```bash
uv run ruff check .
uv run pytest -q
```

## Chaves reais (por slice)
Mantenha `USE_FAKE_PROVIDERS=true` para dev/CI. Ao testar um slice contra serviços vivos, preencha em `.env`
apenas a chave necessária (ex.: `ANTHROPIC_API_KEY` na S2, `VOYAGE_API_KEY` na S3) e ligue `USE_FAKE_PROVIDERS=false`.
Nunca comite o `.env`.
