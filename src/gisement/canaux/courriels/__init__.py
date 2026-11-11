"""Email channel (lot 5): the work that goes through no tool at all."""

from __future__ import annotations

from gisement.canaux.courriels.collecteur import (
    SPEC,
    collecter,
    couverture,
    mesurer_volume,
    source_fichiers,
)
from gisement.canaux.courriels.echantillonnage import echantillonner_stratifie

__all__ = [
    "SPEC",
    "collecter",
    "couverture",
    "echantillonner_stratifie",
    "mesurer_volume",
    "source_fichiers",
]
