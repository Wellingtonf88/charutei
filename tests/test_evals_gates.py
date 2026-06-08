"""Os 4 gates de qualidade/custo do MVP também rodam como pytest (defesa local + CI).

Garante que uma regressão que derrube um gate falhe o `pytest`, não só o job dedicado de evals.
"""

import pytest
from evals import (
    assistant_groundedness,
    band_recognition,
    cascade_efficiency,
    catalog_coverage,
    cost_per_interaction,
    embedding_ann_quality,
)

_EVALS = [
    cascade_efficiency,
    band_recognition,
    assistant_groundedness,
    cost_per_interaction,
    catalog_coverage,
    embedding_ann_quality,
]


@pytest.mark.parametrize("module", _EVALS, ids=lambda m: m.__name__.split(".")[-1])
async def test_eval_gate_passes(module) -> None:  # type: ignore[no-untyped-def]
    report = await module.run()
    assert report.passed, f"gate reprovado: {report.summary}"
