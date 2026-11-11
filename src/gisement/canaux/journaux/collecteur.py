"""Application logs collector.

Logs are the only channel that gives an **exact** volume when they exist, and
the only one that shows seasonality without sampling (10.2). Their limit is
their coverage: they only exist for the systems that produce them, which is why
the coverage is published per channel and globally (10.3, EF-16).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.canaux import commun
from gisement.canaux.base import ParametresCollecte, Source
from gisement.canaux.journaux.source import SourceErp
from gisement.types.communs import Canal, StatutDuree
from gisement.types.mesure import Activite

FACTEUR_SECONDES = Decimal(1) / Decimal(60)

SPEC = commun.SpecCanal(
    canal=Canal.JOURNAUX,
    chemin="journaux/journaux.csv",
    kind=commun.KIND_CSV,
    champs_signature=("action",),
    champs_texte=("action", "entite"),
    champ_duree="duree_secondes",
    statut_duree=StatutDuree.MESUREE,
    facteur_duree=FACTEUR_SECONDES,
)


def source_fichiers(racine: str | Path) -> Source:
    return commun.source_fichiers(SPEC, racine)


def source_erp(client: Any, export: str = "") -> Source:
    """The real adapter over an ERP / business application export."""
    return SourceErp(client, Canal.JOURNAUX, export)


def collecter(source: Source, parametres: ParametresCollecte) -> tuple[tuple[Activite, ...], dict]:
    return commun.collecter(SPEC, source, parametres)


def mesurer_volume(source: Source) -> int:
    return commun.mesurer_volume(source)


def couverture(activites: Sequence[Activite], declare_heures: Decimal) -> Decimal:
    return commun.couverture(activites, declare_heures)
