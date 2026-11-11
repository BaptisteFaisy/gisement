"""Real mailbox source adapter. Never instantiated by a test (26.4)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from gisement.types.communs import Canal


class SourceMessagerie:
    """Reads a scoped mailbox through an injected client.

    The scope is declared in advance and recorded in the compliance register:
    only the mailboxes of the declared perimeter are read, and only as a
    stratified sample (6.3, 24.1 - secrecy of correspondence).
    """

    def __init__(self, client: Any, canal: Canal = Canal.COURRIELS, perimetre: str = "") -> None:
        self._client = client
        self.canal = canal
        self.perimetre = perimetre

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in self._client.lister(self.perimetre):
            yield self.normaliser(brut)

    def volume(self) -> int:
        return sum(1 for _ in self.lire())

    @staticmethod
    def normaliser(brut: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(brut.get("id") or ""),
            "horodatage": str(brut.get("horodatage") or brut.get("receivedDateTime") or ""),
            "expediteur": str(brut.get("expediteur") or brut.get("from") or ""),
            "destinataires": list(brut.get("destinataires") or brut.get("to") or ()),
            "objet": str(brut.get("objet") or brut.get("subject") or ""),
            "corps": str(brut.get("corps") or brut.get("body") or ""),
            "service": str(brut.get("service") or ""),
            "stratum": str(brut.get("stratum") or brut.get("folder") or ""),
            "piece_jointe": brut.get("piece_jointe"),
        }
