"""One behaviour for the five collectors (EF-10, lot 4-8).

A channel is a specification plus three functions. Everything that is shared
lives here so that the five packages stay thin and cannot drift apart: reading
the source, sanitising, building activities, measuring the volume and the
coverage.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
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
from gisement.types.communs import Canal, StatutDuree, arrondi
from gisement.types.mesure import Activite

KIND_JSONL = "jsonl"
KIND_JSON = "json"
KIND_CSV = "csv"


@dataclass(frozen=True)
class SpecCanal:
    """What a channel reads, and which field carries what."""

    canal: Canal
    chemin: str
    kind: str = KIND_JSONL
    cle_json: str | None = None
    champs_signature: tuple[str, ...] = ()
    champs_texte: tuple[str, ...] = ()
    champ_duree: str | None = None
    statut_duree: StatutDuree = StatutDuree.INFERREE
    facteur_duree: Decimal = Decimal(1)


def source_fichiers(spec: SpecCanal, racine: str | Path) -> Source:
    """The offline source of a channel: the frozen demo corpus."""
    chemin = Path(racine) / spec.chemin
    if spec.kind == KIND_CSV:
        return SourceCsv(chemin, spec.canal)
    if spec.kind == KIND_JSON:
        return SourceJson(chemin, spec.canal, spec.cle_json)
    return SourceJsonl(chemin, spec.canal)


def collecter(
    spec: SpecCanal,
    source: Source,
    parametres: ParametresCollecte,
    avant: Any = None,
) -> tuple[tuple[Activite, ...], dict[str, Any]]:
    """Ingest one channel. Idempotent: same source, same activities.

    `avant` is an optional hook applied to the raw records before sanitisation
    (stratified sampling for emails, consent filtering for calls).
    """
    if avant is None:
        return construire_activites(
            source,
            parametres,
            champs_signature=spec.champs_signature,
            champs_texte=spec.champs_texte or spec.champs_signature,
            champ_duree=spec.champ_duree,
            statut_duree=spec.statut_duree,
            facteur_duree=spec.facteur_duree,
        )
    return construire_activites(
        SourceFiltree(source, avant),
        parametres,
        champs_signature=spec.champs_signature,
        champs_texte=spec.champs_texte or spec.champs_signature,
        champ_duree=spec.champ_duree,
        statut_duree=spec.statut_duree,
        facteur_duree=spec.facteur_duree,
    )


class SourceFiltree:
    """Wraps a source and transforms its record stream before ingestion."""

    def __init__(self, source: Source, transformateur: Any) -> None:
        self._source = source
        self._transformateur = transformateur
        self.canal = source.canal

    def lire(self):
        return self._transformateur(self._source.lire())

    def volume(self) -> int:
        return self._source.volume()


def mesurer_volume(source: Source) -> int:
    """Raw record count, before any filtering (EF-16)."""
    return source.volume()


def couverture(activites: Sequence[Activite], declare_heures: Decimal) -> Decimal:
    """Share of the declared work volume this channel measures (10.3)."""
    if declare_heures <= 0:
        return Decimal(0)
    return arrondi(heures_mesurees(activites) / declare_heures, 4)
