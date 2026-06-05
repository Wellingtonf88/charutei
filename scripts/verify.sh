#!/usr/bin/env bash
# Verificação local espelhando o CI (Definition of Done de cada slice).
# Roda: lint + format + tipos + testes + os 4 gates de eval. Não cobre gitleaks (CI).
set -euo pipefail

bold() { printf "\n\033[1m▶ %s\033[0m\n" "$1"; }

bold "ruff (lint)";        uv run ruff check .
bold "ruff (format)";      uv run ruff format --check .
bold "mypy (tipos)";       uv run mypy packages services
bold "pytest (testes)";    uv run pytest -q
bold "evals (4 gates)";    uv run python -m evals

printf "\n\033[32m✓ tudo verde — pronto para commit\033[0m\n"
