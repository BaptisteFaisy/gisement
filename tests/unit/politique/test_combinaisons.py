"""R6 - isolating an individual by combining filters (18.4)."""

from __future__ import annotations

import pytest

from gisement.politique import evaluer
from gisement.types import Regle


def test_trois_filtres_qui_isolent_deux_personnes_sont_refuses(fabrique_requete, ctx) -> None:
    decision = evaluer(
        fabrique_requete(
            filtres={"service": "comptabilite", "site": "lyon", "motif": "RESS-01"},
            taille_groupe=2,
            taille_resultat_apres_filtres=2,
        ),
        ctx,
    )
    assert Regle.COMBINAISON in decision.regles_violees
    assert Regle.K5 in decision.regles_violees


def test_trois_filtres_sur_un_groupe_suffisant_passent(fabrique_requete, ctx) -> None:
    decision = evaluer(
        fabrique_requete(
            filtres={"service": "comptabilite", "site": "lyon", "motif": "RESS-01"},
            taille_groupe=40,
            taille_resultat_apres_filtres=40,
        ),
        ctx,
    )
    assert decision.autorisee


def test_deux_filtres_ne_declenchent_pas_la_regle_de_combinaison(fabrique_requete, ctx) -> None:
    decision = evaluer(
        fabrique_requete(
            filtres={"service": "adv", "site": "lyon"},
            taille_groupe=34,
            taille_resultat_apres_filtres=34,
        ),
        ctx,
    )
    assert Regle.COMBINAISON not in decision.regles_violees
    assert decision.autorisee


@pytest.mark.parametrize(
    "attribut", ["langue_parlee", "temps_partiel", "jour_travaille", "poste_telephonique", "adresse_ip"]
)
def test_les_attributs_quasi_identifiants_rares_ne_sont_pas_des_filtres(
    fabrique_requete, ctx, attribut
) -> None:
    """18.4 - a rare attribute is withdrawn from the available filters."""
    decision = evaluer(
        fabrique_requete(
            filtres={"service": "support", attribut: "oui"}, taille_groupe=1, taille_resultat_apres_filtres=1
        ),
        ctx,
    )
    assert Regle.ATTRIBUT_RARE in decision.regles_violees


def test_un_filtre_legitime_n_est_pas_confondu_avec_un_attribut_rare(fabrique_requete, ctx) -> None:
    decision = evaluer(
        fabrique_requete(
            filtres={"service": "support", "langue": "francais"},
            taille_groupe=46,
            taille_resultat_apres_filtres=46,
        ),
        ctx,
    )
    assert Regle.ATTRIBUT_RARE not in decision.regles_violees


def test_le_quota_borne_l_exploration_systematique(fabrique_requete, ctx) -> None:
    """18.4 - bounding and logging requests is what spots a probing attempt."""
    from dataclasses import replace

    assert evaluer(fabrique_requete(requetes_precedentes=200), ctx).autorisee
    decision = evaluer(fabrique_requete(requetes_precedentes=201), ctx)
    assert Regle.QUOTA_REQUETES in decision.regles_violees
    assert (
        Regle.QUOTA_REQUETES
        in evaluer(fabrique_requete(), replace(ctx, requetes_utilisateur=201)).regles_violees
    )


def test_le_compteur_de_requetes_suit_par_utilisateur_et_campagne() -> None:
    from gisement.politique import CompteurRequetes

    compteur = CompteurRequetes(quota=3)
    assert compteur.incrementer("u1", "CMP-0031") == 1
    assert compteur.incrementer("u1", "CMP-0031") == 2
    assert compteur.incrementer("u2", "CMP-0031") == 1
    assert not compteur.depasse("u1", "CMP-0031")
    compteur.incrementer("u1", "CMP-0031")
    compteur.incrementer("u1", "CMP-0031")
    assert compteur.depasse("u1", "CMP-0031")
    assert compteur.nb("u2", "CMP-0031") == 1
