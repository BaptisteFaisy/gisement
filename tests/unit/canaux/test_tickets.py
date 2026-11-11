"""Lot 4 - the tickets collector: measured durations, stable fingerprints."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path

from gisement.canaux import tickets
from gisement.types import Canal, StatutDuree


def test_le_volume_du_canal_est_annonce(corpus: Path) -> None:
    assert tickets.mesurer_volume(tickets.source_fichiers(corpus)) == 4800


def test_les_tickets_deviennent_des_activites_measurees(corpus: Path, parametres) -> None:
    activites, rapport = tickets.collecter(tickets.source_fichiers(corpus), parametres)
    assert len(activites) == 4800
    assert rapport["volume_entree"] == rapport["volume_sortie"] == 4800
    assert rapport["exclus"] == 0
    assert all(a.canal == Canal.TICKETS for a in activites)
    assert all(a.duree_statut == StatutDuree.MESUREE for a in activites)
    assert all(a.duree_mesuree_minutes is not None for a in activites)


def test_la_collecte_est_idempotente(corpus: Path, parametres) -> None:
    """EF-10 - the same source gives the same activities, in the same order."""
    premier, _ = tickets.collecter(tickets.source_fichiers(corpus), parametres)
    second, _ = tickets.collecter(tickets.source_fichiers(corpus), parametres)
    assert [a.id for a in premier] == [a.id for a in second]
    assert [a.signature for a in premier] == [a.signature for a in second]


def test_les_empreintes_regroupent_les_activites(corpus: Path, parametres) -> None:
    """21.2 - the deterministic fingerprint is what holds the budget."""
    activites, _ = tickets.collecter(tickets.source_fichiers(corpus), parametres)
    groupes = Counter(a.signature for a in activites)
    assert len(groupes) < 30
    assert len(activites) / len(groupes) > 50


def test_aucun_identifiant_de_personne_ne_survit(corpus: Path, parametres) -> None:
    """R9 - the pseudonymisation happens at ingestion, before anything else."""
    activites, rapport = tickets.collecter(tickets.source_fichiers(corpus), parametres)
    assert rapport["pseudonymes_appliques"] > 0
    for activite in activites[:500]:
        assert "Marie" not in activite.texte
        assert "@demo.example" not in activite.texte
        assert activite.groupe_pseudonyme.startswith(("ADV", "COMPTA", "APPRO", "SUPPORT"))


def test_la_couverture_du_canal_est_un_ratio(corpus: Path, parametres) -> None:
    activites, _ = tickets.collecter(tickets.source_fichiers(corpus), parametres)
    ratio = tickets.couverture(activites, Decimal("1000"))
    assert Decimal(0) < ratio <= Decimal(1)
    assert tickets.couverture(activites, Decimal(0)) == Decimal(0)


def test_l_adaptateur_itsm_normalise_un_ticket_vendeur() -> None:
    """The real adapter maps a vendor ticket onto the frozen schema."""
    from gisement.canaux.tickets.source import SourceItsm

    normalise = SourceItsm.normaliser(
        {
            "key": "SUP-12",
            "created": "2026-06-01T10:00:00",
            "team": "support",
            "assignee": "Marie Dupont",
            "summary": "Relancer le devis",
            "status": "clos",
        }
    )
    assert normalise["id"] == "SUP-12"
    assert normalise["sujet"] == "Relancer le devis"
    assert normalise["agent"] == "Marie Dupont"
    assert normalise["statut"] == "clos"


def test_une_source_vide_ne_casse_rien(tmp_path: Path, parametres) -> None:
    vide = tmp_path / "tickets" / "tickets.jsonl"
    vide.parent.mkdir(parents=True)
    vide.write_text("", encoding="utf-8")
    activites, rapport = tickets.collecter(tickets.source_fichiers(tmp_path), parametres)
    assert activites == ()
    assert rapport["volume_entree"] == 0
