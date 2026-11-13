"""The API Gateway handler: the same pure handlers, with the Lambda plumbing.

`gisement.api.handlers` holds pure functions over an `Etat`; this module adds
only what a Lambda needs: parsing the API Gateway proxy event, resolving the
tenant from the bearer token (EF-71 - never from the body or a query string),
and shaping the JSON response. One campaign per container: the state lives in
a module global, built lazily so a cold start pays for it once.

No route exposes a person identifier (R1): the answers are the aggregated
outputs of the policy gateway, and the refusals name the rule they enforce.
"""

from __future__ import annotations

import base64
import json

from gisement.api import handlers, vues_mesure, vues_produits
from gisement.api.auth import Identite, meme_tenant, tenant_depuis_jeton

#: The single campaign of a warm container (rebuilt on a cold start).
ETAT: handlers.Etat | None = None

LANGUE_DEFAUT = "fr"
ERREUR_JETON = "jeton absent ou inconnu"


def etat(reinitialiser: bool = False) -> handlers.Etat:
    """The lazy singleton: one demo campaign per container."""
    global ETAT
    if reinitialiser or ETAT is None:
        ETAT = handlers.Etat.demo()
    return ETAT


def reinitialiser() -> None:
    """Forget the cached campaign (tests, or a new campaign in a warm container)."""
    global ETAT
    ETAT = None


def _erreur(statut: int, message: str) -> tuple[int, dict]:
    return statut, {"ok": False, "erreur": message}


def _route_inconnue(chemin: str) -> tuple[int, dict]:
    return _erreur(404, f"route inconnue : {chemin}")


def _methode(evenement: dict) -> str:
    """The HTTP method, from the REST or the HTTP API event shape."""
    methode = evenement.get("httpMethod")
    if not methode:
        methode = (evenement.get("requestContext") or {}).get("http", {}).get("method")
    return str(methode or "").upper()


def _chemin(evenement: dict) -> tuple[str, str]:
    """The full path and the same path without its `/api` prefix.

    `resource` is the API Gateway template; when it holds a placeholder such as
    `/api/gisements/{id}`, the concrete `path` is the truth.
    """
    brut = str(evenement.get("resource") or "")
    if "{" in brut:
        brut = ""
    brut = brut or str(evenement.get("path") or "/")
    brut = brut.split("?", 1)[0].rstrip("/") or "/"
    return brut, (brut.removeprefix("/api").rstrip("/") or "/")


def _langue(evenement: dict) -> str:
    parametres = evenement.get("queryStringParameters") or {}
    return str(parametres.get("langue") or LANGUE_DEFAUT)


def _jeton(evenement: dict) -> str | None:
    """The bearer token, whatever the header casing the runtime used."""
    entetes = evenement.get("headers") or {}
    return entetes.get("Authorization") or entetes.get("authorization")


def _identite(evenement: dict) -> Identite | None:
    """EF-71 - the tenant comes from the token, never from the request text."""
    return tenant_depuis_jeton(_jeton(evenement), etat().campagne.tenant_id)


def _corps(evenement: dict) -> dict:
    """The JSON body of a POST; an empty or malformed body reads as `{}`."""
    brut = evenement.get("body")
    if not brut:
        return {}
    if isinstance(brut, bytes | bytearray):
        brut = brut.decode("utf-8", "replace")
    if evenement.get("isBase64Encoded"):
        brut = base64.b64decode(brut).decode("utf-8", "replace")
    try:
        charge = json.loads(brut)
    except json.JSONDecodeError:
        return {}
    return charge if isinstance(charge, dict) else {}


def _router_get(chemin: str, langue: str) -> tuple[int, dict] | None:
    """Map a GET path to the matching pure handler; None when nothing matches."""
    courant = etat()
    resultat = courant.resultat
    exactes = {
        "/health": lambda: handlers.health(courant),
        "/campagnes/courante": lambda: handlers.campagnes_detail(courant),
        "/campagne": lambda: (
            200,
            {"ok": True, "donnees": vues_produits.campagne_courante(courant.campagne)},
        ),
        "/projets": lambda: handlers.projets(courant),
        "/deconseilles": lambda: handlers.deconseilles(courant),
        "/budget": lambda: handlers.budget(courant),
        "/processus": lambda: vues_mesure.processus_table(resultat),
        "/motifs": lambda: vues_mesure.motifs_mesures(resultat),
        "/catalogue": vues_mesure.catalogue_complet,
        "/plan": lambda: vues_mesure.plan_projet(resultat),
        "/suivi": lambda: vues_produits.suivi_longitudinal(resultat),
        "/backtest": vues_produits.backtest,
        "/evaluation": vues_produits.evaluation,
        "/privacy": lambda: vues_produits.privacy(resultat),
        "/cedar": vues_produits.politique_cedar_vue,
        "/connecteurs": vues_produits.connecteurs,
        "/proposition": lambda: vues_produits.proposition(resultat),
        "/quick": lambda: vues_produits.quick_assets(resultat),
        "/cout": vues_produits.cout_detaille,
    }
    if chemin in exactes:
        return exactes[chemin]()
    if chemin.startswith("/gisements/"):
        return handlers.gisement_detail(courant, chemin.rsplit("/", 1)[-1])
    if chemin.startswith("/processus/"):
        return vues_mesure.processus_fiche(resultat, chemin.rsplit("/", 1)[-1])
    if chemin.startswith("/rapports/"):
        return handlers.rapport(courant, langue)
    if chemin.startswith("/registre-conformite/"):
        return handlers.registre(courant, langue)
    if chemin.startswith("/projets/") and chemin.endswith("/cas-business"):
        return handlers.cas_business_route(courant, chemin.split("/")[2], langue)
    return None


def _router_post(chemin: str, identite: Identite, corps: dict) -> tuple[int, dict] | None:
    """Map a POST path to the matching pure handler; None when nothing matches."""
    courant = etat()
    if chemin == "/campagnes/courante/conformite":
        return handlers.declarer_conformite(courant, identite, corps)
    if chemin == "/campagnes/courante/lancer":
        return handlers.lancer(courant, identite)
    if chemin == "/campagnes/courante/suspendre":
        return handlers.suspendre(courant, identite)
    if chemin == "/mesure":
        return handlers.mesurer(courant, identite, corps)
    if chemin.startswith("/processus/") and chemin.endswith("/valider"):
        processus_id = chemin.split("/")[2]
        decision = str(corps.get("decision") or "validee")
        return handlers.valider_processus(courant, processus_id, decision, identite)
    return None


def router(evenement: dict) -> tuple[int, dict]:
    """Resolve an API Gateway proxy event into `(statusCode, body)`."""
    complet, chemin = _chemin(evenement)
    identite = _identite(evenement)
    if identite is None:
        return _erreur(403, ERREUR_JETON)
    if not meme_tenant(identite, etat().campagne.tenant_id):
        return _erreur(403, "tenant different de la campagne servie (R21)")
    methode = _methode(evenement)
    resultat: tuple[int, dict] | None = None
    if methode == "GET":
        resultat = _router_get(chemin, _langue(evenement))
    elif methode == "POST":
        resultat = _router_post(chemin, identite, _corps(evenement))
    else:
        return _erreur(405, f"methode non supportee : {methode or 'inconnue'} ({complet})")
    return resultat if resultat is not None else _route_inconnue(complet)


def handler(evenement: dict, contexte: object = None) -> dict:
    """The API Gateway proxy response: always JSON, never a stack trace."""
    try:
        statut, corps = router(evenement)
    except Exception as erreur:  # the runtime must answer JSON, whatever happens
        statut, corps = _erreur(500, f"erreur interne : {erreur}")
    return {
        "statusCode": statut,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corps, ensure_ascii=False),
        "isBase64Encoded": False,
    }
