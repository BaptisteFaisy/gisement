"""Jira connector: the ITSM channel of a client that already uses Jira.

Two real APIs are supported, because a real client runs one or the other:

  - Jira **Cloud** (`/rest/api/3/search`), cursor pagination through `next`;
  - Jira **Server / Data Center** (`/rest/api/2/search`), offset pagination
    through `startAt` / `total`. This is what a real public Jira answers, and
    it is the one the real corpus of `reel/` reads (the ASF's Jira).

The fields are asked for explicitly: a real search without `fields` returns the
whole comment body of every issue, which is both slow and useless here.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

from gisement.connecteurs.base import ClientHttp, normaliser_ticket, paginer, paginer_decalage
from gisement.types.communs import Canal

CHAMPS_PAR_DEFAUT = (
    "summary",
    "description",
    "status",
    "created",
    "updated",
    "resolutiondate",
    "assignee",
    "reporter",
    "components",
    "labels",
    "priority",
    "resolution",
    "comment",
)


class SourceJira:
    """Reads a Jira project through an injected HTTP client.

    The client is whatever the MSP already authenticates with (a PAT, an OAuth
    session) - or nothing at all on a public Jira. The connector only paginates
    and normalises; it never stores anything and never sends an identifier
    further (R3).
    """

    canal = Canal.TICKETS

    def __init__(
        self,
        client: ClientHttp,
        projet: str,
        base: str = "/rest/api/3",
        jql: str | None = None,
        champs: tuple[str, ...] = CHAMPS_PAR_DEFAUT,
        pas: int = 100,
        max_pages: int = 100,
        offset: bool | None = None,
    ) -> None:
        self.client = client
        self.projet = projet
        self.base = base.rstrip("/")
        self.jql = jql or f"project={self.projet} ORDER BY created"
        self.champs = tuple(champs)
        self.pas = pas
        self.max_pages = max_pages
        self.offset = self.base.endswith("/2") if offset is None else offset

    def url(self) -> str:
        return (
            f"{self.base}/search?jql={quote(self.jql)}&fields={','.join(self.champs)}&maxResults={self.pas}"
        )

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in self.pages_brutes():
            yield normaliser_ticket(brut, "jira")

    def pages_brutes(self) -> Iterator[dict[str, Any]]:
        """The raw vendor records, for a collector that keeps its own provenance."""
        if self.offset:
            return paginer_decalage(self.client, self.url(), pas=self.pas, max_pages=self.max_pages)
        return paginer(self.client, self.url(), cle_page="issues", max_pages=self.max_pages)

    def volume(self) -> int:
        return sum(1 for _ in self.lire())
