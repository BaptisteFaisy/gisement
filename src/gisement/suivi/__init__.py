"""Quarterly follow-up: realised against predicted (lot 17, EF-63, KPI-6).

Three layers:
  * `base`        - one quarter of realised against predicted, and the
                    cumulative accuracy that is published to the client;
  * `calibration` - the defaults corrected from the history, bounded and
                    explained (idea #4);
  * `alertes`     - what deserves an owner's attention this quarter.
"""

from __future__ import annotations

from gisement.suivi.alertes import Alerte, detecter, resume
from gisement.suivi.base import comparer, ecart_trimestriel, precision_cumulee
from gisement.suivi.calibration import (
    BORNES,
    CoefficientCalibre,
    appliquer,
    calibrer,
    ratio_par_projet,
)

__all__ = [
    "BORNES",
    "Alerte",
    "CoefficientCalibre",
    "appliquer",
    "calibrer",
    "comparer",
    "detecter",
    "ecart_trimestriel",
    "precision_cumulee",
    "ratio_par_projet",
    "resume",
]
