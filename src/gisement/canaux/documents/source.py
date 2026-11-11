"""Document source: metadata joined with its extraction (frozen or real)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from gisement.canaux.base import Source
from gisement.canaux.documents.data_automation import Extracteur
from gisement.types.communs import Canal


class SourceDocuments(Source):
    """Joins `documents.json` with each document's extraction.

    The extractor is injected: the frozen one in every test and in development,
    the Bedrock Data Automation adapter in production (26.4).
    """

    canal = Canal.DOCUMENTS

    def __init__(self, racine: str | Path, extracteur: Extracteur) -> None:
        self.chemin = Path(racine) / "documents" / "documents.json"
        self.extracteur = extracteur
        self.pages_extraites = 0

    def lire(self) -> Iterator[dict[str, Any]]:
        if not self.chemin.exists():
            return iter(())
        for document in json.loads(self.chemin.read_text(encoding="utf-8")):
            yield self.fusionner(document)

    def fusionner(self, document: dict[str, Any]) -> dict[str, Any]:
        extraction = self.extracteur.extraire(document)
        self.pages_extraites += self.extracteur.pages(document)
        champs = extraction.get("champs", {})
        return {
            **document,
            "systeme": document.get("systeme", "ged"),
            "extraction_confiance": extraction.get("confiance", 0.0),
            "champs": champs,
            "tableaux": extraction.get("tableaux", []),
            "texte_libre": str(champs.get("texte_libre", "")),
            "categories_sensibles_detectees": list(extraction.get("categories_sensibles_detectees", [])),
        }

    def volume(self) -> int:
        if not self.chemin.exists():
            return 0
        return len(json.loads(self.chemin.read_text(encoding="utf-8")))


class SourceEspaceDocumentaire:
    """The real document space adapter (S3, SharePoint, GED)."""

    canal = Canal.DOCUMENTS

    def __init__(self, client: Any, extracteur: Extracteur, prefixe: str = "") -> None:
        self._client = client
        self.extracteur = extracteur
        self.prefixe = prefixe

    def lire(self) -> Iterator[dict[str, Any]]:
        for objet in self._client.lister(self.prefixe):
            document = {
                "id": objet["Key"],
                "type": objet.get("type", "document"),
                "titre": objet.get("titre", objet["Key"]),
                "chemin": objet["Key"],
                "pages": int(objet.get("pages", 1)),
                "service": objet.get("service", ""),
                "horodatage": objet.get("LastModified", ""),
            }
            extraction = self.extracteur.extraire(document)
            yield {
                **document,
                "champs": extraction.get("champs", {}),
                "texte_libre": str(extraction.get("champs", {}).get("texte_libre", "")),
                "systeme": "ged",
                "categories_sensibles_detectees": list(extraction.get("categories_sensibles_detectees", [])),
            }

    def volume(self) -> int:
        return sum(1 for _ in self._client.lister(self.prefixe))
