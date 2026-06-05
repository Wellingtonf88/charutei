"""Parser do catálogo de charutos (CSV) → registros normalizados.

O catálogo é a fonte estruturada que o Cigar Intelligence ingere. Campos incertos ficam
vazios (None) — nunca se inventa. Em produção, distribuidores/fontes alimentam este formato.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import BaseModel

VALID_STRENGTHS = {"mild", "medium", "medium-full", "full"}


class CatalogRecord(BaseModel):
    slug: str
    name: str
    brand: str
    country: str
    vitola: str | None = None
    strength: str | None = None
    factory: str | None = None

    @property
    def core(self) -> dict[str, str | None]:
        """Campos de alta confiança usados para detectar conflito numa re-ingestão."""
        return {
            "brand": self.brand,
            "country": self.country,
            "vitola": self.vitola,
            "strength": self.strength,
        }


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v or None


def parse_catalog_csv(path: Path) -> list[CatalogRecord]:
    """Lê o CSV (colunas: slug,name,brand,country,vitola,strength,factory). Valida força."""
    records: list[CatalogRecord] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for line_no, row in enumerate(csv.DictReader(fh), start=2):
            strength = _clean(row.get("strength"))
            if strength is not None and strength not in VALID_STRENGTHS:
                raise ValueError(
                    f"linha {line_no}: força inválida '{strength}' ({row.get('slug')})"
                )
            records.append(
                CatalogRecord(
                    slug=row["slug"].strip(),
                    name=row["name"].strip(),
                    brand=row["brand"].strip(),
                    country=row["country"].strip(),
                    vitola=_clean(row.get("vitola")),
                    strength=strength,
                    factory=_clean(row.get("factory")),
                )
            )
    return records
