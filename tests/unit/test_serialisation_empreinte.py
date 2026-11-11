"""Lot 0 - serialisation and fingerprint helpers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from gisement.empreinte import empreinte, normaliser, signature, verbe
from gisement.serialisation import depuis_dict, json_deterministe, vers_json
from gisement.serialisation import empreinte as empreinte_json
from gisement.types import (
    Campagne,
    Canal,
    ComposanteTransfert,
    DecompositionCout,
    Gisement,
    Intervalle,
    OccurrencesMensuelles,
    Perimetre,
    Repartition,
    StatutDuree,
)

PERIMETRE = Perimetre(
    services=("adv",),
    sites=("lyon",),
    fenetre_debut=date(2026, 5, 1),
    fenetre_fin=date(2026, 11, 1),
    canaux_autorises=(Canal.COURRIELS,),
    volume_travail_estime_heures=Decimal("1000"),
)


def test_un_decimal_ne_devient_jamais_un_flottant():
    """ENF-13 - a float never crosses a boundary, not even in JSON."""
    assert vers_json(Decimal("772.80")) == "772.80"
    assert '"772.80"' in json_deterministe({"gain": Decimal("772.80")})


def test_les_enumerations_et_les_dates_sont_serialisees():
    assert vers_json(Canal.TICKETS) == "tickets"
    assert vers_json(date(2026, 11, 11)) == "2026-11-11"
    assert vers_json(datetime(2026, 11, 11, 8, 30)) == "2026-11-11T08:30:00"


def test_json_deterministe_est_stable():
    objet = {"b": 1, "a": [Decimal("2.5"), Canal.APPELS]}
    assert json_deterministe(objet) == json_deterministe({"a": [Decimal("2.5"), "appels"], "b": 1})


def test_aller_retour_sur_une_campagne():
    campagne = Campagne(id="CMP-0031", tenant_id="T-DEMO", perimetre=PERIMETRE, graine=20261111)
    brut = vers_json(campagne)
    reconstruite = depuis_dict(Campagne, brut)
    assert reconstruite.id == campagne.id
    assert reconstruite.perimetre.fenetre_debut == date(2026, 5, 1)
    assert reconstruite.perimetre.canaux_autorises == [Canal.COURRIELS]
    assert reconstruite.perimetre.volume_travail_estime_heures == Decimal("1000")


def test_aller_retour_sur_un_gisement():
    gisement = Gisement(
        processus_id="P-07",
        temps_brut_heures=Decimal("48.0"),
        coefficient_fragmentation=Decimal("0.70"),
        temps_fragmente_heures=Decimal("33.6"),
        temps_transfere_heures=Decimal("8.0"),
        detail_transfert=(("revue", Decimal("1.6")), ("rejets", Decimal("3.2"))),
        temps_ineliminable_heures=Decimal("7.2"),
        temps_net_heures=Decimal("18.4"),
        temps_net_intervalle=Intervalle(bas=Decimal("14.8"), haut=Decimal("22.1")),
        cout=DecompositionCout(),
        taux_horaire=Decimal("42"),
        gain_mensuel=Decimal("772.80"),
        ecart_naif=Decimal("2.61"),
    )
    reconstruit = depuis_dict(Gisement, vers_json(gisement))
    assert reconstruit.temps_net_heures == Decimal("18.4")
    assert reconstruit.temps_net_intervalle.bas == Decimal("14.8")
    assert reconstruit.ecart_naif == Decimal("2.61")


def test_entrees_de_calcul_serialisables():
    occurrences = OccurrencesMensuelles(mediane=Decimal("320"), nb_mois=6)
    transfert = (ComposanteTransfert("revue", taux=Decimal("0.2"), duree_minutes=Decimal("1.5")),)
    donnees = vers_json(
        {"occurrences": occurrences, "transfert": transfert, "repartition": Repartition.DIFFUSE}
    )
    assert donnees["occurrences"]["mediane"] == "320"
    assert donnees["repartition"] == "diffuse"
    assert depuis_dict(ComposanteTransfert, donnees["transfert"][0]).heures(Decimal(320)) == Decimal("1.6")
    assert StatutDuree.MESUREE.value == "mesuree"


def test_empreinte_deterministe_et_stable():
    assert normaliser("Saisie  des COMMANDES-fournisseurs !") == "saisie des commandes fournisseurs"
    assert verbe("Recopier la commande du courriel vers l'ERP") == "recopier"
    sig = signature("Recopier la commande fournisseur dans l'ERP", ("ERP", "Messagerie"))
    assert sig.startswith("recopier::")
    assert "erp" in sig and "messagerie" in sig
    assert empreinte(sig) == empreinte(sig)
    assert len(empreinte(sig)) == 16


def test_deux_activites_semblables_partagent_leur_empreinte():
    """21.2 - grouping without a model is what holds the budget."""
    a = signature("Recopier la commande fournisseur dans l'ERP", ("ERP",))
    b = signature("recopier une commande fournisseur dans l erp", ("ERP",))
    c = signature("Relancer le devis sans reponse", ("CRM",))
    assert empreinte(a) == empreinte(b)
    assert empreinte(a) != empreinte(c)


def test_empreinte_json_stable_pour_le_registre():
    assert empreinte_json({"qui": "dpo", "quoi": "validation"}) == empreinte_json(
        {"quoi": "validation", "qui": "dpo"}
    )
