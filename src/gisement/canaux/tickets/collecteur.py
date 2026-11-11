"""Tickets collector.

The ticket is the only channel that carries a **measured** processing time
(9.3): the duration comes from the timestamps of the tool, not from an
estimate. Its fingerprint is built on the subject alone - the canonical
gesture - so that two occurrences of the same request group together.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.canaux import commun
from gisement.canaux.base import ParametresCollecte, Source
from gisement.canaux.tickets.source import SourceItsm
from gisement.types.communs import Canal, StatutDuree
from gisement.types.mesure import Activite

SPEC = commun.SpecCanal(
    canal=Canal.TICKETS,
    chemin="tickets/tickets.jsonl",
    kind=commun.KIND_JSONL,
    champs_signature=("sujet",),
    champs_texte=("sujet", "description"),
    champ_duree="duree_traitement_minutes",
    statut_duree=StatutDuree.MESUREE,
)


def source_fichiers(racine: str | Path) -> Source:
    return commun.source_fichiers(SPEC, racine)


def source_itsm(client: Any, requete: str = "") -> Source:
    """The real ITSM adapter (Jira, ServiceNow, Freshservice...)."""
    return SourceItsm(client, Canal.TICKETS, requete)


def collecter(source: Source, parametres: ParametresCollecte) -> tuple[tuple[Activite, ...], dict]:
    return commun.collecter(SPEC, source, parametres)


def mesurer_volume(source: Source) -> int:
    return commun.mesurer_volume(source)


def couverture(activites: Sequence[Activite], declare_heures: Decimal) -> Decimal:
    return commun.couverture(activites, declare_heures)
