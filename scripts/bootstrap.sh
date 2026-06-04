#!/usr/bin/env bash
# Bootstrap de tooling do CHARUTEI (macOS). Idempotente: checa antes de instalar.
# Instala/verifica: OrbStack (Docker leve), uv (Python), Python 3.12.
set -euo pipefail

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }

bold "CHARUTEI · bootstrap de ambiente"

# --- Homebrew (necessário para OrbStack/uv no Mac) ---
if ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew não encontrado. Instale: https://brew.sh e rode este script de novo."
  exit 1
fi
ok "Homebrew presente"

# --- OrbStack (fornece o comando docker) ---
if ! command -v docker >/dev/null 2>&1; then
  warn "Docker ausente — instalando OrbStack..."
  brew install --cask orbstack
  warn "Abra o OrbStack uma vez para concluir a instalação, depois rode este script de novo."
  exit 1
fi
ok "docker disponível ($(docker --version 2>/dev/null || echo '?'))"

# --- uv ---
if ! command -v uv >/dev/null 2>&1; then
  warn "uv ausente — instalando..."
  brew install uv
fi
ok "uv disponível ($(uv --version))"

# --- Python 3.12 via uv ---
uv python install 3.12
ok "Python 3.12 disponível via uv"

bold "Pronto. Próximos passos:"
cat <<'EOF'
  docker compose -f infra/docker-compose.yml up -d
  uv sync --all-packages --dev
  cp .env.example .env
  uv run pytest -q
EOF
