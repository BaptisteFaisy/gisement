"""Declared processes and their aggregation with the measured motifs (lot 11).

The perimeter is declared by the sponsor before the measure starts (11.1): the
processes exist in the client's organisation, Gisement does not invent them -
it attaches a measured volume to each of them, and says which ones it could not
see in the channels.

Aggregation is keyed on **primary motif + service**: the ground truth
guarantees that two processes of one service never share a primary motif, and
the classifier groups on the same key (lot 10).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from gisement.types.communs import Canal, Repartition, StatutDuree, decimal
from gisement.types.economie import (
    ComposanteTransfert,
    CoutAutomatisation,
    EntreeGisement,
    FaitsFaisabilite,
)
from gisement.types.mesure import Motif, OccurrencesMensuelles, Processus, StatutValidation

ORIGINE_MESUREE = "mesuree"
ORIGINE_DECLAREE = "declaree"


@dataclass(frozen=True)
class ProcessusDeclare:
    """One process of the declared perimeter, with what the MSP knows of it."""

    id: str
    nom: str
    nom_en: str
    service: str
    motif_primaire: str
    motifs: tuple[str, ...]
    canaux: tuple[Canal, ...]
    famille_poste: str
    procedure_ref: str
    changements_douze_mois: int
    visibilite_dirigeant: bool
    faits: FaitsFaisabilite
    cout: CoutAutomatisation
    transfert: tuple[ComposanteTransfert, ...]
    part_volume_traitee: Decimal
    suppression_etape: bool
    declare: dict = field(default_factory=dict)
    """Fallback measure, used when the channels saw nothing (9.3, 11.3)."""


def _composantes(bruts: list[dict]) -> tuple[ComposanteTransfert, ...]:
    return tuple(
        ComposanteTransfert(
            nom=b["nom"],
            taux=decimal(b["taux"]) if b.get("taux") is not None else None,
            duree_minutes=decimal(b["duree_minutes"]) if b.get("duree_minutes") is not None else None,
            forfait_heures=(decimal(b["forfait_heures"]) if b.get("forfait_heures") is not None else None),
        )
        for b in bruts
    )


def declare_depuis_dict(brut: dict) -> ProcessusDeclare:
    """One declared process, from the perimeter file."""
    cout = brut["cout"]
    return ProcessusDeclare(
        id=brut["id"],
        nom=brut["nom"],
        nom_en=brut.get("nom_en", brut["nom"]),
        service=brut["service"],
        motif_primaire=brut["motifs"][0],
        motifs=tuple(brut["motifs"]),
        canaux=tuple(Canal(c) for c in brut["canaux"]),
        famille_poste=brut.get("famille_poste", "administratif"),
        procedure_ref=brut.get("procedure_ref", ""),
        changements_douze_mois=int(brut.get("changements_douze_mois", 0)),
        visibilite_dirigeant=bool(brut.get("visibilite_dirigeant", False)),
        faits=FaitsFaisabilite(**brut.get("faits", {})),
        cout=CoutAutomatisation(
            jours=decimal(cout["jours"]),
            tjm=decimal(cout["tjm"]),
            abonnement_mensuel=decimal(cout["abonnement_mensuel"]),
            taux_maintenance=decimal(cout["taux_maintenance"]),
        ),
        transfert=_composantes(brut.get("transfert", [])),
        part_volume_traitee=decimal(brut.get("part_volume_traitee", 1)),
        suppression_etape=bool(brut.get("suppression_etape", False)),
        declare=brut,
    )


def charger_declaration(chemin: str | Path) -> tuple[ProcessusDeclare, ...]:
    """Load the declared perimeter from `demo/spec-processus.json`."""
    document = json.loads(Path(chemin).read_text(encoding="utf-8"))
    return tuple(declare_depuis_dict(brut) for brut in document["processus"])


def processus_de(declare: ProcessusDeclare, campagne_id: str, motif: Motif | None) -> Processus:
    """The contract's `Processus`, filled from the declaration and the measure."""
    return Processus(
        id=declare.id,
        campagne_id=campagne_id,
        nom=declare.nom,
        service=declare.service,
        motif_ids=tuple(declare.motifs),
        validation=StatutValidation.EN_ATTENTE,
        canaux=tuple(motif.canaux) if motif else declare.canaux,
        famille_poste=declare.famille_poste,
        changements_douze_mois=declare.changements_douze_mois,
        visibilite_dirigeant=declare.visibilite_dirigeant,
        saisonnier=bool(declare.declare.get("piege") == "pic_saisonnier"),
    )


def occurrences_declarees(declare: ProcessusDeclare) -> OccurrencesMensuelles:
    """The declared volume, used when the channels saw nothing of the process."""
    brut = declare.declare.get("occurrences", {})
    return OccurrencesMensuelles(
        serie=tuple(decimal(v) for v in brut.get("serie", ())),
        mediane=decimal(brut.get("mediane", 0)),
        minimum=decimal(brut.get("minimum", 0)),
        maximum=decimal(brut.get("maximum", 0)),
        ecart_type=decimal(brut.get("ecart_type", 0)),
        nb_mois=int(brut.get("nb_mois", 0)),
    )


@dataclass(frozen=True)
class _FaitsMesure:
    """The measured side of an engine input, wherever it came from."""

    occurrences: OccurrencesMensuelles
    duree: Decimal
    statut: StatutDuree
    ecart: Decimal
    nb_cas: int
    repartition: Repartition
    atypique: Decimal
    nb_atypiques: int


def _faits_depuis_motif(motif: Motif) -> _FaitsMesure:
    return _FaitsMesure(
        occurrences=motif.occurrences,
        duree=motif.duree_unitaire_minutes,
        statut=motif.duree_statut,
        ecart=motif.duree_ecart_minutes,
        nb_cas=motif.duree_nb_cas,
        repartition=motif.repartition,
        atypique=motif.part_atypique,
        nb_atypiques=motif.part_atypique_nb_cas,
    )


def _faits_depuis_declaration(declare: ProcessusDeclare) -> _FaitsMesure:
    """The interview's figures, used when the channels saw nothing (9.3)."""
    brut = declare.declare
    return _FaitsMesure(
        occurrences=occurrences_declarees(declare),
        duree=decimal(brut.get("duree_unitaire_minutes", 0)),
        statut=StatutDuree.INFERREE,
        ecart=decimal(brut.get("duree_ecart_minutes", 0)),
        nb_cas=int(brut.get("duree_nb_cas", 0)),
        repartition=Repartition(brut.get("repartition", "diffuse")),
        atypique=decimal(brut.get("part_atypique", 0)),
        nb_atypiques=int(brut.get("part_atypique_nb_cas", 0)),
    )


def entree_gisement(
    declare: ProcessusDeclare,
    motif: Motif | None,
    taux_horaire: Decimal | None,
    graine: int,
) -> tuple[EntreeGisement, str]:
    """Build the engine's input from the measure, or from the declaration.

    Returns the input and its origin: `mesuree` when a motif of the corpus
    carries the volume, `declaree` when the channels saw nothing and the volume
    comes from the interview. The report never mixes the two (9.3).
    """
    mesure = motif is not None and motif.occurrences.mediane > 0
    faits = _faits_depuis_motif(motif) if mesure else _faits_depuis_declaration(declare)
    entree = EntreeGisement(
        processus_id=declare.id,
        part_volume_traitee=declare.part_volume_traitee,
        suppression_etape=declare.suppression_etape,
        occurrences=faits.occurrences,
        duree_unitaire_minutes=faits.duree,
        duree_statut=faits.statut,
        duree_ecart_minutes=faits.ecart,
        duree_nb_cas=faits.nb_cas,
        repartition=faits.repartition,
        part_atypique=faits.atypique,
        part_atypique_nb_cas=faits.nb_atypiques,
        transfert=declare.transfert,
        taux_horaire=taux_horaire,
        cout=declare.cout,
        faits=declare.faits,
        graine=graine,
    )
    return entree, (ORIGINE_MESUREE if mesure else ORIGINE_DECLAREE)
