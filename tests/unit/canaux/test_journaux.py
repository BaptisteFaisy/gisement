"""Lot 8 - the application logs collector and the published coverage."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from gisement.canaux import journaux
from gisement.types import Canal, StatutDuree


def test_les_journaux_ont_le_volume_annonce(corpus: Path) -> None:
    assert journaux.mesurer_volume(journaux.source_fichiers(corpus)) == 12400


def test_les_durees_sont_converties_en_minutes(corpus: Path, parametres) -> None:
    activites, rapport = journaux.collecter(journaux.source_fichiers(corpus), parametres)
    assert len(activites) == 12400
    assert rapport["exclus"] == 0
    assert all(a.canal == Canal.JOURNAUX for a in activites)
    assert all(a.duree_statut == StatutDuree.MESUREE for a in activites)
    minutes = [a.duree_mesuree_minutes for a in activites[:200]]
    assert all(m is not None and 0 < m < 600 for m in minutes)


def test_les_journaux_ont_le_horodatage_et_le_groupe(corpus: Path, parametres) -> None:
    activites, _ = journaux.collecter(journaux.source_fichiers(corpus), parametres)
    assert activites[0].horodatage.year == 2026
    assert activites[0].groupe_pseudonyme
    assert activites[0].service in {"adv", "comptabilite", "support", "approvisionnements"}


def test_le_coefficient_de_couverture_est_borne(corpus: Path, parametres) -> None:
    activites, _ = journaux.collecter(journaux.source_fichiers(corpus), parametres)
    ratio = journaux.couverture(activites, Decimal("4040"))
    assert Decimal(0) < ratio <= Decimal(1)
