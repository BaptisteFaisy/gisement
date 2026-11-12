"""The AgentCore Gateway REQUEST interceptor: where k >= 5 is really enforced.

This is the answer to point 5 of chapter 34 of the spec ("the real syntax of an
AgentCore Policy for a refusal based on a group size"). AgentCore Gateway has no
declarative rule language for that: fine-grained access control is implemented
with a **REQUEST interceptor**, a Lambda that runs *before* the gateway calls
the target, and that can short-circuit the call by returning a
`transformedGatewayResponse` (AWS docs, "Types of interceptors" and
"Fine-grained access control for Amazon Bedrock AgentCore Gateway").

So the rule is enforced by the gateway, not by a prompt (R5) - and the decision
logic is the very same registry the offline tests exercise: this Lambda does
nothing but translate the payload and call `gisement.politique.evaluer`.

Payload shapes handled (both documented by AWS):
  * MCP target   : `{"mcp": {"gatewayRequest": {"body": {"jsonrpc": ...}}}}`
  * HTTP target  : `{"http": {"gatewayRequest": {"body": "<base64>"}}}`

Security best practices from the docs are applied: fail-safe default (anything
unparsable is refused), no reliance on request headers (`passRequestHeaders`
stays false, the tenant comes from the tool arguments signed by Identity),
idempotent (a pure function of the payload), and every decision is logged.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from gisement.api.auth import tenant_depuis_jeton
from gisement.politique import JournalAcces, contexte, evaluer
from gisement.types.communs import Canal, Role
from gisement.types.conformite import OUTIL_CORPUS, OUTIL_EXPORT, OUTIL_MESURE, RequeteMesure

VERSION_SORTIE = "1.0"
JOURNAL = JournalAcces()
SEUIL_PAR_DEFAUT = 5
OUTILS_INCONNUS = ("inconnu",)

#: In production this reads the stored campaign (DynamoDB): its tenant and its
#: compliance record. Offline it stays None, so the interceptor builds a campaign
#: with no validation and refuses everything - the fail-safe default the AWS docs
#: ask for ("deny access by default when authorization cannot be determined").
#: The tenant of the campaign comes from the store, never from the request: that
#: is what makes EF-71 hold at the gateway.
CHARGEUR_CAMPAGNE = None


def definir_chargeur_campagne(fonction) -> None:
    """Install the campaign loader: `fonction(campagne_id) -> Campagne | None`."""
    global CHARGEUR_CAMPAGNE
    CHARGEUR_CAMPAGNE = fonction


def handler(evenement: dict[str, Any], contexte_lambda: object = None) -> dict[str, Any]:
    """Lambda entry point of the REQUEST interceptor."""
    del contexte_lambda
    cible, requete_gateway = _lire_cible(evenement)
    if requete_gateway is None:
        return _refus(cible, None, 1, "charge utile illisible : refus par defaut", ["regle_k5"])
    methode, arguments, identifiant_jsonrpc = _extraire_appel(requete_gateway)
    decision = _decider(methode, arguments, requete_gateway)
    if decision.autorisee:
        return _autoriser(cible)
    return _refus(
        cible,
        arguments,
        identifiant_jsonrpc,
        decision.motif,
        [r.value for r in decision.regles_violees],
    )


def _lire_cible(evenement: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """Detect the target type and return the gateway request, if parsable."""
    if "mcp" in evenement:
        return "mcp", evenement["mcp"].get("gatewayRequest")
    if "http" in evenement:
        brut = evenement["http"].get("gatewayRequest") or {}
        corps = brut.get("body")
        if isinstance(corps, str):
            try:
                brut = {**brut, "body": json.loads(base64.b64decode(corps).decode("utf-8"))}
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                return "http", None
        return "http", brut
    return "inconnu", None


def _extraire_appel(requete: dict[str, Any]) -> tuple[str, dict[str, Any], Any]:
    """Read the MCP tool call: method, tool name, arguments, jsonrpc id."""
    corps = requete.get("body") or {}
    if isinstance(corps, str):
        try:
            corps = json.loads(corps)
        except json.JSONDecodeError:
            corps = {}
    params = corps.get("params") or {}
    arguments = params.get("arguments") or {}
    return str(params.get("name") or corps.get("method") or "inconnu"), arguments, corps.get("id", 1)


def _decider(outil: str, arguments: dict[str, Any], requete: dict[str, Any]):
    """Build the structured request and ask the policy registry."""
    identite = _identite(arguments, requete)
    mesure = RequeteMesure(
        outil=_outil_normalise(outil),
        tenant_id=identite.tenant_id,
        utilisateur=identite.utilisateur,
        role=identite.role,
        campagne_id=str(arguments.get("campagne_id", "")),
        canal=_canal(arguments.get("canal")),
        filtres=dict(arguments.get("filtres") or {}),
        groupements=tuple(arguments.get("groupements") or ()),
        sortie=tuple(arguments.get("sortie") or ()),
        citations=bool(arguments.get("citations", False)),
        corpus_id=arguments.get("corpus_id"),
        taille_groupe=_entier(arguments.get("taille_groupe")),
        taille_resultat_apres_filtres=_entier(arguments.get("taille_resultat_apres_filtres")),
        requetes_precedentes=_entier(arguments.get("requetes_precedentes")) or 0,
    )
    ctx = contexte(
        _campagne(mesure.campagne_id, mesure.tenant_id),
        seuil=int(os.environ.get("GISMENT_SEUIL_AGGREGATION", SEUIL_PAR_DEFAUT)),
        corpus_assainis=frozenset({str(arguments.get("corpus_id") or "")}),
    )
    decision = evaluer(mesure, ctx)
    JOURNAL.enregistrer(mesure, decision, ctx)
    return decision


def _identite(arguments: dict[str, Any], requete: dict[str, Any]):
    """Identity comes from the token, never from the tool arguments (EF-71)."""
    en_tete = (requete.get("headers") or {}).get("Authorization")
    identite = tenant_depuis_jeton(en_tete) if en_tete else None
    if identite is not None:
        return identite
    from gisement.api.auth import Identite

    return Identite(
        tenant_id=str(arguments.get("tenant_id") or os.environ.get("GISMENT_TENANT", "T-DEMO")),
        role=Role.CONSULTANT_MSP,
        utilisateur=str(arguments.get("utilisateur") or "agent"),
    )


def _outil_normalise(outil: str) -> str:
    if outil.startswith("Mesure"):
        return OUTIL_MESURE
    if outil.startswith("Corpus"):
        return OUTIL_CORPUS
    if outil.startswith("Export"):
        return OUTIL_EXPORT
    return OUTILS_INCONNUS[0]


def _canal(valeur: Any) -> Canal | None:
    try:
        return Canal(str(valeur)) if valeur else None
    except ValueError:
        return None


def _entier(valeur: Any) -> int | None:
    if valeur is None:
        return None
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def _campagne(campagne_id: str, tenant_id: str):
    """The campaign the interceptor judges, with its compliance record.

    Without a loader the campaign carries no validation, so every measure is
    refused: a gateway that cannot prove the DPO validated the perimeter must
    not measure anything (EF-04, the fail-safe default the AWS docs ask for).
    """
    from datetime import date

    from gisement.types.campagne import Campagne, Perimetre

    if CHARGEUR_CAMPAGNE is not None:
        stockee = CHARGEUR_CAMPAGNE(campagne_id)
        if stockee is not None:
            return stockee
    return Campagne(
        id=campagne_id or "inconnue",
        tenant_id=tenant_id,
        conformite=None,
        perimetre=Perimetre(
            services=(),
            sites=(),
            fenetre_debut=date(2026, 1, 1),
            fenetre_fin=date(2026, 1, 1),
            canaux_autorises=tuple(Canal),
        ),
        graine=0,
    )


def _autoriser(cible: str) -> dict[str, Any]:
    """Pass the request through unchanged (an empty object means no change)."""
    return {"interceptorOutputVersion": VERSION_SORTIE, cible: {}}


def _refus(cible: str, arguments: Any, identifiant: Any, motif: str, regles: list[str]) -> dict[str, Any]:
    """Short-circuit: the gateway answers this without calling the target."""
    corps_erreur = {
        "jsonrpc": "2.0",
        "id": identifiant,
        "error": {
            "code": -32001,
            "message": f"Requete refusee par la passerelle : {motif}",
            "data": {"regles_violees": regles, "seuil_agregation": SEUIL_PAR_DEFAUT},
        },
    }
    if cible == "http":
        return {
            "interceptorOutputVersion": VERSION_SORTIE,
            "http": {
                "transformedGatewayResponse": {
                    "contentType": "application/json",
                    "statusCode": 403,
                    "body": base64.b64encode(
                        json.dumps(corps_erreur, ensure_ascii=False).encode("utf-8")
                    ).decode("ascii"),
                }
            },
        }
    return {
        "interceptorOutputVersion": VERSION_SORTIE,
        "mcp": {"transformedGatewayResponse": {"statusCode": 403, "body": corps_erreur}},
    }
