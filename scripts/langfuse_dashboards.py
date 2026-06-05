"""Dashboards-as-code do CHARUTEI sobre a Metrics API do Langfuse.

Os 5 dashboards do blueprint (FinOps, Cascata, Qualidade, Retrieval/RAG, Operacional) são
definidos AQUI como código (cada painel = uma query da Metrics API) e renderizados ao vivo da
instância — reprodutível e versionado.

Nota honesta: a API PÚBLICA do Langfuse v3 não cria dashboards de UI (só consulta métricas).
Este script (a) computa cada dashboard via Metrics API e (b) com --export grava as definições
em infra/langfuse/dashboards/*.json (queries prontas para colar nos widgets da UI).

    LANGFUSE_HOST=http://localhost:3010 LANGFUSE_PUBLIC_KEY=pk-lf-charutei-dev \
      LANGFUSE_SECRET_KEY=sk-lf-charutei-dev uv run python scripts/langfuse_dashboards.py [--export]
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "infra" / "langfuse" / "dashboards"

HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3010")
PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")


def _window() -> tuple[str, str]:
    now = datetime.now(UTC)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (now - timedelta(days=30)).strftime(fmt), (now + timedelta(days=1)).strftime(fmt)


# Cada painel é uma query da Metrics API. Dimensões disponíveis no Langfuse: name, tags,
# providedModelName, level, userId... (metadata custom NÃO é dimensão — por isso a cascata é
# agregada por `name` da observação, que codifica o passo).
DASHBOARDS: list[dict[str, Any]] = [
    {
        "name": "FinOps de IA",
        "slug": "finops",
        "panels": [
            {
                "title": "Custo total (USD)",
                "view": "observations",
                "metrics": [{"measure": "totalCost", "aggregation": "sum"}],
                "dimensions": [],
            },
            {
                "title": "Custo por modelo",
                "view": "observations",
                "metrics": [
                    {"measure": "totalCost", "aggregation": "sum"},
                    {"measure": "count", "aggregation": "count"},
                ],
                "dimensions": [{"field": "providedModelName"}],
            },
            {
                "title": "Requisições por capability",
                "view": "traces",
                "metrics": [{"measure": "count", "aggregation": "count"}],
                "dimensions": [{"field": "tags"}],
            },
        ],
    },
    {
        "name": "Cascata",
        "slug": "cascata",
        "panels": [
            {
                "title": "Distribuição por degrau (passo da cascata)",
                "view": "observations",
                "metrics": [{"measure": "count", "aggregation": "count"}],
                "dimensions": [{"field": "name"}],
            },
        ],
    },
    {
        "name": "Qualidade & Segurança",
        "slug": "qualidade",
        "panels": [
            {
                "title": "Groundedness (média) por score",
                "view": "scores-numeric",
                "metrics": [
                    {"measure": "value", "aggregation": "avg"},
                    {"measure": "count", "aggregation": "count"},
                ],
                "dimensions": [{"field": "name"}],
            },
        ],
    },
    {
        "name": "Retrieval / RAG",
        "slug": "retrieval",
        "panels": [
            {
                "title": "Latência p95 por etapa",
                "view": "observations",
                "metrics": [{"measure": "latency", "aggregation": "p95"}],
                "dimensions": [{"field": "name"}],
            },
        ],
    },
    {
        "name": "Operacional",
        "slug": "operacional",
        "panels": [
            {
                "title": "Observações por nível (erros)",
                "view": "observations",
                "metrics": [{"measure": "count", "aggregation": "count"}],
                "dimensions": [{"field": "level"}],
            },
            {
                "title": "Latência p50 por etapa",
                "view": "observations",
                "metrics": [{"measure": "latency", "aggregation": "p50"}],
                "dimensions": [{"field": "name"}],
            },
        ],
    },
]


def query_metrics(client: httpx.Client, panel: dict[str, Any]) -> list[dict[str, Any]]:
    from_ts, to_ts = _window()
    query = {
        "view": panel["view"],
        "metrics": panel["metrics"],
        "dimensions": panel["dimensions"],
        "fromTimestamp": from_ts,
        "toTimestamp": to_ts,
    }
    resp = client.get(
        f"{HOST}/api/public/metrics",
        params={"query": json.dumps(query)},
        auth=(PUBLIC_KEY, SECRET_KEY),
        timeout=30,
    )
    resp.raise_for_status()
    data: list[dict[str, Any]] = resp.json().get("data", [])
    return data


def export_definitions() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    for dash in DASHBOARDS:
        path = EXPORT_DIR / f"{dash['slug']}.json"
        path.write_text(json.dumps(dash, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"definições exportadas em {EXPORT_DIR.relative_to(ROOT)}/ ({len(DASHBOARDS)} dashboards)"
    )


def main() -> None:
    if "--export" in sys.argv[1:]:
        export_definitions()
        return
    if not (PUBLIC_KEY and SECRET_KEY):
        raise SystemExit("defina LANGFUSE_PUBLIC_KEY/SECRET_KEY (e LANGFUSE_HOST).")

    with httpx.Client() as client:
        for dash in DASHBOARDS:
            print(f"\n══ {dash['name']} ══")
            for panel in dash["panels"]:
                rows = query_metrics(client, panel)
                print(f"  • {panel['title']}")
                for row in rows or [{}]:
                    print(f"      {row}")


if __name__ == "__main__":
    main()
