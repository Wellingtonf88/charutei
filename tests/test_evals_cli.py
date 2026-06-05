"""Semântica de saída do harness de evals: 0 quando todos passam, !=0 quando um gate falha."""

from evals.__main__ import EVALS, _run
from evals.harness import EvalReport


async def test_run_all_evals_returns_zero() -> None:
    assert await _run([]) == 0


async def test_failing_gate_returns_nonzero(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def _fail() -> EvalReport:
        return EvalReport(name="fake", passed=False, summary="forçado a falhar")

    monkeypatch.setitem(EVALS, "fake", _fail)
    assert await _run(["fake"]) == 1
