"""Documents channel (lot 6): forms re-keyed, hand kept spreadsheets, procedures."""

from __future__ import annotations

from gisement.canaux.documents.collecteur import collecter, couverture, mesurer_volume, source_fichiers
from gisement.canaux.documents.data_automation import DataAutomation, ExtractionFigee

__all__ = [
    "DataAutomation",
    "ExtractionFigee",
    "collecter",
    "couverture",
    "mesurer_volume",
    "source_fichiers",
]
