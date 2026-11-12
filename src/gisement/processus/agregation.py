"""Aggregation of the measured motifs into declared processes (EF-24).

One declared process = one primary motif in one service. When the channels saw
nothing of a process - a quarterly board reporting, a task done on paper - the
declared volume from the interview is used and the report says so, instead of
silently publishing a zero (9.3, 11.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from gisement.calcul.occurrences import statistiques
from gisement.processus.declaration import (
    ORIGINE_DECLAREE,
    ORIGINE_MESUREE,
    ProcessusDeclare,
    entree_gisement,
    processus_de,
)
from gisement.types.communs import arrondi
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
    """Key the measured motifs by (catalogue ref, service).

    Several fingerprint groups can carry the same (ref, service): a real Jira
    has thousands of distinct subjects, and the deterministic fingerprint gives
    one group per subject. Their occurrences are therefore **summed** before the
    process is attached - taking the biggest group alone would publish a zero
    median for a process the channels did observe, and would declare invisible
    what is really measured (the real corpus of `reel/`).
    """
    groupes: dict[tuple[str, str], list[Motif]] = {}
    for motif in motifs:
        if not motif.catalogue_ref:
            continue
        for service in motif.services or ("",):
            groupes.setdefault((motif.catalogue_ref, service), []).append(motif)
    index: dict[tuple[str, str], Motif] = {}
    for cle, couple in groupes.items():
        fusion = _fusionner(couple)
        precedent = index.get(cle)
        if precedent is None or fusion.occurrences.mediane > precedent.occurrences.mediane:
            index[cle] = fusion
    return index


def _fusionner(couple: Sequence[Motif]) -> Motif:
    """One (motif, service) measured over several fingerprint groups."""
    if len(couple) == 1:
        return couple[0]
    series: dict[int, Decimal] = {}
    for motif in couple:
        for index, valeur in enumerate(motif.occurrences.serie):
            series[index] = series.get(index, Decimal(0)) + valeur
    serie = tuple(series[index] for index in sorted(series))
    occurrences = statistiques(serie)
    total = sum(serie, Decimal(0))
    atypiques = sum(motif.part_atypique_nb_cas for motif in couple)
    porteur = max(couple, key=lambda motif: (motif.duree_nb_cas, motif.confiance))
    return replace(
        porteur,
        occurrences=occurrences,
        duree_unitaire_minutes=porteur.duree_unitaire_minutes,
        duree_ecart_minutes=porteur.duree_ecart_minutes,
        duree_nb_cas=int(total),
        part_atypique=arrondi(atypiques / total, 4) if total > 0 else Decimal(0),
        part_atypique_nb_cas=atypiques,
        canaux=tuple(sorted({canal for motif in couple for canal in motif.canaux})),
        services=tuple(sorted({service for motif in couple for service in motif.services})),
        empreintes=tuple(sorted({e for motif in couple for e in motif.empreintes})),
        confiance=max(motif.confiance for motif in couple),
        nouveau=any(motif.nouveau for motif in couple),
    )


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
