"""The real HTTP client of the connectors: standard library only.

A connector is handed whatever the MSP authenticates with. This module is the
plain implementation used when the corpus is fetched for real (`reel/`): no
dependency, a timeout, a bounded number of retries, a polite rate, and an
identification that says who is calling.

Two rules are non-negotiable:
  - a credential never appears in an exception, a log or a written file;
  - nothing here is ever called by a test (26.4): tests use `FauxClientHttp`.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "gisement/1.0 (+https://github.com/BaptisteFaisy/gisement)"
TIMEOUT_SECONDES = 30.0
PAUSE_SECONDES = 1.0
ESSAIS_MAX = 3
STATUTS_RETOUVE = frozenset({429, 500, 502, 503, 504})


class ErreurHttpReel(RuntimeError):
    """A real HTTP failure, said out loud - without the request headers."""


class ClientHttpReel:
    """`ClientHttp` over urllib, for a real public system."""

    def __init__(
        self,
        entetes: dict[str, str] | None = None,
        timeout: float = TIMEOUT_SECONDES,
        pause: float = PAUSE_SECONDES,
        essais: int = ESSAIS_MAX,
    ) -> None:
        self._entetes = {"User-Agent": USER_AGENT, "Accept": "application/json", **(entetes or {})}
        self.timeout = timeout
        self.pause = pause
        self.essais = essais
        self.requetes = 0

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """One page of JSON results."""
        brut = self.get_bytes(url, params)
        try:
            return json.loads(brut.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as erreur:
            raise ErreurHttpReel(f"reponse non JSON pour {url_sans_jetons(url)}") from erreur

    def get_bytes(self, url: str, params: dict[str, Any] | None = None) -> bytes:
        """The raw body, for the sources that are not JSON (mbox, ZIP, text)."""
        complet = url
        if params:
            sep = "&" if "?" in url else "?"
            complet = f"{url}{sep}{urllib.parse.urlencode(params)}"
        requete = urllib.request.Request(complet, headers=self._entetes)
        self.requetes += 1
        time.sleep(self.pause)
        return self._lire(requete)

    def _lire(self, requete: urllib.request.Request) -> bytes:
        """Retry the transient failures, fail loudly on the rest."""
        derniere: Exception | None = None
        for essai in range(self.essais):
            try:
                with urllib.request.urlopen(requete, timeout=self.timeout) as reponse:
                    return reponse.read()
            except urllib.error.HTTPError as erreur:
                if erreur.code not in STATUTS_RETOUVE or essai == self.essais - 1:
                    raise ErreurHttpReel(
                        f"HTTP {erreur.code} sur {url_sans_jetons(requete.full_url)}"
                    ) from None
                derniere = erreur
            except (urllib.error.URLError, TimeoutError, OSError) as erreur:
                if essai == self.essais - 1:
                    raise ErreurHttpReel(
                        f"reseau : {erreur.__class__.__name__} sur {url_sans_jetons(requete.full_url)}"
                    ) from None
                derniere = erreur
            time.sleep(self.pause * (essai + 1))
        raise ErreurHttpReel(f"echec apres {self.essais} essais ({derniere})")


def url_sans_jetons(url: str) -> str:
    """A URL safe to print: the query string is dropped, the path is kept."""
    return url.split("?", 1)[0]
