"""The API can serve the REAL corpus, with the same handlers as the demo."""

from __future__ import annotations

from gisement.api import vues_produits
from gisement.api.serveur import choisir_corpus


def test_le_serveur_peut_servir_le_corpus_reel() -> None:
    """`gisement serve --corpus reel` mesure le vrai corpus, memes handlers."""
    reel = choisir_corpus("reel")
    assert reel.campagne.id == "CMP-REEL-0001"
    assert reel.racine.name == "donnees"
    assert reel.declaration.name == "declaration.json"
    assert reel.objets_max == 2, "l'empreinte reelle est calibree, pas celle de la demo"


def test_le_serveur_demo_ne_change_pas() -> None:
    assert choisir_corpus("demo").campagne.id == "CMP-0031"


def test_l_entete_annonce_la_campagne_du_corpus_serti() -> None:
    """The header must not announce the demo campaign on the real corpus."""
    reel = choisir_corpus("reel")
    en_tete = vues_produits.campagne_courante(reel.campagne)
    assert en_tete["id"] == "CMP-REEL-0001"
    assert en_tete["tenant"] == "T-KAFKA"
