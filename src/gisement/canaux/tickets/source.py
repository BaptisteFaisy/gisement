"""Real ITSM source adapter. Never instantiated by a test (26.4)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from gisement.types.communs import Canal


class SourceItsm:
    """Reads tickets through an injected client.

    The client is whatever the MSP already uses for the account: a REST client,
    a boto3 resource, a Strands tool. The adapter only normalises the records
    into the frozen schema of `docs/CONTRACTS.md` section 5.
    """

    def __init__(self, client: Any, canal: Canal = Canal.TICKETS, requete: str = "") -> None:
        self._client = client
        self.canal = canal
        self.requete = requete

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in self._client.lister(self.requete):
            yield self.normaliser(brut)

    def volume(self) -> int:
        return sum(1 for _ in self.lire())

    @staticmethod
    def normaliser(brut: dict[str, Any]) -> dict[str, Any]:
        """Map a vendor ticket onto the frozen schema."""
        return {
            "id": str(brut.get("id") or brut.get("key") or ""),
            "horodatage": str(brut.get("created") or brut.get("horodatage") or ""),
            "service": str(brut.get("service") or brut.get("team") or ""),
            "site": str(brut.get("site") or ""),
            "agent": str(brut.get("agent") or brut.get("assignee") or ""),
            "sujet": str(brut.get("sujet") or brut.get("summary") or ""),
            "description": str(brut.get("description") or ""),
            "systeme": str(brut.get("systeme") or brut.get("system") or ""),
            "duree_traitement_minutes": brut.get("duree_traitement_minutes"),
            "statut": str(brut.get("statut") or brut.get("status") or ""),
            "allers_retours": int(brut.get("allers_retours") or brut.get("comments") or 0),
            "groupe": str(brut.get("groupe") or brut.get("group") or ""),
        }
