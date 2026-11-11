"""Lots 13 - the decision tree of the five automation types (chapter 14)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.faisabilite import (
    est_automatisable,
    evaluer_faisabilite,
    evaluer_risque,
    type_automatisation,
)
from gisement.types import FaitsFaisabilite, Processus, Risque, StatutValidation, TypeAutomatisation
from tests.fakes.builders import faits_depuis_spec, processus_depuis_spec, processus_verite

BASE = {
    "id": "P-TEST",
    "campagne_id": "CMP-DEMO",
    "nom": "test",
    "service": "adv",
    "validation": StatutValidation.EN_ATTENTE,
}


def processus(**kw) -> Processus:
    return Processus(**{**BASE, **kw})


def test_l_arbre_de_decision_du_14_3():
    """14.3 - A first, then B, C, D, and E with a reason."""
    assert type_automatisation(FaitsFaisabilite(etape_supprimable_amont=True))[0] == TypeAutomatisation.A
    assert type_automatisation(FaitsFaisabilite(api_ou_flux_natif=True))[0] == TypeAutomatisation.B
    assert (
        type_automatisation(FaitsFaisabilite(travail_deterministe=True, interface_stable=True))[0]
        == TypeAutomatisation.C
    )
    assert type_automatisation(FaitsFaisabilite(jugement_requis=True))[0] == TypeAutomatisation.D
    assert type_automatisation(FaitsFaisabilite())[0] == TypeAutomatisation.E


def test_le_type_A_passe_avant_les_autres():
    """14.2 - the deliberate bias: removing the step is tested first."""
    faits = FaitsFaisabilite(
        etape_supprimable_amont=True,
        api_ou_flux_natif=True,
        travail_deterministe=True,
        interface_stable=True,
        jugement_requis=True,
    )
    retenu, trace = type_automatisation(faits)
    assert retenu == TypeAutomatisation.A
    assert any("amont" in ligne for ligne in trace)


def test_un_interface_instable_ne_donne_pas_un_agent_navigateur():
    faits = FaitsFaisabilite(travail_deterministe=True, interface_stable=False, jugement_requis=True)
    assert type_automatisation(faits)[0] == TypeAutomatisation.D


def test_chaque_decision_est_tracee():
    """EF-41 - the decision is explainable, not a black box."""
    processus_test = processus(changements_douze_mois=3)
    faits = FaitsFaisabilite(
        api_ou_flux_natif=True, donnee_sensible=True, dependance_externe_non_contractuelle=True
    )
    faisabilite = evaluer_faisabilite(processus_test, faits)
    assert faisabilite.type == TypeAutomatisation.B
    assert faisabilite.api_existe and not faisabilite.interface_stable
    assert any("sensible" in m for m in faisabilite.motifs_decision)
    assert any("dependance" in m for m in faisabilite.motifs_decision)
    assert any("mouvant" in m for m in faisabilite.motifs_decision)


def test_les_trois_niveaux_de_risque():
    assert evaluer_risque(FaitsFaisabilite(jugement_requis=True)) == Risque.ELEVE
    assert evaluer_risque(FaitsFaisabilite(obligation_legale_humaine=True)) == Risque.ELEVE
    assert evaluer_risque(FaitsFaisabilite(donnee_sensible=True)) == Risque.ELEVE
    assert evaluer_risque(FaitsFaisabilite(dependance_externe_non_contractuelle=True)) == Risque.MOYEN
    assert evaluer_risque(FaitsFaisabilite(api_ou_flux_natif=True, interface_stable=False)) == Risque.MOYEN
    assert evaluer_risque(FaitsFaisabilite(api_ou_flux_natif=True), changements=2) == Risque.MOYEN
    assert evaluer_risque(FaitsFaisabilite(api_ou_flux_natif=True, interface_stable=True)) == Risque.FAIBLE


def test_est_automatisable_exclut_la_categorie_E():
    assert est_automatisable(evaluer_faisabilite(processus(), FaitsFaisabilite(api_ou_flux_natif=True)))
    assert not est_automatisable(evaluer_faisabilite(processus(), FaitsFaisabilite()))


@pytest.mark.parametrize("spec", processus_verite(), ids=[p["id"] for p in processus_verite()])
def test_l_arbre_reproduit_le_type_attendu_des_23_processus(spec):
    """R13 and the ground truth: the tree gives the expected type on all 23."""
    faisabilite = evaluer_faisabilite(processus_depuis_spec(spec), faits_depuis_spec(spec))
    assert faisabilite.type.value == spec["type_arbre_attendu"], spec["id"]
    assert faisabilite.jugement_requis == spec["faits"].get("jugement_requis", False)


def test_le_processus_a_fort_jugement_n_est_jamais_de_type_A_ou_B():
    """R13 - P-02, 55 % of atypical cases, must not look easy."""
    spec = next(p for p in processus_verite() if p["id"] == "P-02")
    faisabilite = evaluer_faisabilite(processus_depuis_spec(spec), faits_depuis_spec(spec))
    assert faisabilite.type in (TypeAutomatisation.D, TypeAutomatisation.E)
    assert evaluer_risque(faits_depuis_spec(spec), Decimal(spec["part_atypique"])) == Risque.ELEVE
