"""Band Recognition Agent: foto de anilha → cigar_id, com cascata de visão cost-aware."""

from charutei_band_recognition.agent import (
    CAPABILITY,
    BandRecognitionAgent,
    default_spec,
)
from charutei_band_recognition.catalog import BAND_KIND, build_band_catalog

__all__ = [
    "BandRecognitionAgent",
    "CAPABILITY",
    "default_spec",
    "build_band_catalog",
    "BAND_KIND",
]
