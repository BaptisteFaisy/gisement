"""R21 / EF-70 / EF-71 - tenant isolation, derived from the token, never from text."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from gisement.politique import contexte, evaluer
from gisement.types import (
    Campagne,
    Canal,
    Conformite,
    CoutCampagne,
    Perimetre,
    Regle,
    Role,
    StatutCampagne,
)
from gisement.types.conformite import RequeteMesure

PERIMETRE = Perimetre(
    services=("adv",),
    sites=("lyon",),
    fenetre_debut=date(2026, 5, 1),
    fenetre_fin=date(2026, 11, 1),
    canaux_autorises=(Canal.TICKETS, Canal.COURRIELS),
)


def campagne(tenant: str, suspendue: bool = False, valide: bool = True) -> Campagne:
    return Campagne(
        id="CMP-0031",
        tenant_id=tenant,
        perimetre=PERIMETRE,
        graine=20261111,
        statut=StatutCampagne.SUSPENDUE if suspendue else StatutCampagne.EN_COURS,
        conformite=Conformite(
            campagne_id="CMP-0031",
            finalite="mesure des processus",
            canaux_autorises=(Canal.TICKETS, Canal.COURRIELS),
            validation_dpo=valide,
            validation_cse=valide,
            suspension=suspendue,
        ),
        cout=CoutCampagne(total_usd=Decimal("4.00"), budget_plafond_usd=Decimal("20.00")),
    )


def requete(tenant: str) -> RequeteMesure:
    return RequeteMesure(
        outil="Mesure__agregat",
        tenant_id=tenant,
        utilisateur="u-01",
        role=Role.CONSULTANT_MSP,
        campagne_id="CMP-0031",
        canal=Canal.TICKETS,
        groupements=("service",),
        taille_groupe=34,
    )


def test_le_contexte_vient_de_la_campagne_pas_de_la_requete() -> None:
    ctx = contexte(campagne("T-DEMO"))
    assert ctx.tenant_id == "T-DEMO"
    assert ctx.conforme is True
    assert ctx.suspendue is False
    assert ctx.canaux_autorises == ("tickets", "courriels")
    assert ctx.budget_restant == Decimal("16.00")
    assert ctx.seuil == 5


def test_un_client_ne_peut_pas_lire_les_donnees_d_un_autre() -> None:
    ctx = contexte(campagne("T-DEMO"))
    decision = evaluer(requete("T-AUTRE"), ctx)
    assert decision.refusee
    assert Regle.TENANT in decision.regles_violees


def test_le_meme_tenant_passe() -> None:
    assert evaluer(requete("T-DEMO"), contexte(campagne("T-DEMO"))).autorisee


def test_une_suspension_bloque_tout(fabrique_requete) -> None:
    ctx = contexte(campagne("T-DEMO", suspendue=True))
    assert ctx.suspendue is True
    assert Regle.SUSPENSION in evaluer(fabrique_requete(), ctx).regles_violees


def test_l_absence_de_validation_dpo_bloque_l_ingestion() -> None:
    ctx = contexte(campagne("T-DEMO", valide=False))
    assert ctx.conforme is False
    assert campagne("T-DEMO", valide=False).peut_ingerer() is False


def test_un_canal_hors_perimetre_est_refuse() -> None:
    ctx = contexte(campagne("T-DEMO"))
    decision = evaluer(replace(requete("T-DEMO"), canal=Canal.APPELS), ctx)
    assert Regle.CANAL_NON_AUTORISE in decision.regles_violees
