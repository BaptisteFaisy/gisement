"""Annex A.7 - the type A action: remove the step instead of automating it."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from gisement.calcul import calculer
from gisement.types import CoutAutomatisation, EntreeGisement


def variante_a(cas_reference: EntreeGisement) -> EntreeGisement:
    """78 % of the supplier orders move to the existing, unused EDI portal."""
    return replace(
        cas_reference,
        part_volume_traitee=Decimal("0.78125"),
        suppression_etape=True,
        cout=CoutAutomatisation(
            jours=Decimal(3), tjm=Decimal(650), abonnement_mensuel=Decimal(0), taux_maintenance=Decimal(0)
        ),
    )


def test_annexe_a7_le_gain_de_l_action_A(cas_reference: EntreeGisement) -> None:
    g = calculer(variante_a(cas_reference))
    assert g.temps_net_heures == Decimal("26.3")
    assert g.gain_mensuel == Decimal("1102.50")
    assert g.gain_annuel == Decimal("13230.00")


def test_annexe_a7_aucun_transfert_ni_ine_liminable(cas_reference: EntreeGisement) -> None:
    """D-11 - a suppressed step has no automated output left to review."""
    g = calculer(variante_a(cas_reference))
    assert g.temps_transfere_heures == Decimal("0.0")
    assert g.temps_ineliminable_heures == Decimal("0.0")
    assert g.detail_transfert == ()


def test_annexe_a7_le_retour_sur_investissement(cas_reference: EntreeGisement) -> None:
    g = calculer(variante_a(cas_reference))
    assert g.cout.annee_1 == Decimal("1950.00")
    assert g.delai_retour_mois == Decimal("1.8")
    assert g.ecart_naif == Decimal("1.43")


def test_l_action_A_est_plus_rentable_que_l_automatisation_B(cas_reference: EntreeGisement) -> None:
    """14.2 - the whole point of recommending A first."""
    a = calculer(variante_a(cas_reference))
    b = calculer(cas_reference)
    assert a.gain_mensuel > b.gain_mensuel
    assert a.cout.annee_1 < b.cout.annee_1
    assert a.delai_retour_mois < b.delai_retour_mois
