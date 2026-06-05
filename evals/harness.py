"""Estruturas comuns do harness de evals."""

from __future__ import annotations

from pydantic import BaseModel


class EvalReport(BaseModel):
    name: str
    passed: bool
    summary: str
    details: dict[str, float] = {}

    def render(self) -> str:
        status = "PASS ✅" if self.passed else "FAIL ❌"
        line = f"[{status}] {self.name} — {self.summary}"
        if self.details:
            line += "\n  " + " · ".join(f"{k}={v:.4f}" for k, v in self.details.items())
        return line
