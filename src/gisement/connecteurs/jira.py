"""Jira connector: the ITSM channel of a client that already uses Jira."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from gisement.connecteurs.base import ClientHttp, normaliser_ticket, paginer
from gisement.types.communs import Canal


class SourceJira:
    """Reads a Jira project through an injected HTTP client.

    The client is whatever the MSP already authenticates with (a PAT, an OAuth
    session). The connector only paginates and normalises; it never stores
    anything and never sends an identifier further (R3).
    """

    canal = Canal.TICKETS

    def __init__(self, client: ClientHttp, projet: str, base: str = "/rest/api/3"):
        self.client = client
        self.projet = projet
        self.base = base.rstrip("/")

    def url(self) -> str:
        jql = f"project={self.projet} ORDER BY created"
        return f"{self.base}/search?jql={jql}&maxResults=100"

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in paginer(self.client, self.url()):
            yield normaliser_ticket(brut, "jira")

    def volume(self) -> int:
        return sum(1 for _ in self.lire())
