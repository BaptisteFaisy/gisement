"""Bedrock Data Automation: structured extraction of documents (EF-15).

Two implementations of the same protocol:

* `ExtractionFigee` reads the extractions frozen in the demo corpus. It is what
  every test and every development run uses - rule 1 of 26.4: Data Automation is
  half of the cost of a mapping, so it is never called during development.
* `DataAutomation` is the real adapter, with an injected boto3 client. It exists,
  it is deployed, and no test instantiates it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Extracteur(Protocol):
    """Extracts the structure of one document."""

    def extraire(self, document: dict[str, Any]) -> dict[str, Any]:
        """The frozen extraction shape: document_id, confiance, champs, tableaux."""
        ...

    def pages(self, document: dict[str, Any]) -> int:
        """Number of pages billed by Data Automation."""
        ...


class ExtractionFigee:
    """Reads the extractions committed in the demo corpus."""

    nom = "figee"

    def __init__(self, racine: str | Path) -> None:
        self.racine = Path(racine)

    def extraire(self, document: dict[str, Any]) -> dict[str, Any]:
        chemin = self.racine / "documents" / "extractions" / f"{document['id']}.json"
        if not chemin.exists():
            return {
                "document_id": document.get("id", ""),
                "confiance": 0.0,
                "champs": {},
                "tableaux": [],
                "categories_sensibles_detectees": [],
            }
        return json.loads(chemin.read_text(encoding="utf-8"))

    def pages(self, document: dict[str, Any]) -> int:
        return int(document.get("pages", 1))


class DataAutomation:
    """The real Bedrock Data Automation adapter. Never instantiated by a test."""

    nom = "bedrock-data-automation"

    def __init__(self, client: Any, profil: str = "gisement-documents") -> None:
        self._client = client
        self.profil = profil
        self._cache: dict[str, dict[str, Any]] = {}

    def extraire(self, document: dict[str, Any]) -> dict[str, Any]:
        identifiant = str(document.get("id", ""))
        if identifiant in self._cache:
            return self._cache[identifiant]
        tache = self._client.start_data_automation_analysis(
            s3InputPath=document.get("chemin", ""), configuration={"profiles": [self.profil]}
        )
        resultat = self._client.get_data_automation_analysis(invokeId=tache["invokeId"])
        extrait = self.normaliser(identifiant, resultat)
        self._cache[identifiant] = extrait
        return extrait

    def pages(self, document: dict[str, Any]) -> int:
        return int(document.get("pages", 1))

    @staticmethod
    def normaliser(identifiant: str, resultat: dict[str, Any]) -> dict[str, Any]:
        """Map a Data Automation answer onto the frozen extraction shape."""
        return {
            "document_id": identifiant,
            "confiance": float(resultat.get("confidence", 0.0)),
            "champs": dict(resultat.get("fields", {})),
            "tableaux": list(resultat.get("tables", [])),
            "categories_sensibles_detectees": list(resultat.get("sensitiveCategories", [])),
        }
