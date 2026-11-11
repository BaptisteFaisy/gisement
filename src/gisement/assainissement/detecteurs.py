"""PII detectors: an offline lexical reference and the Amazon Comprehend adapter.

Comprehend is the service that applies the sensitive filter in production
(chapter 20.2). The lexical detector is the reference implementation used by
every test: it must produce the same shape, so the two can be swapped without
touching a collector (spec 26.4 - no AWS call during development).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gisement.assainissement.pseudonymisation import (
    REGEX_PII,
    OccurrencePii,
    pseudonyme,
    pseudonymiser_texte,
)
from gisement.assainissement.sensibles import detecter_categories

#: Amazon Comprehend PII types mapped onto the project's own categories.
COMPREHEND_PII = {
    "EMAIL": "email",
    "PHONE": "telephone",
    "SSN": "numero_securite_sociale",
    "IBAN": "iban",
    "NAME": "personne",
    "ADDRESS": "adresse",
    "BANK_ACCOUNT_NUMBER": "iban",
    "DRIVER_ID": "matricule",
    "LICENSE_PLATE": "matricule",
    "PASSPORT_NUMBER": "matricule",
    "NATIONAL_IDENTIFICATION_NUMBER": "matricule",
}


@runtime_checkable
class DetecteurPii(Protocol):
    """Detects personal identifiers in a text."""

    nom: str

    def detecter(self, texte: str) -> tuple[OccurrencePii, ...]:
        """Occurrences found, with the pseudonym that will replace them."""
        ...


class DetecteurLexical:
    """Offline detector: regular expressions plus an explicit list of names."""

    nom = "lexical"

    def __init__(self, cle: str | bytes, sel: str = "", noms: tuple[str, ...] = ()) -> None:
        self.cle = cle
        self.sel = sel
        self.noms = tuple(noms)

    def detecter(self, texte: str) -> tuple[OccurrencePii, ...]:
        if not texte:
            return ()
        _, occurrences = pseudonymiser_texte(texte, self.cle, self.sel, self.noms)
        return occurrences

    def categories_sensibles(self, texte: str) -> tuple[str, ...]:
        return detecter_categories(texte)


class ComprehendDetecteur:
    """Amazon Comprehend adapter. Never instantiated by a test.

    The client is injected so the unit test of the mapping uses a fake:

        DetecteurPii.detecter() -> tuple[OccurrencePii, ...]
    """

    nom = "comprehend"

    def __init__(self, client: object, langue: str = "fr", cle: str | bytes = "", sel: str = "") -> None:
        self._client = client
        self._langue = langue
        self._cle = cle
        self._sel = sel

    def detecter(self, texte: str) -> tuple[OccurrencePii, ...]:
        if not texte:
            return ()
        reponse = self._client.detect_pii_entities(Text=texte, LanguageCode=self._langue)  # type: ignore[attr-defined]
        return self.convertir(reponse)

    def convertir(self, reponse: dict) -> tuple[OccurrencePii, ...]:
        """Map a Comprehend answer onto the project's own categories."""
        occurrences: list[OccurrencePii] = []
        for entite in reponse.get("Entities", ()):
            categorie = COMPREHEND_PII.get(entite.get("Type", ""), "autre")
            debut = int(entite.get("BeginOffset", 0))
            fin = int(entite.get("EndOffset", 0))
            occurrences.append(
                OccurrencePii(
                    categorie=categorie,
                    valeur_pseudonymisee=pseudonyme(f"{categorie}:{debut}:{fin}", self._cle, self._sel),
                    debut=debut,
                    fin=fin,
                )
            )
        return tuple(occurrences)


def categories_depuis_comprehend(reponse: dict) -> tuple[str, ...]:
    """Sensitive categories of a Comprehend answer, in the canonical order."""
    return detecter_categories(" ".join(str(e.get("Type", "")) for e in reponse.get("Entities", ())))


def regex_pii_disponibles() -> tuple[str, ...]:
    """The categories the lexical detector recognises by pattern."""
    return tuple(categorie for categorie, _ in REGEX_PII)
