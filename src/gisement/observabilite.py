"""Measured cost of a mapping (lot 20, ENF-10, KPI-8, R24).

A cost is measured, never estimated after the fact. The counters are fed by the
collectors (Transcribe minutes, Data Automation pages) and by the model calls
(tokens), then priced with `config/tarifs.json`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from gisement.types.campagne import CoutCampagne
from gisement.types.communs import arrondi, decimal

RACINE_CONFIG = Path(__file__).resolve().parents[2] / "config"


@dataclass
class CompteurCout:
    """Accumulates what a campaign consumes, service by service."""

    transcribe_minutes: Decimal = Decimal(0)
    data_automation_pages: int = 0
    jetons_entree: int = 0
    jetons_sortie: int = 0
    appels_modele: int = 0
    modele: str = "mixte"
    _tarifs: dict = field(default_factory=dict)

    def charger_tarifs(self, chemin: Path | None = None) -> None:
        cible = chemin or (RACINE_CONFIG / "tarifs.json")
        self._tarifs = json.loads(cible.read_text(encoding="utf-8"))

    def ajouter_transcribe(self, minutes: Decimal | float | int) -> None:
        self.transcribe_minutes += decimal(minutes)

    def ajouter_pages(self, pages: int) -> None:
        self.data_automation_pages += int(pages)

    def ajouter_appel(self, jetons_entree: int, jetons_sortie: int) -> None:
        self.jetons_entree += int(jetons_entree)
        self.jetons_sortie += int(jetons_sortie)
        self.appels_modele += 1

    def tarifer(self) -> CoutCampagne:
        """Price the counters with the configured tariffs (annex G.3)."""
        if not self._tarifs:
            self.charger_tarifs()
        t = self._tarifs
        transcribe = self.transcribe_minutes * decimal(t["transcribe_usd_par_minute"])
        bda = decimal(self.data_automation_pages) * decimal(t["data_automation_usd_par_page"])
        inference = self._inference(t)
        return CoutCampagne(
            transcribe_minutes=self.transcribe_minutes,
            transcribe_usd=arrondi(transcribe, 2),
            data_automation_pages=self.data_automation_pages,
            data_automation_usd=arrondi(bda, 2),
            jetons_entree=self.jetons_entree,
            jetons_sortie=self.jetons_sortie,
            inference_usd=arrondi(inference, 2),
            appels_modele=self.appels_modele,
            total_usd=arrondi(transcribe + bda + inference, 2),
        )

    def _inference(self, t: dict) -> Decimal:
        entree_m = decimal(self.jetons_entree) / Decimal(1_000_000)
        sortie_m = decimal(self.jetons_sortie) / Decimal(1_000_000)
        if self.modele == "nova_lite":
            cle_e, cle_s = "nova_lite_usd_par_million_entree", "nova_lite_usd_par_million_sortie"
        else:
            cle_e, cle_s = "modele_fort_usd_par_million_entree", "modele_fort_usd_par_million_sortie"
        return entree_m * decimal(t[cle_e]) + sortie_m * decimal(t[cle_s])


def estimation_annexe_g(tarifs: Path | None = None) -> Decimal:
    """The annex G.3 estimate of one mapping: 19.77 $."""
    t = json.loads((tarifs or (RACINE_CONFIG / "tarifs.json")).read_text(encoding="utf-8"))
    return arrondi(
        decimal(360) * decimal(t["transcribe_usd_par_minute"])
        + decimal(200) * decimal(t["data_automation_usd_par_page"])
        + decimal("1.400") * decimal(t["nova_lite_usd_par_million_entree"])
        + decimal("0.320") * decimal(t["nova_lite_usd_par_million_sortie"])
        + decimal("0.095") * decimal(t["modele_fort_usd_par_million_entree"])
        + decimal("0.045") * decimal(t["modele_fort_usd_par_million_sortie"]),
        2,
    )


def ecart_a_l_estimation(cout: CoutCampagne, estimation: Decimal | None = None) -> Decimal:
    """R24 - the gap between the measured cost and the annex G estimate."""
    estimation = estimation or estimation_annexe_g()
    if estimation <= 0:
        return Decimal(0)
    return arrondi(abs(cout.total_usd - estimation) / estimation, 4)


def repartition(cout: CoutCampagne) -> dict[str, Decimal]:
    """The share of each service in the cost (annex G.4)."""
    total = cout.total_usd or Decimal(1)
    return {
        "transcribe": arrondi(cout.transcribe_usd / total, 4),
        "data_automation": arrondi(cout.data_automation_usd / total, 4),
        "inference": arrondi(cout.inference_usd / total, 4),
    }
