"""Shared plumbing of the real connectors (idea #8).

A connector's only job is to translate a vendor's payload into the frozen
schema of `docs/CONTRACTS.md` section 5. Everything after that - sanitisation,
fingerprinting, measurement - is the same for every source, which is what makes
a new channel a data question rather than an engineering one.

The HTTP client is injected: in production it is an authenticated session, in
tests it is `FauxClientHttp` with canned pages. No connector is ever pointed at
a real system from CI.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable

CLEFS_SUIVANTES = ("next", "nextPage", "link", "nextPageToken", "offset")


@runtime_checkable
class ClientHttp(Protocol):
    """The only thing a connector needs from the network."""

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """One page of results."""
        ...


class FauxClientHttp:
    """Canned pages for tests: `pages[url]` is the list of records of that page."""

    def __init__(self, pages: dict[str, list[dict[str, Any]]], liens: dict[str, str] | None = None):
        self.pages = pages
        self.liens = liens or {}
        self.appels: list[str] = []

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.appels.append(url)
        valeurs = list(self.pages.get(url, []))
        suivant = self.liens.get(url)
        reponse: dict[str, Any] = {"values": valeurs}
        if suivant:
            reponse["next"] = suivant
        return reponse


def paginer(
    client: ClientHttp, url: str, cle_page: str = "values", max_pages: int = 100
) -> Iterator[dict[str, Any]]:
    """Follow the pagination cursor, with a bound.

    A connector that loops forever is a bug, not a feature: `max_pages` turns an
    infinite cursor into a loud stop.
    """
    courant: str | None = url
    pages = 0
    while courant and pages < max_pages:
        reponse = client.get(courant)
        yield from reponse.get(cle_page, []) or []
        courant = _suivant(reponse)
        pages += 1


def _suivant(reponse: dict[str, Any]) -> str | None:
    for cle in CLEFS_SUIVANTES:
        valeur = reponse.get(cle)
        if isinstance(valeur, str) and valeur:
            return valeur
    return None


def _texte(valeur: Any) -> str:
    return "" if valeur is None else str(valeur)


def _minutes(depuis: Any, jusqu: Any) -> float | None:
    """Minutes between two ISO timestamps, or None when either is missing."""
    from datetime import datetime

    try:
        debut = datetime.fromisoformat(_texte(depuis).replace("Z", "+00:00"))
        fin = datetime.fromisoformat(_texte(jusqu).replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((fin - debut).total_seconds() / 60.0, 1)


def normaliser_ticket(brut: dict[str, Any], source: str) -> dict[str, Any]:
    """Vendor ticket -> the frozen ticket schema."""
    champs = brut.get("fields", brut)
    return {
        "id": _texte(brut.get("key") or brut.get("number") or brut.get("id")),
        "horodatage": _texte(champs.get("created") or champs.get("opened_at") or brut.get("horodatage")),
        "service": _texte(
            champs.get("project", {}).get("key")
            if isinstance(champs.get("project"), dict)
            else champs.get("project") or champs.get("service") or ""
        ),
        "site": _texte(champs.get("site") or ""),
        "agent": _texte(_nom(champs.get("assignee") or champs.get("assigned_to"))),
        "sujet": _texte(champs.get("summary") or champs.get("short_description") or ""),
        "description": _texte(champs.get("description") or ""),
        "systeme": source,
        "duree_traitement_minutes": _minutes(
            champs.get("created") or champs.get("opened_at"),
            champs.get("resolutiondate") or champs.get("resolved_at"),
        ),
        "statut": _texte(
            champs.get("status", {}).get("name")
            if isinstance(champs.get("status"), dict)
            else champs.get("status") or champs.get("state") or ""
        ),
        "allers_retours": int(
            champs.get("comment", {}).get("total", 0)
            if isinstance(champs.get("comment"), dict)
            else champs.get("allers_retours", 0) or 0
        ),
        "groupe": _texte(champs.get("groupe") or champs.get("group") or ""),
    }


def _nom(valeur: Any) -> str:
    if isinstance(valeur, dict):
        return _texte(valeur.get("displayName") or valeur.get("name") or valeur.get("value"))
    return _texte(valeur)


def normaliser_journal(brut: dict[str, Any], source: str) -> dict[str, Any]:
    """ERP export line -> the frozen journal schema."""
    return {
        "horodatage": _texte(brut.get("date") or brut.get("Date") or brut.get("horodatage")),
        "service": _texte(brut.get("service") or brut.get("centre") or ""),
        "action": _texte(brut.get("operation") or brut.get("Operation") or brut.get("action") or ""),
        "entite": _texte(brut.get("compte") or brut.get("entite") or brut.get("Amount") or ""),
        "systeme": source,
        "groupe": _texte(brut.get("utilisateur") or brut.get("User") or brut.get("groupe") or ""),
        "duree_secondes": _secondes(brut.get("duree_secondes") or brut.get("Duration")),
    }


def _secondes(valeur: Any) -> int | None:
    try:
        return int(float(valeur))
    except (TypeError, ValueError):
        return None
