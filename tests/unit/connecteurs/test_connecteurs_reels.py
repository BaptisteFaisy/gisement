"""The real connectors, exercised without a network (26.4).

The pages are canned: a connector that only works with the internet is a
connector nobody can test.
"""

from __future__ import annotations

from typing import Any

from gisement.connecteurs.confluence import SourceConfluence, html_vers_texte, tableaux
from gisement.connecteurs.github import SourceGithub


class FauxGithub:
    """The GitHub REST API, canned: a list of issues per page."""

    def __init__(self, pages: dict[int, list[dict[str, Any]]]) -> None:
        self.pages = pages
        self.appels: list[str] = []

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.appels.append(url)
        page = 1
        for morceau in url.split("&"):
            if morceau.startswith("page="):
                page = int(morceau.split("=", 1)[1])
        return {"issues": self.pages.get(page, [])}


def _issue(numero: int, cree: str, labels: list[str], pr: bool = False) -> dict[str, Any]:
    return {
        "number": numero,
        "created_at": f"{cree}T10:00:00Z",
        "closed_at": f"{cree}T12:00:00Z",
        "title": "Fix the thing",
        "body": "a real body",
        "labels": [{"name": nom} for nom in labels],
        "assignee": {"login": "un-contributeur"},
        "user": {"login": "un-contributeur"},
        "comments": 3,
        "state": "closed",
        **({"pull_request": {"url": "..."}} if pr else {}),
    }


def test_github_lit_la_fenetre_reelle_et_s_arrete() -> None:
    client = FauxGithub(
        {
            1: [_issue(3, "2025-06-02", ["core"]), _issue(2, "2025-05-02", ["core"])],
            2: [_issue(1, "2025-04-02", ["core"])],
        }
    )
    source = SourceGithub(client, "apache", "kafka", depuis="2025-05-01", jusqu="2025-06-30", pas=2)
    tickets = list(source.lire())
    assert [t["id"] for t in tickets] == ["GH-3", "GH-2"]
    assert len(client.appels) == 2, "la lecture s'arrete a la page qui franchit le debut"


def test_github_normalise_le_service_le_groupe_et_le_traitement() -> None:
    client = FauxGithub({1: [_issue(7, "2025-05-02", ["core", "kip"], pr=True)]})
    source = SourceGithub(client, "apache", "kafka", depuis="2025-05-01", jusqu="2025-06-30")
    ticket = next(iter(source.lire()))
    assert ticket["systeme"] == "github"
    assert ticket["service"] == "core"
    assert ticket["groupe"] == "pull_request"
    assert ticket["allers_retours"] == 3
    assert ticket["duree_traitement_minutes"] == 120.0


def test_confluence_lit_les_pages_d_un_espace() -> None:
    class Faux:
        def __init__(self) -> None:
            self.appels: list[str] = []

        def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            self.appels.append(url)
            if "start=25" in url:
                return {"results": []}
            return {
                "results": [
                    {
                        "id": "42",
                        "title": "KIP-42: A real proposal",
                        "version": {"number": 3, "when": "2025-05-02T10:00:00.000Z"},
                        "body": {"storage": {"value": "<p>Motivation</p><p>Real text</p>"}},
                    }
                ]
            }

    client = Faux()
    source = SourceConfluence(client, espace="KAFKA", cql='space=KAFKA AND title~"KIP"', pas=25)
    pages = list(source.bruts())
    assert len(pages) == 1
    assert pages[0]["title"].startswith("KIP-42")
    assert "Motivation" in html_vers_texte("<p>Motivation</p><p>Real text</p>")


def test_les_tableaux_dune_page_sont_extraits() -> None:
    html = "<table><tr><th>col</th><th>val</th></tr><tr><td>a</td><td>1</td></tr></table>"
    extraits = tableaux(html)
    assert len(extraits) == 1
    assert extraits[0]["colonnes"] == ["col", "val"]
    assert extraits[0]["lignes"] == [["a", "1"]]
