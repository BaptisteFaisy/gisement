"""R5 - asking for a measure per employee is refused by the gateway, not by a prompt."""

from __future__ import annotations

import pytest

from gisement.politique import RefusPolitique, evaluer, exiger
from gisement.types import Regle, Role
from gisement.types.conformite import OUTIL_CORPUS, OUTIL_MESURE


def test_un_groupement_par_salarie_est_refuse(fabrique_requete, ctx) -> None:
    decision = evaluer(fabrique_requete(groupements=("service", "individu")), ctx)
    assert decision.refusee
    assert Regle.INDIVIDU in decision.regles_violees
    assert "cinq" in decision.motif or "individuelle" in decision.motif


@pytest.mark.parametrize(
    "groupement",
    ["individu", "personne", "salarie", "employe", "pseudonyme", "matricule", "nom", "email"],
)
def test_tous_les_groupements_individuels_sont_refuses(fabrique_requete, ctx, groupement) -> None:
    assert evaluer(fabrique_requete(groupements=(groupement,)), ctx).refusee


@pytest.mark.parametrize(
    "cle,valeur", [("salarie", "Marie Dupont"), ("matricule", "M-2291"), ("email", "m.dupont@demo.example")]
)
def test_un_identifiant_de_personne_est_refuse_en_filtre(fabrique_requete, ctx, cle, valeur) -> None:
    decision = evaluer(fabrique_requete(filtres={"service": "adv", cle: valeur}), ctx)
    assert Regle.FILTRE_PERSONNE in decision.regles_violees


def test_un_groupe_de_quatre_est_supprime_pas_arrondi(fabrique_requete, ctx) -> None:
    decision = evaluer(fabrique_requete(taille_groupe=4, taille_resultat_apres_filtres=4), ctx)
    assert Regle.K5 in decision.regles_violees
    assert decision.seuil_agregation == 5


def test_un_groupe_de_cinq_passe(fabrique_requete, ctx) -> None:
    decision = evaluer(fabrique_requete(taille_groupe=5, taille_resultat_apres_filtres=5), ctx)
    assert decision.autorisee
    assert decision.regles_violees == ()


def test_une_mesure_sans_taille_de_groupe_est_refusee(fabrique_requete, ctx) -> None:
    """Fail closed: omitting the group size is not a way around the rule."""
    decision = evaluer(fabrique_requete(taille_groupe=None), ctx)
    assert decision.refusee
    assert Regle.K5 in decision.regles_violees


def test_une_citation_non_aggregee_est_refusee(fabrique_requete, ctx) -> None:
    assert Regle.CITATION in evaluer(fabrique_requete(citations=True), ctx).regles_violees
    assert Regle.CITATION in evaluer(fabrique_requete(sortie=("citation_non_agregee",)), ctx).regles_violees


def test_un_classement_individuel_en_sortie_est_refuse(fabrique_requete, ctx) -> None:
    for sortie in ("classement_individuel", "score_individuel", "temps_travail_individuel"):
        decision = evaluer(fabrique_requete(sortie=(sortie,)), ctx)
        assert Regle.INDIVIDU in decision.regles_violees, sortie


def test_la_lecture_d_un_corpus_brut_est_refusee(fabrique_requete, ctx) -> None:
    decision = evaluer(fabrique_requete(outil=OUTIL_CORPUS, corpus_id="CORP-BRUT-01"), ctx)
    assert Regle.CORPUS_BRUT in decision.regles_violees
    assert evaluer(fabrique_requete(outil=OUTIL_CORPUS, corpus_id="CORP-0031-tickets"), ctx).autorisee


def test_exiger_leve_une_exception_qui_nomme_la_regle(fabrique_requete, ctx) -> None:
    with pytest.raises(RefusPolitique) as erreur:
        exiger(fabrique_requete(groupements=("salarie",)), ctx)
    assert "regle_individu" in str(erreur.value)
    assert erreur.value.decision.refusee


def test_le_seuil_ne_peut_pas_etre_abaisse_sous_cinq(ctx) -> None:
    """R2 - a client can raise the threshold, never lower it."""
    from dataclasses import replace

    from gisement.politique.regles import seuil_effectif

    assert seuil_effectif(replace(ctx, seuil=2)) == 5
    assert seuil_effectif(replace(ctx, seuil=10)) == 10


def test_une_campagne_sans_validation_dpo_ne_mesure_rien(fabrique_requete, ctx) -> None:
    from dataclasses import replace

    decision = evaluer(fabrique_requete(), replace(ctx, conforme=False))
    assert Regle.CONFORMITE in decision.regles_violees


def test_une_campagne_suspendue_s_arrete_immediatement(fabrique_requete, ctx) -> None:
    from dataclasses import replace

    assert Regle.SUSPENSION in evaluer(fabrique_requete(), replace(ctx, suspendue=True)).regles_violees


def test_un_budget_epuise_arrete_proprement(fabrique_requete, ctx) -> None:
    from dataclasses import replace
    from decimal import Decimal

    decision = evaluer(fabrique_requete(), replace(ctx, budget_restant=Decimal(0)))
    assert Regle.BUDGET in decision.regles_violees


def test_le_role_dpo_est_un_role_de_premier_niveau() -> None:
    """Chapter 7 - the DPO can suspend; the role exists in the contract."""
    assert Role.DPO.value == "dpo"
    assert OUTIL_MESURE == "Mesure__agregat"
