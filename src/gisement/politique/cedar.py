"""The Cedar policy deployed as an AgentCore Policy (D-22).

Point 5 of chapter 34 of the spec asked for the **real** syntax of an AgentCore
Policy that refuses on a group size. Confirmed against the AWS documentation and
the `aws_bedrockagentcore` CloudFormation module:

* `AWS::BedrockAgentCore::PolicyEngine` + `AWS::BedrockAgentCore::Policy`, whose
  `PolicyDefinitionProperty` takes a **Cedar** statement
  (`CedarPolicyProperty(statement: str)`);
* `AWS::BedrockAgentCore::Gateway` binds the engine through
  `GatewayPolicyEngineConfigurationProperty(arn, mode)` and runs a **REQUEST
  interceptor** Lambda *before* the target is called, which can short-circuit
  the call with a `transformedGatewayResponse`.

So the declarative part of chapter 18 is Cedar, and what Cedar cannot express
(a person identifier hidden in a filter value, a rare quasi-identifier, the
quota of requests per user) is enforced by `gisement.lambdas.intercepteur`.
Both read the same registry, so they cannot drift.

Cedar is deny-by-default: everything that is not explicitly permitted is
refused, which is exactly the fail-safe default the AWS documentation asks for.
"""

from __future__ import annotations

from gisement.politique.regles import ContextePolitique, seuil_effectif
from gisement.types.conformite import (
    ATTRIBUTS_QUASI_IDENTIFIANTS_RARES,
    FILTRES_PERSONNE,
    GROUPEMENTS_INTERDITS,
    OUTIL_CORPUS,
    OUTIL_EXPORT,
    OUTIL_MESURE,
    SORTIES_INTERDITES,
    Regle,
)

#: The five human roles of chapter 7 allowed to read an aggregated measure.
ROLES_AUTORISES: tuple[str, ...] = (
    "commanditaire",
    "responsable_service",
    "dpo",
    "consultant_msp",
    "responsable_compte",
)

EN_TETE = """// Gisement - AgentCore Policy (Cedar), generated from gisement.politique.regles.
// Do not edit by hand: the registry is the single source of truth.
// Cedar is deny by default - what is not permitted here is refused.
"""

#: Rule -> (the tool it guards, the Cedar `when` clause template).
#: `{seuil}` and `{quota}` are filled from the campaign context.
INTERDICTIONS: tuple[tuple[Regle, str, str], ...] = (
    (Regle.K5, OUTIL_MESURE, '!context.has("taille_groupe") || context.taille_groupe < {seuil}'),
    (Regle.INDIVIDU, OUTIL_MESURE, "context.groupements.containsAny({groupements})"),
    (Regle.CITATION, OUTIL_MESURE, "context.citations == true || context.sortie.containsAny({sorties})"),
    (Regle.FILTRE_PERSONNE, OUTIL_MESURE, "context.filtres.containsAny({filtres_personne})"),
    (Regle.ATTRIBUT_RARE, OUTIL_MESURE, "context.filtres.containsAny({attributs_rares})"),
    (
        Regle.COMBINAISON,
        OUTIL_MESURE,
        "context.nb_filtres >= 3 && context.taille_resultat_apres_filtres < {seuil}",
    ),
    (Regle.CANAL_NON_AUTORISE, OUTIL_MESURE, "!context.canaux_autorises.contains(context.canal)"),
    (Regle.CONFORMITE, "", "context.conforme == false"),
    (Regle.SUSPENSION, "", "context.suspendue == true"),
    (Regle.BUDGET, "", "context.budget_restant <= 0"),
    (Regle.QUOTA_REQUETES, "", "context.requetes_utilisateur > {quota}"),
    (Regle.TENANT, "", "principal.tenant != resource.tenant"),
    (Regle.CORPUS_BRUT, OUTIL_CORPUS, "context.corpus_assaini == false"),
    (Regle.EXPORT, OUTIL_EXPORT, "context.citations == true || context.taille_groupe < {seuil}"),
)


def liste_cedar(valeurs: tuple[str, ...]) -> str:
    """A Cedar set literal."""
    return "[" + ", ".join(f'"{v}"' for v in valeurs) + "]"


def _remplir(modele: str, contexte: ContextePolitique, seuil: int) -> str:
    return modele.format(
        seuil=seuil,
        quota=contexte.quota_requetes,
        groupements=liste_cedar(GROUPEMENTS_INTERDITS),
        sorties=liste_cedar(SORTIES_INTERDITES),
        filtres_personne=liste_cedar(FILTRES_PERSONNE),
        attributs_rares=liste_cedar(ATTRIBUTS_QUASI_IDENTIFIANTS_RARES),
    )


def interdictions_cedar(contexte: ContextePolitique) -> str:
    """Every `forbid` statement, each commented with the rule it enforces."""
    seuil = seuil_effectif(contexte)
    blocs: list[str] = []
    for regle, outil, condition in INTERDICTIONS:
        cible = f'action == Action::"{outil}"' if outil else "action"
        blocs.append(
            f"// {regle.value}\nforbid (principal, {cible}, resource)\n"
            f"  when {{ {_remplir(condition, contexte, seuil)} }};"
        )
    return "\n\n".join(blocs)


def autorisations_cedar(contexte: ContextePolitique) -> str:
    """The only `permit` statements: the five declared roles, on aggregated measures."""
    seuil = seuil_effectif(contexte)
    return "\n\n".join(
        f'permit (principal in Role::"{role}", action == Action::"{OUTIL_MESURE}", resource)\n'
        f"  when {{ context.conforme == true && context.suspendue == false\n"
        f"          && context.taille_groupe >= {seuil} && context.budget_restant > 0 }};"
        for role in ROLES_AUTORISES
    )


def politique_cedar(contexte: ContextePolitique) -> str:
    """The full Cedar statement, ready for `CfnPolicy(definition={"cedar": ...})`."""
    return f"{EN_TETE}\n{interdictions_cedar(contexte)}\n\n{autorisations_cedar(contexte)}\n"


def definition_politique(contexte: ContextePolitique) -> dict:
    """The `PolicyDefinitionProperty` of `AWS::BedrockAgentCore::Policy`."""
    return {"cedar": {"statement": politique_cedar(contexte)}}


def configuration_passerelle(
    lambda_arn: str,
    policy_engine_arn: str,
    role_arn: str,
    discovery_url: str,
    allowed_clients: tuple[str, ...] = (),
    mode: str = "ENFORCE",
) -> dict:
    """The `create_gateway` payload: policy engine + REQUEST interceptor.

    `passRequestHeaders` is true because the tenant is derived from the bearer
    token (EF-71) and never from the tool arguments. The interceptor never logs
    headers, which is the caution the AWS documentation asks for; it logs the
    decision, the rule and the request fingerprint.
    """
    return {
        "name": "gisement-gateway",
        "roleArn": role_arn,
        "protocolType": "MCP",
        "authorizerType": "CUSTOM_JWT",
        "authorizerConfiguration": {
            "customJWTAuthorizer": {
                "discoveryUrl": discovery_url,
                "allowedClients": list(allowed_clients),
            }
        },
        "policyEngineConfiguration": {"arn": policy_engine_arn, "mode": mode},
        "interceptorConfigurations": [
            {
                "interceptor": {"lambda": {"arn": lambda_arn}},
                "interceptionPoints": ["REQUEST"],
                "inputConfiguration": {"passRequestHeaders": True},
            }
        ],
    }


def verifier_cedar(texte: str, contexte: ContextePolitique) -> tuple[str, ...]:
    """Structural checks on the generated Cedar text (a real parser is not ours)."""
    erreurs: list[str] = []
    seuil = str(seuil_effectif(contexte))
    for regle in Regle:
        if f"// {regle.value}" not in texte:
            erreurs.append(f"regle absente du Cedar : {regle.value}")
    if texte.count("forbid") < len(INTERDICTIONS):
        erreurs.append("des interdictions manquent")
    if "permit" not in texte:
        erreurs.append("aucune autorisation : tout serait refuse")
    if f"taille_groupe < {seuil}" not in texte:
        erreurs.append("le seuil k >= 5 n'apparait pas")
    if texte.count("{") != texte.count("}"):
        erreurs.append("accolades non equilibrees")
    return tuple(erreurs)
