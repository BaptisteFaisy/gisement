"""Pseudonymisation applied at ingestion, before any model sees the data.

R3 (chapter 18): direct identifiers are replaced by a pseudonym that is not
reversible without the key. The pseudonym is an HMAC-SHA256 truncated to 16
hex characters, salted per campaign, so the same person maps to the same
pseudonym inside one campaign and to nothing recognisable outside it.

The mapping table (pseudonym -> real identity) is kept apart, encrypted, and
destroyed at the end of the campaign (ENF-06). Nothing here ever stores it.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

PREFIXE_PSEUDONYME = "PSD-"
LONGUEUR_EMPREINTE = 16

#: What a person identifier can look like in the five channels.
REGEX_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
REGEX_TELEPHONE = re.compile(r"(?<!\d)(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}(?!\d)")
REGEX_NIR = re.compile(r"(?<!\d)[12]\s?\d{2}\s?\d{2}\s?\d{2,3}\s?\d{3}\s?\d{2}(?!\d)")
REGEX_IBAN = re.compile(r"\bFR\d{2}\s?(?:\d{5}\s?\d{5}\s?\d{11,13})\b")
REGEX_MATRICULE = re.compile(r"\b(?:M|MAT|EMP)-\d{3,6}\b")

REGEX_PII: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", REGEX_EMAIL),
    ("telephone", REGEX_TELEPHONE),
    ("numero_securite_sociale", REGEX_NIR),
    ("iban", REGEX_IBAN),
    ("matricule", REGEX_MATRICULE),
)


@dataclass(frozen=True)
class OccurrencePii:
    """One detected personal identifier, already replaced in the text."""

    categorie: str
    valeur_pseudonymisee: str
    debut: int
    fin: int


def _octets(cle: str | bytes) -> bytes:
    return cle.encode("utf-8") if isinstance(cle, str) else cle


def pseudonyme(identifiant: str, cle: str | bytes, sel: str = "") -> str:
    """Non-reversible pseudonym of a direct identifier."""
    message = f"{sel}|{identifiant}".encode()
    empreinte = hmac.new(_octets(cle), message, hashlib.sha256).hexdigest()
    return PREFIXE_PSEUDONYME + empreinte[:LONGUEUR_EMPREINTE]


#: Canonical abbreviations: a group label must stay readable in a report.
ABREVIATIONS_SERVICE: dict[str, str] = {
    "approvisionnements": "APPRO",
    "adv": "ADV",
    "administration_des_ventes": "ADV",
    "comptabilite": "COMPTA",
    "support": "SUPPORT",
    "support_client": "SUPPORT",
    "ressources_humaines": "RH",
    "direction": "DIR",
}


def groupe_pseudonyme(service: str, site: str = "", equipe: str = "") -> str:
    """A group label such as "ADV-JOUR": never a person, always a collective."""
    cle = (service or "").strip().lower().replace(" ", "_")
    racine = ABREVIATIONS_SERVICE.get(cle) or cle.upper()[:6] or "GEN"
    suffixe = (equipe or site or "").strip().upper().replace(" ", "_")[:8]
    return f"{racine}-{suffixe}" if suffixe else racine


def pseudonymiser_texte(
    texte: str, cle: str | bytes, sel: str = "", noms: tuple[str, ...] = ()
) -> tuple[str, tuple[OccurrencePii, ...]]:
    """Replace every personal identifier of a text by its pseudonym.

    `noms` is an explicit list of person names to catch (the demo dataset
    publishes its own generated name list, so the detector never has to guess).
    """
    if not texte:
        return texte, ()
    occurrences: list[OccurrencePii] = []
    resultat = texte
    for categorie, motif in REGEX_PII:
        resultat = _remplacer(resultat, motif, categorie, cle, sel, occurrences)
    for nom in noms:
        if nom and nom in resultat:
            resultat = _remplacer(resultat, re.compile(re.escape(nom)), "personne", cle, sel, occurrences)
    return resultat, tuple(occurrences)


def _remplacer(
    texte: str,
    motif: re.Pattern[str],
    categorie: str,
    cle: str | bytes,
    sel: str,
    occurrences: list[OccurrencePii],
) -> str:
    """Replace every match of one pattern, keeping the offsets of the source."""

    def substituer(correspondance: re.Match[str]) -> str:
        valeur = pseudonyme(correspondance.group(0).strip(), cle, sel)
        occurrences.append(
            OccurrencePii(
                categorie=categorie,
                valeur_pseudonymisee=valeur,
                debut=correspondance.start(),
                fin=correspondance.end(),
            )
        )
        return valeur

    return motif.sub(substituer, texte)


def est_pseudonymise(valeur: object) -> bool:
    """True when a value already carries the pseudonym prefix."""
    return isinstance(valeur, str) and valeur.startswith(PREFIXE_PSEUDONYME)
