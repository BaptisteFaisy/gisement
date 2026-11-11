"""Shared fixtures: the reference case of annex A, used by many lots."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.types import (
    ComposanteTransfert,
    CoutAutomatisation,
    FaitsFaisabilite,
    OccurrencesMensuelles,
    Repartition,
    StatutDuree,
)
from gisement.types.economie import EntreeGisement

#: The reference case of annex A: "saisie des commandes fournisseurs recues
#: par courriel". 320 occurrences per month, 9 minutes each, 42 EUR per hour.
CAS_REFERENCE_ID = "P-07"


@pytest.fixture
def cas_reference() -> EntreeGisement:
    return EntreeGisement(
        processus_id=CAS_REFERENCE_ID,
        occurrences=OccurrencesMensuelles(
            serie=(Decimal(210), Decimal(300), Decimal(320), Decimal(340), Decimal(465), Decimal(280)),
            mediane=Decimal("320"),
            minimum=Decimal("210"),
            maximum=Decimal("465"),
            ecart_type=Decimal("42"),
            nb_mois=6,
        ),
        duree_unitaire_minutes=Decimal("9"),
        duree_statut=StatutDuree.MESUREE,
        duree_ecart_minutes=Decimal("1.8"),
        duree_nb_cas=1840,
        repartition=Repartition.SEMI_REGROUPEE,
        part_atypique=Decimal("0.15"),
        part_atypique_nb_cas=1840,
        transfert=(
            ComposanteTransfert("revue", taux=Decimal("0.20"), duree_minutes=Decimal("1.5")),
            ComposanteTransfert("rejets", taux=Decimal("0.05"), duree_minutes=Decimal("12")),
            ComposanteTransfert("supervision", forfait_heures=Decimal("3.2")),
        ),
        taux_horaire=Decimal("42"),
        cout=CoutAutomatisation(
            jours=Decimal("12"),
            tjm=Decimal("650"),
            abonnement_mensuel=Decimal("180"),
            taux_maintenance=Decimal("0.08"),
        ),
        faits=FaitsFaisabilite(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True),
        graine=20261111,
    )
