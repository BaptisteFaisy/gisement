"""Aggregation of the measured motifs into declared processes (EF-24).

One declared process = one primary motif in one service. When the channels saw
nothing of a process - a quarterly board reporting, a task done on paper - the
declared volume from the interview is used and the report says so, instead of
silently publishing a zero (9.3, 11.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from gisement.processus.declaration import (
    ORIGINE_DECLAREE,
    ORIGINE_MESUREE,
    ProcessusDeclare,
    entree_gisement,
    processus_de,
)
from gisement.types.economie import EntreeGisement
from gisement.types.mesure import Motif, Processus


@dataclass(frozen=True)
class MesureProcessus:
    """A declared process, its measured motif, and the engine's input."""

    declare: ProcessusDeclare
    processus: Processus
    motif: Motif | None
    origine: str
    entree: EntreeGisement

    @property
    def est_mesuree(self) -> bool:
        return self.origine == ORIGINE_MESUREE

    @property
    def est_invisible(self) -> bool:
        """True when no channel saw the process: it is published as such."""
        return self.origine == ORIGINE_DECLAREE


def index_motifs(motifs: Sequence[Motif]) -> dict[tuple[str, str], Motif]:
    """Key the measured motifs by (catalogue ref, service)."""
    index: dict[tuple[str, str], Motif] = {}
    for motif in motifs:
        if not motif.catalogue_ref:
            continue
        for service in motif.services or ("",):
            cle = (motif.catalogue_ref, service)
            precedent = index.get(cle)
            if precedent is None or motif.occurrences.mediane > precedent.occurrences.mediane:
                index[cle] = motif
    return index


def agreger(
    declares: Sequence[ProcessusDeclare],
    motifs: Sequence[Motif],
    campagne_id: str,
    taux_horaire: Decimal | None,
    graine: int = 0,
) -> tuple[MesureProcessus, ...]:
    """Attach a measured volume to every declared process."""
    index = index_motifs(motifs)
    mesures: list[MesureProcessus] = []
    for declare in declares:
        motif = index.get((declare.motif_primaire, declare.service))
        entree, origine = entree_gisement(declare, motif, taux_horaire, graine)
        mesures.append(
            MesureProcessus(
                declare=declare,
                processus=processus_de(declare, campagne_id, motif),
                motif=motif,
                origine=origine,
                entree=entree,
            )
        )
    return tuple(mesures)


def invisibles(mesures: Sequence[MesureProcessus]) -> tuple[MesureProcessus, ...]:
    """The processes the channels did not see (11.3 - the manager can add one)."""
    return tuple(m for m in mesures if m.est_invisible)


def motifs_orphelins(motifs: Sequence[Motif], declares: Sequence[ProcessusDeclare]) -> tuple[Motif, ...]:
    """Measured motifs that no declared process claims: a discovery, not a bug."""
    declares_cles = {(d.motif_primaire, d.service) for d in declares}
    return tuple(
        m
        for m in motifs
        if m.catalogue_ref and not any((m.catalogue_ref, s) in declares_cles for s in m.services)
    )
