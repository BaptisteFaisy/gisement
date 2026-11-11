"""Lot 5 - the email collector and its stratified, reproducible sampling."""

from __future__ import annotations

from pathlib import Path

from gisement.canaux import courriels
from gisement.canaux.courriels.echantillonnage import echantillonner_stratifie, repartir
from gisement.types import StatutDuree


def test_le_volume_du_canal_est_annonce(corpus: Path) -> None:
    assert courriels.mesurer_volume(courriels.source_fichiers(corpus)) == 2000


def test_les_courriels_n_ont_pas_de_duree_mesuree(corpus: Path, parametres) -> None:
    """9.3 - a message carries no timestamp of the work it caused."""
    activites, rapport = courriels.collecter(courriels.source_fichiers(corpus), parametres)
    assert len(activites) == 2000
    assert all(a.duree_statut == StatutDuree.INFERREE for a in activites)
    assert all(a.duree_mesuree_minutes is None for a in activites)
    assert rapport["exclus"] == 0


def test_l_echantillon_est_reproductible_et_stratifie(corpus: Path, parametres) -> None:
    """EF-13 - same seed, same sample; the strata are published."""
    activites, rapport = courriels.collecter(courriels.source_fichiers(corpus), parametres, cible=1500)
    assert len(activites) == 1500
    assert rapport["echantillon_cible"] == 1500
    assert rapport["echantillon_retenu"] == 1500
    assert rapport["echantillon_strates"]
    autre, _ = courriels.collecter(courriels.source_fichiers(corpus), parametres, cible=1500)
    assert [a.id for a in activites] == [a.id for a in autre]


def test_les_adresses_sont_pseudonymisees(corpus: Path, parametres) -> None:
    """R9 - no address survives ingestion."""
    activites, rapport = courriels.collecter(courriels.source_fichiers(corpus), parametres)
    assert rapport["pseudonymes_appliques"] > 0
    for activite in activites[:300]:
        assert "@demo.example" not in activite.texte
        assert "PSD-" in activite.texte


def test_la_repartition_proportionnelle_tombe_juste() -> None:
    quotas = repartir({"a": 100, "b": 50, "c": 25}, 70)
    assert sum(quotas.values()) == 70
    assert quotas["a"] == 40 and quotas["b"] == 20 and quotas["c"] == 10


def test_une_cible_superieure_au_volume_garde_tout() -> None:
    entree = [{"id": str(i), "stratum": "s"} for i in range(10)]
    retenus, quotas = echantillonner_stratifie(entree, 100, graine=1)
    assert len(retenus) == 10
    assert quotas == {"s": 10}


def test_chaque_strate_conserve_au_moins_un_message() -> None:
    entree = [{"id": str(i), "stratum": f"s{i % 8}"} for i in range(80)]
    retenus, _ = echantillonner_stratifie(entree, 8, graine=3)
    assert len({r["stratum"] for r in retenus}) == 8
