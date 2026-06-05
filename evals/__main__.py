"""CLI do harness de evals.

Uso:
  uv run python -m evals                 # roda todos os evals disponíveis
  uv run python -m evals cascade_efficiency
Sai com código != 0 se algum gate falhar (reprovando o CI).
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable

from evals import (
    assistant_groundedness,
    band_recognition,
    cascade_efficiency,
    cost_per_interaction,
)
from evals.harness import EvalReport

# Registro de evals disponíveis (os 4 gates do Anexo C do MVP).
EVALS: dict[str, Callable[[], Awaitable[EvalReport]]] = {
    "cascade_efficiency": cascade_efficiency.run,
    "band_recognition": band_recognition.run,
    "assistant_groundedness": assistant_groundedness.run,
    "cost_per_interaction": cost_per_interaction.run,
}


async def _run(names: list[str]) -> int:
    selected = names or list(EVALS)
    reports = [await EVALS[name]() for name in selected]
    print("\n".join(r.render() for r in reports))
    return 0 if all(r.passed for r in reports) else 1


def main() -> None:
    args = [a for a in sys.argv[1:] if a in EVALS]
    unknown = [a for a in sys.argv[1:] if a not in EVALS]
    if unknown:
        print(f"eval(s) desconhecido(s): {', '.join(unknown)}. Disponíveis: {', '.join(EVALS)}")
        sys.exit(2)
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
