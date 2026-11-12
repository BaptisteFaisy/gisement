"""Confluence connector: the real written procedures of a real client.

Gisement never reads a procedure to describe the process - it reads it last, to
measure the gap with the observed work (9.1). This connector is what makes that
possible on a real client: the design documents of a real project (the ASF's
public Confluence, where the Kafka KIPs live) are its written procedures.

Public API, no credential, offset pagination (`start` / `limit` / `size`).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

from gisement.connecteurs.base import ClientHttp

BASE_REELLE = "https://cwiki.apache.org/confluence/rest/api"
BLOCS = ("p", "br", "li", "tr", "h1", "h2", "h3", "h4", "table", "div")
IGNORES = ("script", "style")


class SourceConfluence:
    """Reads the pages of one real space through an injected HTTP client."""

    def __init__(
        self,
        client: ClientHttp,
        espace: str,
        base: str = BASE_REELLE,
        expansion: str = "body.storage,version,history",
        pas: int = 25,
        max_pages: int = 40,
        cql: str = "",
    ) -> None:
        self.client = client
        self.espace = espace
        self.cql = cql
        self.base = base.rstrip("/")
        self.expansion = expansion
        self.pas = pas
        self.max_pages = max_pages

    def url(self, debut: int) -> str:
        """One page of results. A real Confluence answers a CQL query on
        `/content/search`, and a plain space listing on `/content`."""
        fin = f"&expand={self.expansion}&limit={self.pas}&start={debut}"
        if self.cql:
            return f"{self.base}/content/search?cql={quote(self.cql)}{fin}"
        return f"{self.base}/content?space={self.espace}&type=page{fin}"

    def bruts(self) -> Iterator[dict[str, Any]]:
        """The raw pages, bounded by `max_pages` and by a short last page."""
        for page in range(self.max_pages):
            reponse = self.client.get(self.url(page * self.pas))
            resultats = list(reponse.get("results", []) or [])
            yield from resultats
            if not resultats or len(resultats) < self.pas:
                return

    def volume(self) -> int:
        return sum(1 for _ in self.bruts())


class _Extracteur(HTMLParser):
    """A real `body.storage` -> readable text. Standard library only."""

    def __init__(self) -> None:
        super().__init__()
        self.morceaux: list[str] = []
        self._ignore = 0

    def handle_starttag(self, balise: str, attrs: Any) -> None:
        if balise in IGNORES:
            self._ignore += 1
        if balise in BLOCS:
            self.morceaux.append("\n")
        if balise in ("td", "th"):
            self.morceaux.append(" | ")

    def handle_endtag(self, balise: str) -> None:
        if balise in IGNORES and self._ignore:
            self._ignore -= 1

    def handle_data(self, donnee: str) -> None:
        if not self._ignore and donnee.strip():
            self.morceaux.append(donnee.strip())


def html_vers_texte(brut_html: str) -> str:
    """The readable text of a real page, one line per block."""
    extracteur = _Extracteur()
    extracteur.feed(brut_html or "")
    lignes = [" ".join(ligne.split()) for ligne in "".join(extracteur.morceaux).split("\n")]
    return "\n".join(ligne for ligne in lignes if ligne)


def _nettoyer(cellule: str) -> str:
    return " ".join(re.sub(r"<.*?>", "", cellule, flags=re.S).split())


def tableaux(brut_html: str, limite: int = 5) -> list[dict[str, Any]]:
    """The real tables of a page, in the frozen extraction shape."""
    trouves: list[dict[str, Any]] = []
    for brut in re.findall(r"<table.*?</table>", brut_html or "", re.S | re.I)[:limite]:
        lignes = [
            [_nettoyer(cellule) for cellule in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", ligne, re.S | re.I)]
            for ligne in re.findall(r"<tr.*?</tr>", brut, re.S | re.I)
        ]
        lignes = [ligne for ligne in lignes if ligne]
        if not lignes:
            continue
        trouves.append(
            {
                "nom": f"tableau_{len(trouves) + 1}",
                "colonnes": lignes[0],
                "lignes": lignes[1:],
            }
        )
    return trouves
