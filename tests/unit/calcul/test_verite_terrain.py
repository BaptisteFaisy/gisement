"""The 23 processes of the demo client, cross-checked against the ground truth.

`demo/spec-processus.json` carries the expected outputs, computed by an
independent implementation of annex A (lot 0). This test is the proof that the
engine and that implementation agree to the cent on every field - spec 27:
"100 % d'accord (le calcul est déterministe)".
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.calcul import (
    calculer,
    calculer_portefeuille,
    entree_depuis_spec,
    entrees_depuis_verite,
    gisement_total,
)
from tests.fakes.builders import identifiants_verite, processus_verite

CHAMPS_HEURES = (
    "temps_brut_heures",
    "temps_fragmente_heures",
    "temps_transfere_heures",
    "temps_ineliminable_heures",
    "temps_net_heures",
)
CHAMPS_EUROS = (
    "gain_mensuel",
    "gain_annuel",
    "gain_naif_mensuel",
    "ecart_naif",
    "delai_retour_mois",
    "gain_trois_ans",
)
CHAMPS_COUT = ("developpement", "outil_annuel", "maintenance_annuelle", "annee_1", "recurrent")


@pytest.mark.parametrize("spec", processus_verite(), ids=identifiants_verite())
def test_le_moteur_reproduit_la_verite_terrain(spec: dict) -> None:
    g = calculer(entree_depuis_spec(spec))
    attendu = spec["attendu"]
    for champ in CHAMPS_HEURES + CHAMPS_EUROS:
        valeur = getattr(g, champ)
        if attendu[champ] is None:
            assert valeur is None, f"{spec['id']}.{champ}"
        else:
            assert valeur == Decimal(attendu[champ]), f"{spec['id']}.{champ}: {valeur} != {attendu[champ]}"
    for champ in CHAMPS_COUT:
        assert getattr(g.cout, champ) == Decimal(attendu["cout"][champ]), f"{spec['id']}.cout.{champ}"
    assert g.coefficient_fragmentation == Decimal(attendu["coefficient_fragmentation"])


@pytest.mark.parametrize("spec", processus_verite(), ids=identifiants_verite())
def test_chaque_gisement_publie_un_intervalle(spec: dict) -> None:
    """EF-31 - no published figure is a single number."""
    g = calculer(entree_depuis_spec(spec))
    assert g.temps_net_intervalle.bas <= g.temps_net_heures <= g.temps_net_intervalle.haut
    assert g.temps_net_intervalle.largeur > 0
    assert g.gain_mensuel_intervalle is not None


def test_le_portefeuille_complet_et_son_gisement_net() -> None:
    entrees = entrees_depuis_verite()
    assert len(entrees) == 23
    gisements = calculer_portefeuille(entrees)
    assert len(gisements) == 23
    actionable = [
        g for g, spec in zip(gisements, processus_verite(), strict=True) if spec["type_final_attendu"] != "E"
    ]
    total = gisement_total(actionable)
    assert Decimal("78000") <= total <= Decimal("104000"), f"annex E: {total}"


def test_le_cas_de_reference_du_jeu_de_demo_est_l_action_A() -> None:
    spec = next(p for p in processus_verite() if p["id"] == "P-07")
    g = calculer(entree_depuis_spec(spec))
    assert g.gain_mensuel == Decimal("1102.50")
    assert g.delai_retour_mois == Decimal("1.8")
    assert g.cout.annee_1 == Decimal("1950.00")


def test_le_facteur_naif_moyen_du_portefeuille_est_superieur_a_deux() -> None:
    """KPI-4 - across the portfolio, the naive calculation is roughly twice as乐观."""
    facteurs = [
        calculer(entree_depuis_spec(s)).ecart_naif for s in processus_verite() if s["attendu"]["ecart_naif"]
    ]
    assert facteurs
    moyenne = sum(facteurs, Decimal(0)) / Decimal(len(facteurs))
    assert moyenne > Decimal(2)
