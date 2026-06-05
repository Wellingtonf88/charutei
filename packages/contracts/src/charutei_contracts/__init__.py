"""Contratos compartilhados do CHARUTEI (Pydantic).

Toda I/O de agente e o resultado da cascata de inteligência vivem aqui, para que
serviços e workers dependam de schemas — nunca de implementações concretas.
"""

from charutei_contracts.band import BandCandidate, BandImage, BandRecognitionResult
from charutei_contracts.cascade import CascadeResult, Citation, Tier

__all__ = [
    "CascadeResult",
    "Citation",
    "Tier",
    "BandImage",
    "BandCandidate",
    "BandRecognitionResult",
]
