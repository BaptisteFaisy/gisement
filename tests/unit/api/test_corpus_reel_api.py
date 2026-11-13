"""The API can serve the REAL corpus, with the same handlers as the demo."""

from __future__ import annotations

from gisement.api import handlers, vues_produits
from gisement.api.auth import Identite
from gisement.api.serveur import choisir_corpus
from gisement.types.communs import Role


def _msp() -> Identite:
    return Identite(tenant_id="T-KAFKA", role=Role.CONSULTANT_MSP, utilisateur="u-msp")


def _dpo() -> Identite:
    return Identite(tenant_id="T-KAFKA", role=Role.DPO, utilisateur="u-dpo")


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


def test_le_corpus_reel_a_son_client() -> None:
    reel = choisir_corpus("reel")
    assert reel.campagne.tenant_id == "T-KAFKA"
    assert reel.campagne.client_nom.startswith("Apache Kafka")


def test_le_plan_ne_mentionne_pas_les_projets_de_la_demo() -> None:
    """The plan announces only the projects the campaign really holds."""
    from gisement.api import vues_mesure

    reel = choisir_corpus("reel")
    handlers.declarer_conformite(reel, _dpo(), {})
    handlers.lancer(reel, _msp())
    statut, reponse = vues_mesure.plan_projet(reel.resultat)
    assert statut == 200
    projet_ids = {p.processus_id for p in reel.resultat.portefeuille.projets}
    for dependance in reponse["donnees"]["dependances"]:
        assert dependance["projet"] in projet_ids
