"""GitHub Issues connector: the ITSM a real client actually uses today.

A real client migrates. The ASF's Kafka project still has its Jira, but the work
of the last years happens in GitHub issues and pull requests: reading only the
old tracker measures work that is no longer done. This connector reads the real
current one and produces **the same frozen ticket schema**, with `systeme`
saying which tool a record came from.

Pagination is by page number (`?page=N&per_page=100`) rather than by the `Link`
header: a connector that has to read headers to know when to stop cannot be
exercised with a canned client, and every connector of this project is tested
without a network (26.4).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from gisement.connecteurs.base import ClientHttp, normaliser_ticket
from gisement.types.communs import Canal

API = "https://api.github.com"


class SourceGithub:
    """Reads the issues and pull requests of a real repository."""

    canal = Canal.TICKETS

    def __init__(
        self,
        client: ClientHttp,
        proprietaire: str,
        depot: str,
        depuis: str = "",
        jusqu: str = "",
        base: str = API,
        pas: int = 100,
        max_pages: int = 100,
    ) -> None:
        self.client = client
        self.proprietaire = proprietaire
        self.depot = depot
        self.depuis = depuis
        self.jusqu = jusqu
        self.base = base.rstrip("/")
        self.pas = pas
        self.max_pages = max_pages

    def url(self, page: int) -> str:
        return (
            f"{self.base}/repos/{self.proprietaire}/{self.depot}/issues"
            f"?state=all&sort=created&direction=desc&per_page={self.pas}&page={page}"
        )

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in self.bruts():
            yield normaliser_ticket(self.vers_jira(brut), "github")

    def bruts(self) -> Iterator[dict[str, Any]]:
        """The raw records of the window, newest first.

        The records after `jusqu` are skipped and the walk stops on the first one
        older than `depuis`: one real window, and not one request more.
        """
        for page in range(1, self.max_pages + 1):
            bruts = self._page(page)
            if not bruts:
                return
            for brut in bruts:
                quand = str(brut.get("created_at", ""))[:10]
                if self.depuis and quand < self.depuis:
                    return
                if self.jusqu and quand > self.jusqu:
                    continue
                yield brut

    def _page(self, page: int) -> list[dict[str, Any]]:
        reponse = self.client.get(self.url(page))
        if isinstance(reponse, dict):
            return list(reponse.get("issues", []) or [])
        return list(reponse or [])

    def vers_jira(self, brut: dict[str, Any]) -> dict[str, Any]:
        """A GitHub issue in the shape `normaliser_ticket` already understands."""
        etiquettes = [str(e.get("name", "")) for e in brut.get("labels", []) if e.get("name")]
        assigne = brut.get("assignee") or brut.get("user") or {}
        return {
            "key": f"GH-{brut.get('number')}",
            "fields": {
                "summary": brut.get("title"),
                "description": brut.get("body"),
                "created": brut.get("created_at"),
                "resolutiondate": brut.get("closed_at"),
                "assignee": {"displayName": assigne.get("login")},
                "status": {"name": brut.get("state")},
                "project": {"key": self.depot},
                "components": [{"name": e} for e in etiquettes],
                "priority": {"name": next((e for e in etiquettes if e.lower() == "blocker"), "")},
                "comment": {"total": brut.get("comments", 0)},
                "groupe": "pull_request" if brut.get("pull_request") else "issue",
                "labels": etiquettes,
            },
        }

    def volume(self) -> int:
        return sum(1 for _ in self.lire())
