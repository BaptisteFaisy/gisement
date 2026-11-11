"""Lot 0 - the frozen contracts must hold before anything is built on them."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gisement.types import (
    COEFFICIENTS_FRAGMENTATION,
    SEUIL_AGGREGATION_DEFAUT,
    Campagne,
    Canal,
    ComposanteTransfert,
    Conformite,
    CoutAutomatisation,
    OccurrencesMensuelles,
    Perimetre,
    Repartition,
    StatutCampagne,
    TauxHoraires,
    Tenant,
    arrondi,
    decimal,
    euros,
    facteur,
    heures,
)

PERIMETRE = Perimetre(
    services=("approvisionnements", "adv", "comptabilite", "support"),
    sites=("lyon",),
    fenetre_debut=date(2026, 5, 1),
    fenetre_fin=date(2026, 11, 1),
    canaux_autorises=(Canal.TICKETS, Canal.COURRIELS, Canal.JOURNAUX),
    volume_travail_estime_heures=Decimal("1000"),
)


def test_seuil_agregation_est_cinq():
    """R2 - the hard threshold is five individuals, never four."""
    assert SEUIL_AGGREGATION_DEFAUT == 5


def test_coefficients_fragmentation_du_chapitre_13():
    assert COEFFICIENTS_FRAGMENTATION[Repartition.REGROUPEE] == Decimal("0.90")
    assert COEFFICIENTS_FRAGMENTATION[Repartition.SEMI_REGROUPEE] == Decimal("0.70")
    assert COEFFICIENTS_FRAGMENTATION[Repartition.DIFFUSE] == Decimal("0.45")
    assert COEFFICIENTS_FRAGMENTATION[Repartition.INTERRUPTIVE] == Decimal("0.85")


def test_arrondis():
    assert arrondi(Decimal("2.345"), 2) == Decimal("2.35")
    assert euros(Decimal("772.7999")) == Decimal("772.80")
    assert heures(Decimal("18.44")) == Decimal("18.4")
    assert facteur(Decimal("2.6087")) == Decimal("2.61")


def test_decimal_ne_passe_jamais_par_un_flottant_binaire():
    assert decimal(0.1) == Decimal("0.1")
    assert decimal(9) == Decimal("9")


def test_annexe_a3_les_trois_composantes_du_transfert():
    """Annex A.3: 1.6 h of review + 3.2 h of rejects + 3.2 h of supervision."""
    occurrences = Decimal("320")
    revue = ComposanteTransfert("revue", taux=Decimal("0.20"), duree_minutes=Decimal("1.5"))
    rejets = ComposanteTransfert("rejets", taux=Decimal("0.05"), duree_minutes=Decimal("12"))
    supervision = ComposanteTransfert("supervision", forfait_heures=Decimal("3.2"))
    total = revue.heures(occurrences) + rejets.heures(occurrences) + supervision.heures(occurrences)
    assert revue.heures(occurrences) == Decimal("1.6")
    assert rejets.heures(occurrences) == Decimal("3.2")
    assert total == Decimal("8.0")


def test_annexe_a4_cout_de_automatisation():
    cout = CoutAutomatisation(
        jours=Decimal("12"),
        tjm=Decimal("650"),
        abonnement_mensuel=Decimal("180"),
        taux_maintenance=Decimal("0.08"),
    )
    assert cout.developpement() == Decimal("7800")
    assert cout.developpement() * cout.taux_maintenance == Decimal("624.00")
    assert cout.abonnement_mensuel * 12 == Decimal("2160")


def test_amplitude_saisonnieres():
    """13.1 correction 4 - the seasonal amplitude is published, not hidden."""
    serie = OccurrencesMensuelles(
        serie=tuple(Decimal(x) for x in (210, 300, 320, 340, 465, 280)),
        mediane=Decimal("320"),
        minimum=Decimal("210"),
        maximum=Decimal("465"),
        ecart_type=Decimal("42"),
        nb_mois=6,
    )
    assert serie.amplitude == pytest.approx(Decimal("0.796875"))


def test_conformite_exige_les_deux_validations():
    """EF-02 / EF-04 - the DPO and the staff representatives, not suspended."""
    base = Conformite(campagne_id="CMP-0031", finalite="mesure", canaux_autorises=(Canal.TICKETS,))
    assert not base.est_valide()
    dpo = Conformite(
        campagne_id="CMP-0031",
        finalite="mesure",
        canaux_autorises=(Canal.TICKETS,),
        validation_dpo=True,
        validation_cse=True,
    )
    assert dpo.est_valide()
    suspendue = Conformite(
        campagne_id="CMP-0031",
        finalite="mesure",
        canaux_autorises=(Canal.TICKETS,),
        validation_dpo=True,
        validation_cse=True,
        suspension=True,
    )
    assert not suspendue.est_valide()


def test_une_campagne_sans_conformite_ne_peut_pas_ingerer():
    tenant = Tenant(
        id="T-DEMO",
        nom_client="Demo Distribution SAS",
        effectif=120,
        taux_horaires=TauxHoraires(fournis=True, par_famille={"administratif": Decimal("42")}),
    )
    campagne = Campagne(id="CMP-0031", tenant_id=tenant.id, perimetre=PERIMETRE, graine=20261111)
    assert campagne.statut == StatutCampagne.BROUILLON
    assert not campagne.peut_ingerer()
    assert tenant.taux_horaires.taux("administratif") == Decimal("42")
    assert campagne.perimetre.nb_mois() == 6


def test_un_taux_horaire_non_fourni_interdit_les_euros():
    """13.4 - publishing euros on an invented rate is the gravest fault."""
    taux = TauxHoraires(fournis=False)
    assert taux.taux("administratif") is None
