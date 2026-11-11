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

from gisement.api import handlers
from gisement.api.auth import tenant_depuis_jeton

RACINE = Path(__file__).resolve().parents[3]
PORTAIL = RACINE / "portal"

ETAT = handlers.Etat.demo()

CONTENU_JSON = "application/json; charset=utf-8"
CONTENU_HTML = "text/html; charset=utf-8"
CONTENU_JS = "application/javascript; charset=utf-8"
CONTENU_CSS = "text/css; charset=utf-8"


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
        requete = parse_qs(urlparse(self.path).query)
        langue = requete.get("langue", ["fr"])[0]
        if chemin == "/api/health":
            statut, reponse = handlers.health(ETAT)
        elif chemin == "/api/campagnes/courante":
            statut, reponse = handlers.campagnes_detail(ETAT)
        elif chemin == "/api/projets":
            statut, reponse = handlers.projets(ETAT)
        elif chemin == "/api/deconseilles":
            statut, reponse = handlers.deconseilles(ETAT)
        elif chemin.startswith("/api/gisements/"):
            statut, reponse = handlers.gisement_detail(ETAT, chemin.rsplit("/", 1)[-1])
        elif chemin.startswith("/api/rapports/"):
            statut, reponse = handlers.rapport(ETAT, langue)
        elif chemin.startswith("/api/registre-conformite/"):
            statut, reponse = handlers.registre(ETAT, langue)
        elif chemin.startswith("/api/projets/") and chemin.endswith("/cas-business"):
            processus_id = chemin.split("/")[3]
            statut, reponse = handlers.cas_business_route(ETAT, processus_id, langue)
        elif chemin == "/api/budget":
            statut, reponse = handlers.budget(ETAT)
        else:
            statut, reponse = 404, {"ok": False, "erreur": f"route inconnue : {chemin}"}
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


def servir(hote: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the demo server (blocking)."""
    serveur = ThreadingHTTPServer((hote, port), Gestionnaire)
    print(f"Gisement - portail sur http://{hote}:{port}/ (jeton: jeton-demo-msp)")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        serveur.shutdown()
