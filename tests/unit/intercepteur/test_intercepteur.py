"""R5 on the real AWS mechanism: the AgentCore Gateway REQUEST interceptor.

The interceptor is the enforcement point documented by AWS ("Types of
interceptors": a REQUEST interceptor runs before the gateway calls the target
and can short-circuit it with a `transformedGatewayResponse`). These tests
prove that the refusal of an individual measure happens there, with the very
same rule registry the offline policy uses.
"""

from __future__ import annotations

import base64
import json

import pytest

from gisement.lambdas import intercepteur
from gisement.types.campagne import Conformite
from gisement.types.communs import Canal

CONFORME = Conformite(
    campagne_id="CMP-0031",
    finalite="mesure des processus de travail",
    canaux_autorises=tuple(Canal),
    validation_dpo=True,
    validation_cse=True,
)


def campagne_stockee(campagne_id: str):
    """What DynamoDB would return: the campaign with its own tenant."""
    from datetime import date

    from gisement.types.campagne import Campagne, Perimetre

    if campagne_id != "CMP-0031":
        return None
    return Campagne(
        id="CMP-0031",
        tenant_id="T-DEMO",
        graine=20261111,
        conformite=CONFORME,
        perimetre=Perimetre(
            services=("adv",),
            sites=("lyon",),
            fenetre_debut=date(2026, 5, 1),
            fenetre_fin=date(2026, 11, 1),
            canaux_autorises=tuple(Canal),
        ),
    )


def evenement_mcp(arguments: dict, identifiant: int = 7, outil: str = "Mesure__agregat") -> dict:
    return {
        "interceptorInputVersion": "1.0",
        "mcp": {
            "gatewayRequest": {
                "path": "/mcp",
                "httpMethod": "POST",
                "body": {
                    "jsonrpc": "2.0",
                    "id": identifiant,
                    "method": "tools/call",
                    "params": {"name": outil, "arguments": arguments},
                },
            }
        },
    }


@pytest.fixture
def campagne_validee():
    """Install the campaign loader: CMP-0031 exists and the DPO validated it."""
    intercepteur.definir_chargeur_campagne(campagne_stockee)
    yield
    intercepteur.definir_chargeur_campagne(None)


def test_une_mesure_par_individu_est_refusee_avant_la_cible(campagne_validee) -> None:
    """R5 - the gateway answers, the tool is never called."""
    rep = intercepteur.handler(
        evenement_mcp(
            {
                "campagne_id": "CMP-0031",
                "tenant_id": "T-DEMO",
                "canal": "tickets",
                "groupements": ["service", "individu"],
                "taille_groupe": 1,
                "taille_resultat_apres_filtres": 1,
            }
        )
    )
    assert rep["interceptorOutputVersion"] == "1.0"
    reponse = rep["mcp"]["transformedGatewayResponse"]
    assert reponse["statusCode"] == 403
    regles = reponse["body"]["error"]["data"]["regles_violees"]
    assert "regle_individu" in regles
    assert "regle_k5" in regles
    assert reponse["body"]["error"]["data"]["seuil_agregation"] == 5


def test_une_mesure_agregee_passe_sans_court_circuit(campagne_validee) -> None:
    rep = intercepteur.handler(
        evenement_mcp(
            {
                "campagne_id": "CMP-0031",
                "tenant_id": "T-DEMO",
                "canal": "tickets",
                "groupements": ["service", "motif"],
                "taille_groupe": 34,
                "taille_resultat_apres_filtres": 34,
            }
        )
    )
    assert rep == {"interceptorOutputVersion": "1.0", "mcp": {}}


def test_sans_validation_dpo_tout_est_refuse() -> None:
    """Fail-safe default: no loader installed means nothing is validated."""
    intercepteur.definir_chargeur_campagne(None)
    rep = intercepteur.handler(
        evenement_mcp(
            {
                "campagne_id": "CMP-0031",
                "tenant_id": "T-DEMO",
                "canal": "tickets",
                "groupements": ["service"],
                "taille_groupe": 34,
            }
        )
    )
    assert rep["mcp"]["transformedGatewayResponse"]["statusCode"] == 403
    assert (
        "regle_conformite"
        in rep["mcp"]["transformedGatewayResponse"]["body"]["error"]["data"]["regles_violees"]
    )


def test_une_campagne_inconnue_est_refusee(campagne_validee) -> None:
    rep = intercepteur.handler(
        evenement_mcp(
            {
                "campagne_id": "CMP-INCONNUE",
                "tenant_id": "T-DEMO",
                "groupements": ["service"],
                "taille_groupe": 34,
            }
        )
    )
    assert rep["mcp"]["transformedGatewayResponse"]["statusCode"] == 403


def test_la_cible_http_refuse_en_base64(campagne_validee) -> None:
    """HTTP targets carry a base64 body and get a base64 refusal."""
    corps = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "Mesure__agregat",
                "arguments": {
                    "campagne_id": "CMP-0031",
                    "tenant_id": "T-DEMO",
                    "groupements": ["salarie"],
                    "taille_groupe": 1,
                },
            },
        }
    ).encode()
    evenement = {
        "interceptorInputVersion": "1.0",
        "http": {
            "gatewayRequest": {
                "path": "/mesure/invocations",
                "httpMethod": "POST",
                "body": base64.b64encode(corps).decode(),
            }
        },
    }
    rep = intercepteur.handler(evenement)
    sortie = rep["http"]["transformedGatewayResponse"]
    assert sortie["statusCode"] == 403
    assert sortie["contentType"] == "application/json"
    decode = json.loads(base64.b64decode(sortie["body"]).decode("utf-8"))
    assert "regle_individu" in decode["error"]["data"]["regles_violees"]


def test_une_charge_utilisable_illegible_est_refusee() -> None:
    """An unparsable payload is refused, never passed through."""
    for evenement in (
        {},
        {"inattendu": True},
        {"mcp": {}},
        {"mcp": {"gatewayRequest": None}},
    ):
        rep = intercepteur.handler(evenement)
        assert rep["interceptorOutputVersion"] == "1.0"
        assert rep["mcp"]["transformedGatewayResponse"]["statusCode"] == 403


def test_chaque_decision_est_journalisee(campagne_validee) -> None:
    """Best practice from the AWS docs: log authorization decisions."""
    avant = len(intercepteur.JOURNAL.entrees())
    intercepteur.handler(
        evenement_mcp(
            {
                "campagne_id": "CMP-0031",
                "tenant_id": "T-DEMO",
                "groupements": ["individu"],
                "taille_groupe": 1,
            }
        )
    )
    assert len(intercepteur.JOURNAL.entrees()) == avant + 1
    derniere = intercepteur.JOURNAL.entrees()[-1]
    assert derniere.autorise is False


def test_le_tenant_vient_du_jeton_quand_il_y_en_a_un(campagne_validee) -> None:
    """EF-71 - a bearer token wins over any tenant written in the arguments."""
    evenement = evenement_mcp(
        {
            "campagne_id": "CMP-0031",
            "tenant_id": "T-DEMO",
            "groupements": ["service"],
            "taille_groupe": 34,
            "taille_resultat_apres_filtres": 34,
        }
    )
    evenement["mcp"]["gatewayRequest"]["headers"] = {"Authorization": "Bearer jeton-autre-client"}
    rep = intercepteur.handler(evenement)
    # the campaign belongs to T-DEMO; a T-AUTRE token cannot read it (EF-71, R21)
    sortie = rep["mcp"]["transformedGatewayResponse"]
    assert sortie["statusCode"] == 403
    assert "regle_tenant" in sortie["body"]["error"]["data"]["regles_violees"]
