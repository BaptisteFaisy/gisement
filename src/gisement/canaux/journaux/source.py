"""Real application-log source adapter. Never instantiated by a test (26.4)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from gisement.types.communs import Canal


class SourceErp:
    """Reads an application log export through an injected client."""

    def __init__(self, client: Any, canal: Canal = Canal.JOURNAUX, export: str = "") -> None:
        self._client = client
        self.canal = canal
        self.export = export

    def lire(self) -> Iterator[dict[str, Any]]:
        for brut in self._client.lire_export(self.export):
            yield self.normaliser(brut)

    def volume(self) -> int:
        return sum(1 for _ in self.lire())

    @staticmethod
    def normaliser(brut: dict[str, Any]) -> dict[str, Any]:
        return {
            "horodatage": str(brut.get("horodatage") or brut.get("timestamp") or ""),
            "service": str(brut.get("service") or ""),
            "action": str(brut.get("action") or brut.get("operation") or ""),
            "entite": str(brut.get("entite") or brut.get("entity") or ""),
            "systeme": str(brut.get("systeme") or brut.get("application") or ""),
            "groupe": str(brut.get("groupe") or brut.get("group") or ""),
            "duree_secondes": brut.get("duree_secondes") or brut.get("duration_seconds"),
        }
