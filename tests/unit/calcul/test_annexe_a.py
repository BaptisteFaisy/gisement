"""R2 / R3 - the reference case of annex A, to the cent."""

from __future__ import annotations

from decimal import Decimal

from gisement.calcul import calculer
from gisement.types import EntreeGisement, TypeAutomatisation  # noqa: F401  (contract import check)


def test_annexe_a3_les_quatre_corrections(cas_reference: EntreeGisement) -> None:
    g = calculer(cas_reference)
    assert g.temps_brut_heures == Decimal("48.0")
    assert g.coefficient_fragmentation == Decimal("0.70")
    assert g.temps_fragmente_heures == Decimal("33.6")
    assert g.temps_transfere_heures == Decimal("8.0")
    assert g.temps_ineliminable_heures == Decimal("7.2")
    assert g.temps_net_heures == Decimal("18.4")


def test_annexe_a3_le_detail_du_transfert_est_publie(cas_reference: EntreeGisement) -> None:
    """A CFO must be able to check the three components line by line."""
    detail = dict(calculer(cas_reference).detail_transfert)
    assert detail["revue"] == Decimal("1.6000")
    assert detail["rejets"] == Decimal("3.2000")
    assert detail["supervision"] == Decimal("3.2000")


def test_annexe_a4_les_gains_et_le_cout(cas_reference: EntreeGisement) -> None:
    g = calculer(cas_reference)
    assert g.gain_mensuel == Decimal("772.80")
    assert g.gain_annuel == Decimal("9273.60")
    assert g.cout.developpement == Decimal("7800.00")
    assert g.cout.outil_annuel == Decimal("2160.00")
    assert g.cout.maintenance_annuelle == Decimal("624.00")
    assert g.cout.annee_1 == Decimal("10584.00")
    assert g.cout.recurrent == Decimal("2784.00")
    assert g.delai_retour_mois == Decimal("13.7")
    assert g.gain_trois_ans == Decimal("11668.80")


def test_annexe_a5_l_ecart_au_calcul_naif(cas_reference: EntreeGisement) -> None:
    """KPI-4 - the factor that makes the tool believable."""
    g = calculer(cas_reference)
    assert g.gain_naif_mensuel == Decimal("2016.00")
    assert g.ecart_naif == Decimal("2.61")
    assert g.delai_retour_naif_mois == Decimal("5.2")
    assert g.delai_retour_mois > g.delai_retour_naif_mois


def test_sans_taux_horaire_le_moteur_publie_des_heures_pas_des_euros(cas_reference) -> None:
    """13.4 - publishing euros on an invented rate is the gravest fault."""
    from dataclasses import replace

    g = calculer(replace(cas_reference, taux_horaire=None))
    assert g.temps_net_heures == Decimal("18.4")
    assert g.gain_mensuel is None
    assert g.gain_annuel is None
    assert g.ecart_naif is None
    assert g.delai_retour_mois is None
    assert g.taux_horaire is None
