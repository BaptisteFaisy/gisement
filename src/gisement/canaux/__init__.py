"""The five observation channels (spec chapter 10).

Each channel is an independent, idempotent collector (EF-10). The registry
below imports them lazily so a channel package can be missing while the others
are already delivered - the lots land in parallel.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

from gisement.canaux.base import (
    ParametresCollecte,
    Source,
    SourceCsv,
    SourceJson,
    SourceJsonl,
    construire_activites,
    heures_mesurees,
)
from gisement.types.communs import Canal

MODULES: dict[Canal, str] = {
    Canal.TICKETS: "gisement.canaux.tickets",
    Canal.COURRIELS: "gisement.canaux.courriels",
    Canal.DOCUMENTS: "gisement.canaux.documents",
    Canal.APPELS: "gisement.canaux.appels",
    Canal.JOURNAUX: "gisement.canaux.journaux",
}

__all__ = [
    "MODULES",
    "ParametresCollecte",
    "Source",
    "SourceCsv",
    "SourceJson",
    "SourceJsonl",
    "collecteur",
    "collecteurs_disponibles",
    "construire_activites",
    "fonction",
    "heures_mesurees",
]


def collecteur(canal: Canal) -> Any:
    """Import and return the module of one channel."""
    return import_module(MODULES[canal])


def collecteurs_disponibles() -> dict[Canal, Any]:
    """The channel modules that are already delivered."""
    disponibles: dict[Canal, Any] = {}
    for canal in Canal:
        try:
            disponibles[canal] = collecteur(canal)
        except ModuleNotFoundError:
            continue
    return disponibles


def fonction(canal: Canal, nom: str) -> Callable[..., Any]:
    """One function of one channel module: `collecter`, `mesurer_volume`, ..."""
    return getattr(collecteur(canal), nom)
