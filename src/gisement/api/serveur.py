"""Local demo server (lot 18): stdlib http.server, no framework dependency.

The handlers are framework-agnostic pure functions, so the Lambda/API-Gateway
deployment (decision D-21) reuses them unchanged; this server only adds HTTP
routing and the tenant-from-token resolution for the local demo and the video.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from gisement.api import handlers, vues_mesure, vues_produits
from gisement.api.auth import tenant_depuis_jeton

RACINE = Path(__file__).resolve().parents[3]
# the static site is the complete artefact (it carries data/api.json); the
# portal directory is the source it is built from
PORTAIL = RACINE / "site" if (RACINE / "site").is_dir() else RACINE / "portal"

#: The state the server measures: the synthetic demo, or the real corpus when
#: the server is started with `--corpus reel`. Same handlers either way.
ETAT = handlers.Etat.demo()


def choisir_corpus(nom: str) -> handlers.Etat:
    """The state of the requested corpus: "demo" or "reel"."""
    if nom == "reel":
        return handlers.Etat.reel()
    return handlers.Etat.demo()


CONTENU_JSON = "application/json; charset=utf-8"
CONTENU_HTML = "text/html; charset=utf-8"
CONTENU_JS = "application/javascript; charset=utf-8"
CONTENU_CSS = "text/css; charset=utf-8"


def _route_get(chemin: str, langue: str) -> tuple[int, dict]:
    """Dispatch one GET route. Order matters: exact paths before prefixes."""
    resultat = ETAT.resultat
    exactes = {
        "/api/health": lambda: handlers.health(ETAT),
        "/api/campagnes/courante": lambda: handlers.campagnes_detail(ETAT),
        "/api/campagne": lambda: (200, {"ok": True, "donnees": vues_produits.campagne_courante()}),
        "/api/projets": lambda: handlers.projets(ETAT),
        "/api/deconseilles": lambda: handlers.deconseilles(ETAT),
        "/api/budget": lambda: handlers.budget(ETAT),
        "/api/processus": lambda: vues_mesure.processus_table(resultat),
        "/api/motifs": lambda: vues_mesure.motifs_mesures(resultat),
        "/api/catalogue": vues_mesure.catalogue_complet,
        "/api/plan": lambda: vues_mesure.plan_projet(resultat),
        "/api/suivi": lambda: vues_produits.suivi_longitudinal(resultat),
        "/api/backtest": vues_produits.backtest,
        "/api/evaluation": vues_produits.evaluation,
        "/api/privacy": lambda: vues_produits.privacy(resultat),
        "/api/cedar": vues_produits.politique_cedar_vue,
        "/api/connecteurs": vues_produits.connecteurs,
        "/api/proposition": lambda: vues_produits.proposition(resultat),
        "/api/quick": lambda: vues_produits.quick_assets(resultat),
        "/api/cout": vues_produits.cout_detaille,
    }
    if chemin in exactes:
        return exactes[chemin]()
    if chemin.startswith("/api/gisements/"):
        return handlers.gisement_detail(ETAT, chemin.rsplit("/", 1)[-1])
    if chemin.startswith("/api/processus/"):
        return vues_mesure.processus_fiche(resultat, chemin.rsplit("/", 1)[-1])
    if chemin.startswith("/api/rapports/"):
        return handlers.rapport(ETAT, langue)
    if chemin.startswith("/api/registre-conformite/"):
        return handlers.registre(ETAT, langue)
    if chemin.startswith("/api/projets/") and chemin.endswith("/cas-business"):
        return handlers.cas_business_route(ETAT, chemin.split("/")[3], langue)
    return 404, {"ok": False, "erreur": f"route inconnue : {chemin}"}


class Gestionnaire(BaseHTTPRequestHandler):
    """Routes the demo API and serves the static portal."""

    def log_message(self, format: str, *args) -> None:
        pass

    def _identite(self):
        return tenant_depuis_jeton(self.headers.get("Authorization"))

    def _corps(self) -> dict:
        longueur = int(self.headers.get("Content-Length", 0) or 0)
        if longueur == 0:
            return {}
        try:
            return json.loads(self.rfile.read(longueur).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _repondre(self, statut: int, contenu: bytes, type_contenu: str) -> None:
        self.send_response(statut)
        self.send_header("Content-Type", type_contenu)
        self.send_header("Content-Length", str(len(contenu)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(contenu)

    def _json(self, statut: int, objet: dict) -> None:
        self._repondre(statut, json.dumps(objet, ensure_ascii=False).encode("utf-8"), CONTENU_JSON)

    def do_GET(self) -> None:
        chemin = urlparse(self.path).path
        if chemin.startswith("/api/"):
            self._api_get(chemin)
        else:
            self._statique(chemin)

    def do_POST(self) -> None:
        chemin = urlparse(self.path).path
        identite = self._identite()
        if identite is None:
            self._json(401, {"ok": False, "erreur": "jeton absent ou inconnu"})
            return
        corps = self._corps()
        statut, reponse = self._router_post(chemin, identite, corps)
        self._json(statut, reponse)

    def _api_get(self, chemin: str) -> None:
        identite = self._identite()
        if identite is None:
            self._json(401, {"ok": False, "erreur": "jeton absent ou inconnu"})
            return
        langue = parse_qs(urlparse(self.path).query).get("langue", ["fr"])[0]
        statut, reponse = _route_get(chemin, langue)
        self._json(statut, reponse)

    def _router_post(self, chemin: str, identite, corps: dict) -> tuple[int, dict]:
        if chemin == "/api/campagnes/courante/conformite":
            return handlers.declarer_conformite(ETAT, identite, corps)
        if chemin == "/api/campagnes/courante/lancer":
            return handlers.lancer(ETAT, identite)
        if chemin == "/api/campagnes/courante/suspendre":
            return handlers.suspendre(ETAT, identite)
        if chemin == "/api/mesure":
            return handlers.mesurer(ETAT, identite, corps)
        if chemin.startswith("/api/processus/") and chemin.endswith("/valider"):
            processus_id = chemin.split("/")[3]
            return handlers.valider_processus(
                ETAT, processus_id, corps.get("decision", "validee"), identite.utilisateur
            )
        return 404, {"ok": False, "erreur": f"route inconnue : {chemin}"}

    def _statique(self, chemin: str) -> None:
        cible = "index.html" if chemin in ("/", "") else chemin.lstrip("/")
        fichier = (PORTAIL / cible).resolve()
        if not str(fichier).startswith(str(PORTAIL.resolve())) or not fichier.is_file():
            self._repondre(404, b"introuvable", "text/plain; charset=utf-8")
            return
        type_contenu = {
            ".html": CONTENU_HTML,
            ".js": CONTENU_JS,
            ".css": CONTENU_CSS,
        }.get(fichier.suffix, "application/octet-stream")
        self._repondre(200, fichier.read_bytes(), type_contenu)


def servir(hote: str = "127.0.0.1", port: int = 8080, corpus: str = "demo") -> None:
    """Run the portal server (blocking), on the demo or on the real corpus."""
    global ETAT
    ETAT = choisir_corpus(corpus)
    serveur = ThreadingHTTPServer((hote, port), Gestionnaire)
    print(f"Gisement - portail sur http://{hote}:{port}/ (jeton: jeton-demo-msp)")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        serveur.shutdown()
