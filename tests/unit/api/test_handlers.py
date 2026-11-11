"""Lot 18 - the portal handlers: R1, R5, R20, R21 on the demo campaign."""

from __future__ import annotations

import pytest

from gisement.api import handlers
from gisement.api.auth import Identite
from gisement.types.communs import Role

MSP = Identite(tenant_id="T-DEMO", role=Role.CONSULTANT_MSP, utilisateur="u-consultant_msp")
DPO = Identite(tenant_id="T-DEMO", role=Role.DPO, utilisateur="u-dpo")
AUTRE = Identite(tenant_id="T-AUTRE", role=Role.CONSULTANT_MSP, utilisateur="u-autre")


@pytest.fixture
def etat() -> handlers.Etat:
    return handlers.Etat.demo()


def _valider(etat: handlers.Etat) -> None:
    statut, _ = handlers.declarer_conformite(etat, DPO, {})
    assert statut == 200


def test_r1_la_mesure_est_refusee_sans_validation(etat: handlers.Etat) -> None:
    """EF-04 - no ingestion without a recorded DPO validation."""
    statut, reponse = handlers.lancer(etat, MSP)
    assert statut == 409
    assert reponse["bouton_grise"] is True
    assert "validation" in reponse["erreur"].lower()


def test_la_mesure_demarre_apres_validation(etat: handlers.Etat) -> None:
    _valider(etat)
    statut, reponse = handlers.lancer(etat, MSP)
    assert statut == 200
    assert reponse["donnees"]["statut"] == "terminee"
    statut, detail = handlers.campagnes_detail(etat)
    assert statut == 200
    assert detail["donnees"]["activites"] > 1000
    assert detail["donnees"]["groupes"] < 100


def test_r5_une_mesure_par_salarie_est_refusee(etat: handlers.Etat) -> None:
    """The gateway refuses before the tool, naming the rule (R5)."""
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.mesurer(
        etat,
        MSP,
        {
            "canal": "tickets",
            "groupements": ["service", "individu"],
            "taille_groupe": 1,
            "taille_resultat_apres_filtres": 1,
        },
    )
    assert statut == 403
    assert "regle_individu" in reponse["regles_violees"]
    assert reponse["seuil_agregation"] == 5


def test_une_mesure_agregee_passe(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.mesurer(
        etat,
        MSP,
        {
            "canal": "tickets",
            "groupements": ["service", "motif"],
            "taille_groupe": 34,
            "taille_resultat_apres_filtres": 34,
            "filtres": {"service": "adv"},
        },
    )
    assert statut == 200
    assert reponse["donnees"]["seuil_applique"] == 5


def test_r21_le_tenant_vient_du_jeton(etat: handlers.Etat) -> None:
    """EF-71 - no route accepts a tenant; the token decides."""
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.mesurer(
        etat,
        AUTRE,
        {
            "canal": "tickets",
            "groupements": ["service", "individu"],
            "taille_groupe": 1,
        },
    )
    assert statut == 403
    assert "regle_individu" in reponse["regles_violees"]


def test_r20_la_suspension_est_reservee_au_dpo(etat: handlers.Etat) -> None:
    _valider(etat)
    statut, _ = handlers.suspendre(etat, MSP)
    assert statut == 403
    statut, reponse = handlers.suspendre(etat, DPO)
    assert statut == 200
    assert reponse["donnees"]["suspendue"] is True
    assert reponse["donnees"]["etat_conserve"] is True


def test_une_campagne_suspendue_refuse_la_mesure(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    handlers.suspendre(etat, DPO)
    statut, reponse = handlers.mesurer(
        etat,
        MSP,
        {
            "canal": "tickets",
            "groupements": ["service"],
            "taille_groupe": 34,
        },
    )
    assert statut == 403
    assert "regle_suspension" in reponse["regles_violees"]


def test_le_portefeuille_est_publie(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.projets(etat)
    assert statut == 200
    donnees = reponse["donnees"]
    assert donnees["vague1_existe"] is True
    assert any(p["vague"] == "vague_1" for p in donnees["projets"])
    assert any(p["vague"] == "vague_3" for p in donnees["projets"])


def test_les_processus_a_ne_pas_automatiser_sont_publies(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.deconseilles(etat)
    assert statut == 200
    assert len(reponse["donnees"]) == 6
    assert all(d["condition_reexamen"] for d in reponse["donnees"])


def test_le_gisement_publie_son_intervalle(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.gisement_detail(etat, "P-07")
    assert statut == 200
    donnees = reponse["donnees"]
    assert float(donnees["intervalle"][0]) <= float(donnees["temps_net"]) <= float(donnees["intervalle"][1])
    assert float(donnees["ecart_naif"]) > 1


def test_le_cout_est_mesure(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.budget(etat)
    assert statut == 200
    total = float(reponse["donnees"]["cout_mesure_usd"])
    assert 0 < total < 30
    assert float(reponse["donnees"]["ecart_a_l_estimation"]) < 0.25


def test_le_rapport_et_le_registre_sont_publies(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, reponse = handlers.rapport(etat, "fr")
    assert statut == 200
    assert "62 %" in reponse["donnees"]["rapport"]
    statut, reponse = handlers.rapport(etat, "en")
    assert "62%" in reponse["donnees"]["rapport"]
    statut, reponse = handlers.registre(etat, "fr")
    assert statut == 200
    assert "Seuil d'agregation" in reponse["donnees"]["registre"]


def test_une_route_inconnue_est_refusee(etat: handlers.Etat) -> None:
    _valider(etat)
    handlers.lancer(etat, MSP)
    statut, _ = handlers.gisement_detail(etat, "P-99")
    assert statut == 404
