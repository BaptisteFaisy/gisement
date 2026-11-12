"""Idea #5 - the catalogue is alive: proposals, validation, emergence."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from gisement.motif_banque import (
    emergentes,
    fusionner,
    propositions,
    valider,
)
from gisement.motifs import charger_catalogue
from gisement.types.communs import Canal
from gisement.types.mesure import Motif, OccurrencesMensuelles


def motif(nouveau: bool, mediane: str = "40", confiance: str = "0.30", nom: str = "Saisir X") -> Motif:
    return Motif(
        id=f"M-{nom}",
        campagne_id="CMP-0031",
        nom=nom,
        catalogue_ref="" if nouveau else "RESS-01",
        confiance=Decimal(confiance),
        occurrences=OccurrencesMensuelles(mediane=Decimal(mediane), nb_mois=6),
        canaux=(Canal.TICKETS,),
        nouveau=nouveau,
        proposition_catalogue='{"indices": {"systemes": ["erp"]}}' if nouveau else "",
    )


def test_un_motif_nouveau_devient_une_proposition() -> None:
    liste = propositions([motif(True, "40"), motif(False), motif(True, "90")])
    assert len(liste) == 2
    assert liste[0].occurrences == 90, "les plus riches d'abord"
    assert liste[0].ref_proposee == "PROP-01"
    assert liste[0].systemes == ("erp",)
    assert liste[0].a_valider is True


def test_un_motif_confiant_n_est_pas_a_valider() -> None:
    liste = propositions([motif(True, confiance="0.95")], seuil_confiance=Decimal("0.70"))
    assert liste[0].a_valider is False


def test_valider_ecrit_le_motif_en_donnees(tmp_path: Path) -> None:
    """R25 - adding a motif is a data change, not a release."""
    proposition = propositions([motif(True, "40", nom="Saisir les releves")])[0]
    ref = valider(proposition, tmp_path)
    fichier = tmp_path / "motifs" / "a_classer.json"
    assert fichier.exists()
    contenu = json.loads(fichier.read_text(encoding="utf-8"))
    assert contenu[0]["ref"] == ref
    assert contenu[0]["nom"] == "Saisir les releves"
    assert contenu[0]["indices"]["systemes"] == ["erp"]


def test_valider_refuse_une_reference_en_double(tmp_path: Path) -> None:
    proposition = propositions([motif(True)])[0]
    valider(proposition, tmp_path)
    with pytest.raises(ValueError, match="existe deja"):
        valider(proposition, tmp_path)


def test_le_motif_valide_est_reconnu_sans_code(tmp_path: Path) -> None:
    proposition = propositions([motif(True, nom="Pointer les palettes")])[0]
    valider(proposition, tmp_path)
    catalogue = charger_catalogue(tmp_path)
    assert catalogue.par_ref(proposition.ref_proposee).nom == "Pointer les palettes"


def test_fusionner_ajoute_tout_le_lot(tmp_path: Path) -> None:
    liste = propositions([motif(True, "10", nom="A"), motif(True, "20", nom="B")])
    assert fusionner(liste, tmp_path) == 2
    assert len(json.loads((tmp_path / "motifs" / "a_classer.json").read_text(encoding="utf-8"))) == 2


def test_un_motif_qui_apparait_est_emergent() -> None:
    liste = emergentes({"RESS-01": 100}, {"RESS-01": 120, "REPO-09": 45})
    assert len(liste) == 1
    assert liste[0].ref == "REPO-09"
    assert "nouveau motif apparu" in liste[0].recommandation


def test_une_hausse_de_volume_est_signalee() -> None:
    liste = emergentes({"RESS-01": 100}, {"RESS-01": 145})
    assert liste[0].variation == Decimal("45.0")
    assert "hausse" in liste[0].recommandation


def test_une_baisse_de_volume_est_signalee() -> None:
    liste = emergentes({"RESS-01": 100}, {"RESS-01": 60})
    assert liste[0].variation == Decimal("-40.0")
    assert "baisse" in liste[0].recommandation


def test_une_variation_faible_ne_bouge_pas() -> None:
    assert emergentes({"RESS-01": 100}, {"RESS-01": 110}) == ()
    assert emergentes({}, {}) == ()
