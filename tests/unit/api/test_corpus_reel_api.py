"""The API can serve the REAL corpus, with the same handlers as the demo."""

from __future__ import annotations

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
