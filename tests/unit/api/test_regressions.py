"""The bugs the review found, each one pinned by a test that failed before.

The guarantees at stake: k >= 5 is never lowerable, a tenant never reads or
writes another tenant's campaign, and no request crashes the server.
"""

from __future__ import annotations

import pytest

from gisement.api import handlers
from gisement.api.auth import Identite, meme_tenant, tenant_depuis_jeton
from gisement.types.communs import Role

MSP = Identite(tenant_id="T-DEMO", role=Role.CONSULTANT_MSP, utilisateur="u-consultant_msp")
DPO = Identite(tenant_id="T-DEMO", role=Role.DPO, utilisateur="u-dpo")
RESPONSABLE = Identite(tenant_id="T-DEMO", role=Role.RESPONSABLE_SERVICE, utilisateur="u-resp")
AUTRE = Identite(tenant_id="T-AUTRE", role=Role.CONSULTANT_MSP, utilisateur="u-autre")


@pytest.fixture
def etat() -> handlers.Etat:
    return handlers.Etat.demo()


def _lancee(etat: handlers.Etat) -> None:
    handlers.declarer_conformite(etat, DPO, {})
    handlers.lancer(etat, MSP)


# --------------------------------------------------------------------- k >= 5


def test_le_seuil_ne_peut_pas_etre_abaisse(etat: handlers.Etat) -> None:
    """A client cannot lower the threshold below five: k >= 5 is a floor."""
    statut, reponse = handlers.declarer_conformite(etat, DPO, {"seuil": 1})
    assert statut == 200
    assert reponse["donnees"]["seuil"] == 5
    assert etat.conformite.seuil_agregation == 5


def test_le_seuil_peut_etre_rehausse(etat: handlers.Etat) -> None:
    """A stricter threshold is the client's right."""
    _, reponse = handlers.declarer_conformite(etat, DPO, {"seuil": 12})
    assert reponse["donnees"]["seuil"] == 12


def test_une_mesure_sur_un_tPetit_groupe_est_refusee(etat: handlers.Etat) -> None:
    """The gateway compares to the EFFECTIVE threshold, not the raw one."""
    _lancee(etat)
    for taille in (1, 3, 4):
        statut, reponse = handlers.mesurer(etat, MSP, {"groupements": ["service"], "taille_groupe": taille})
        assert statut == 403, f"taille {taille} acceptee"
        assert "regle_k5" in reponse["regles_violees"]


def test_le_seuil_rehausse_s_applique(etat: handlers.Etat) -> None:
    """A stricter threshold is enforced by the gateway."""
    handlers.declarer_conformite(etat, DPO, {"seuil": 12})
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.mesurer(etat, MSP, {"groupements": ["service"], "taille_groupe": 6})
    assert statut == 403
    assert "regle_k5" in reponse["regles_violees"]


# ------------------------------------------------------------------ isolation


def test_un_autre_tenant_est_refuse(etat: handlers.Etat) -> None:
    """R21 - a client of another tenant reads and writes nothing."""
    assert not meme_tenant(AUTRE, etat.campagne.tenant_id)
    assert meme_tenant(MSP, etat.campagne.tenant_id)


def test_le_jeton_du_demonstration_suit_la_campagne_servie() -> None:
    """The demo tokens belong to the client the server measures."""
    reel = tenant_depuis_jeton("Bearer jeton-demo-msp", "T-KAFKA")
    assert reel is not None and reel.tenant_id == "T-KAFKA"
    autre = tenant_depuis_jeton("Bearer jeton-autre-client", "T-KAFKA")
    assert autre is not None and autre.tenant_id == "T-AUTRE"


def test_un_jeton_inconnu_ne_resout_pas() -> None:
    assert tenant_depuis_jeton("Bearer jeton-bidon") is None
    assert tenant_depuis_jeton(None) is None


# ----------------------------------------------------------- validation 11.3


def test_valider_un_processus_ne_crashe_pas(etat: handlers.Etat) -> None:
    """The measured objects are frozen: the validation replaces them."""
    _lancee(etat)
    processus = etat.resultat.mesures[0].processus.id
    statut, reponse = handlers.valider_processus(etat, processus, "validee", RESPONSABLE)
    assert statut == 200
    assert reponse["donnees"]["validation"] == "validee"


def test_valider_un_processus_inconnu_est_un_404(etat: handlers.Etat) -> None:
    _lancee(etat)
    statut, _ = handlers.valider_processus(etat, "P-99", "validee", RESPONSABLE)
    assert statut == 404


def test_valider_avec_une_decision_inconnue_est_un_400(etat: handlers.Etat) -> None:
    _lancee(etat)
    processus = etat.resultat.mesures[0].processus.id
    statut, _ = handlers.valider_processus(etat, processus, "INCONNUE", RESPONSABLE)
    assert statut == 400


def test_valider_est_reserve_au_responsable_et_au_dpo(etat: handlers.Etat) -> None:
    """11.3 - the service manager validates the volumes; the MSP does not."""
    _lancee(etat)
    processus = etat.resultat.mesures[0].processus.id
    statut, _ = handlers.valider_processus(etat, processus, "validee", MSP)
    assert statut == 403


def test_suspendre_sans_conformite_est_un_409(etat: handlers.Etat) -> None:
    """There is nothing to suspend before a campaign is validated."""
    statut, _ = handlers.suspendre(etat, DPO)
    assert statut == 409


# ------------------------------------------------------------ corpus et demos


def test_le_corpus_reel_annonce_son_client() -> None:
    """The real corpus measures Apache Kafka, not the demo client."""
    reel = handlers.Etat.reel()
    assert reel.campagne.tenant_id == "T-KAFKA"
    assert reel.campagne.client_nom.startswith("Apache Kafka")
    assert reel.corpus == "reel"


def test_la_campagne_courante_annonce_le_corpus_servi() -> None:
    """The header tells the truth about what is on screen."""
    from gisement.api import vues_produits

    reel = handlers.Etat.reel()
    en_tete = vues_produits.campagne_courante(reel.campagne)
    assert en_tete["id"] == "CMP-REEL-0001"
    assert en_tete["tenant"] == "T-KAFKA"
