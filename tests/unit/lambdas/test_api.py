"""Lot 22 - the Lambda router: same handlers, API Gateway plumbing, no AWS.

Nothing here talks to AWS or to the network: the tests call `router` and
`handler` directly on synthetic proxy events, and reset the module singleton
between tests so each one starts from a fresh demo campaign.
"""

from __future__ import annotations

import json

import pytest

from gisement.lambdas import api

JETON_MSP = "jeton-demo-msp"
JETON_DPO = "jeton-demo-dpo"


@pytest.fixture(autouse=True)
def campagne_neuve():
    """A fresh campaign per test: the container singleton is reset around it."""
    api.reinitialiser()
    yield
    api.reinitialiser()


def _evenement(
    methode: str,
    chemin: str,
    *,
    jeton: str | None = JETON_MSP,
    corps: dict | None = None,
    langue: str | None = None,
    ressource: str | None = None,
) -> dict:
    """A minimal API Gateway proxy event."""
    entetes = {} if jeton is None else {"Authorization": f"Bearer {jeton}"}
    parametres = {} if langue is None else {"langue": langue}
    return {
        "httpMethod": methode,
        "resource": ressource if ressource is not None else f"/api{chemin}",
        "path": f"/api{chemin}",
        "headers": entetes,
        "queryStringParameters": parametres or None,
        "body": "" if corps is None else json.dumps(corps),
        "isBase64Encoded": False,
    }


def _valider_et_lancer() -> None:
    """The EF-04 prelude: the DPO validates, then the measure runs."""
    statut, _ = api.router(_evenement("POST", "/campagnes/courante/conformite", jeton=JETON_DPO))
    assert statut == 200
    statut, _ = api.router(_evenement("POST", "/campagnes/courante/lancer", jeton=JETON_DPO))
    assert statut == 200


def test_health_repond_en_ligne() -> None:
    statut, corps = api.router(_evenement("GET", "/health"))
    assert statut == 200
    assert corps["donnees"]["statut"] == "en_ligne"


def test_le_parcours_conformite_mesure_projets() -> None:
    """The demo story end to end, through the proxy events only."""
    _valider_et_lancer()
    statut, corps = api.router(_evenement("GET", "/projets"))
    assert statut == 200
    assert corps["donnees"]["vague1_existe"] is True


def test_lancer_sans_validation_est_refuse() -> None:
    """R1 / EF-04 - the handler itself refuses, before any ingestion."""
    statut, corps = api.router(_evenement("POST", "/campagnes/courante/lancer"))
    assert statut == 409
    assert corps["bouton_grise"] is True


def test_une_mesure_individuelle_est_refusee() -> None:
    """R5 - the gateway refuses and names the rule."""
    _valider_et_lancer()
    statut, corps = api.router(
        _evenement(
            "POST",
            "/mesure",
            corps={
                "canal": "tickets",
                "groupements": ["service", "individu"],
                "taille_groupe": 1,
                "taille_resultat_apres_filtres": 1,
            },
        )
    )
    assert statut == 403
    assert "regle_individu" in corps["regles_violees"]


def test_une_mesure_agregee_passe() -> None:
    _valider_et_lancer()
    statut, corps = api.router(
        _evenement(
            "POST",
            "/mesure",
            corps={
                "canal": "tickets",
                "groupements": ["service", "motif"],
                "taille_groupe": 34,
                "taille_resultat_apres_filtres": 34,
            },
        )
    )
    assert statut == 200
    assert corps["donnees"]["seuil_applique"] == 5


def test_sans_jeton_la_reponse_est_403() -> None:
    statut, corps = api.router(_evenement("GET", "/projets", jeton=None))
    assert statut == 403
    assert corps == {"ok": False, "erreur": "jeton absent ou inconnu"}


def test_un_jeton_inconnu_est_refuse() -> None:
    statut, corps = api.router(_evenement("GET", "/projets", jeton="jeton-inexistant"))
    assert statut == 403
    assert corps["erreur"] == "jeton absent ou inconnu"


def test_le_tenant_vient_du_jeton_pas_des_parametres() -> None:
    """EF-71 / R21 - a tenant in the query string is simply ignored."""
    _valider_et_lancer()
    evenement = _evenement("GET", "/projets")
    evenement["queryStringParameters"] = {"tenant_id": "T-AUTRE", "langue": "fr"}
    statut, corps = api.router(evenement)
    assert statut == 200
    assert corps["donnees"]["vague1_existe"] is True


def test_une_route_inconnue_repond_404() -> None:
    statut, corps = api.router(_evenement("GET", "/inexistant"))
    assert statut == 404
    assert corps["ok"] is False
    assert "route inconnue" in corps["erreur"]
    assert "/api/inexistant" in corps["erreur"]


def test_le_modele_de_ressource_avec_accolades_utilise_le_chemin() -> None:
    """A real proxy event carries `/{proxy+}` as resource: `path` decides."""
    _valider_et_lancer()
    statut, corps = api.router(_evenement("GET", "/gisements/P-07", ressource="/api/{proxy+}"))
    assert statut == 200
    assert corps["donnees"]["processus_id"] == "P-07"


def test_handler_rend_la_forme_proxy_api_gateway() -> None:
    reponse = api.handler(_evenement("GET", "/health"))
    assert reponse["statusCode"] == 200
    assert reponse["headers"] == {"Content-Type": "application/json"}
    assert reponse["isBase64Encoded"] is False
    corps = json.loads(reponse["body"])
    assert corps["ok"] is True
    assert corps["donnees"]["statut"] == "en_ligne"


def test_handler_repond_en_json_meme_sur_une_route_inconnue() -> None:
    reponse = api.handler(_evenement("GET", "/inexistant"))
    assert reponse["statusCode"] == 404
    assert json.loads(reponse["body"])["ok"] is False


def test_un_corps_vide_ne_casse_pas_le_post() -> None:
    """An empty body reads as `{}` - the handler answers, it does not crash."""
    evenement = _evenement("POST", "/campagnes/courante/conformite", jeton=JETON_DPO)
    evenement["body"] = None
    statut, _ = api.router(evenement)
    assert statut == 200


def test_le_singleton_est_partage_entre_les_appels() -> None:
    """One campaign per container: the validation of call one is seen by call two."""
    api.router(_evenement("POST", "/campagnes/courante/conformite", jeton=JETON_DPO))
    statut, corps = api.router(_evenement("GET", "/health"))
    assert statut == 200
    assert corps["donnees"]["conformite_validee"] is True
