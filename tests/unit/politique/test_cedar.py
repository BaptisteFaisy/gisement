"""D-22 - the AgentCore Policy is a real Cedar statement, generated from the registry."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.politique.cedar import (
    ROLES_AUTORISES,
    configuration_passerelle,
    definition_politique,
    politique_cedar,
    verifier_cedar,
)
from gisement.politique.regles import ContextePolitique
from gisement.types.conformite import (
    ATTRIBUTS_QUASI_IDENTIFIANTS_RARES,
    FILTRES_PERSONNE,
    GROUPEMENTS_INTERDITS,
    Regle,
)

CTX = ContextePolitique(
    campagne_id="CMP-0031",
    tenant_id="T-DEMO",
    conforme=True,
    suspendue=False,
    budget_restant=Decimal("12.50"),
    quota_requetes=200,
)


@pytest.fixture
def cedar() -> str:
    return politique_cedar(CTX)


def test_le_cedar_est_structurellement_valide(cedar: str) -> None:
    assert verifier_cedar(cedar, CTX) == ()
    assert cedar.count("{") == cedar.count("}")
    assert cedar.startswith("//")


def test_chaque_regle_du_registre_a_son_interdiction(cedar: str) -> None:
    for regle in Regle:
        assert f"// {regle.value}" in cedar, regle.value


def test_le_seuil_k5_est_ecrit_dans_le_cedar(cedar: str) -> None:
    """R2 - the threshold is in the deployed policy, not in a prompt."""
    assert "context.taille_groupe < 5" in cedar
    assert '!context.has("taille_groupe")' in cedar


def test_les_groupements_interdits_sont_dans_le_cedar(cedar: str) -> None:
    for groupement in GROUPEMENTS_INTERDITS:
        assert f'"{groupement}"' in cedar, groupement
    for filtre in FILTRES_PERSONNE:
        assert f'"{filtre}"' in cedar, filtre
    for attribut in ATTRIBUTS_QUASI_IDENTIFIANTS_RARES:
        assert f'"{attribut}"' in cedar, attribut


def test_cedar_interdit_par_defaut_et_n_autorise_que_les_cinq_roles(cedar: str) -> None:
    assert cedar.count("forbid (") == 14
    assert cedar.count("permit (") == len(ROLES_AUTORISES)
    for role in ROLES_AUTORISES:
        assert f'Role::"{role}"' in cedar


def test_le_seuil_du_contexte_est_reporte_dans_le_cedar() -> None:
    from dataclasses import replace

    texte = politique_cedar(replace(CTX, seuil=10))
    assert "context.taille_groupe < 10" in texte
    assert "context.taille_groupe >= 10" in texte


def test_la_definition_est_au_format_cloudformation() -> None:
    definition = definition_politique(CTX)
    assert set(definition) == {"cedar"}
    assert "statement" in definition["cedar"]
    assert definition["cedar"]["statement"].count("forbid (") == 14


def test_la_configuration_de_la_passerelle_est_celle_de_la_doc_aws() -> None:
    """The gateway payload matches the documented create_gateway shape."""
    config = configuration_passerelle(
        lambda_arn="arn:aws:lambda:eu-west-3:123456789012:function:gisement-intercepteur",
        policy_engine_arn="arn:aws:bedrock-agentcore:eu-west-3:123456789012:policy-engine/pe-1",
        role_arn="arn:aws:iam::123456789012:role/gisement-gateway",
        discovery_url="https://cognito-idp.eu-west-3.amazonaws.com/eu-west-3_x/.well-known/openid-configuration",
        allowed_clients=("client-id",),
    )
    assert config["protocolType"] == "MCP"
    assert config["authorizerType"] == "CUSTOM_JWT"
    assert config["policyEngineConfiguration"]["mode"] == "ENFORCE"
    intercepteur = config["interceptorConfigurations"][0]
    assert intercepteur["interceptionPoints"] == ["REQUEST"]
    assert intercepteur["interceptor"]["lambda"]["arn"].endswith("gisement-intercepteur")
    # the tenant comes from the bearer token, so headers must reach the interceptor
    assert intercepteur["inputConfiguration"]["passRequestHeaders"] is True
