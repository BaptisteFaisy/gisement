"""ServiceNow connector: the ITSM channel of a client that uses ServiceNow."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from gisement.connecteurs.base import ClientHttp, normaliser_ticket, paginer
from gisement.types.communs import Canal


class SourceServiceNow:
    """Reads a ServiceNow table through an injected HTTP client."""

    canal = Canal.TICKETS

    def __init__(self, client: ClientHttp, table: str = "incident", base: str = "/api/now/table"):
        self.client = client
        self.table = table
        self.base = base.rstrip("/")

    def url(self) -> str:
        return f"{self.base}/{self.table}?sysparm_limit=100&sysparm_query=ORDERBYopened_at"

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in paginer(self.client, self.url()):
            yield normaliser_ticket(brut, "servicenow")

    def volume(self) -> int:
        return sum(1 for _ in self.lire())
