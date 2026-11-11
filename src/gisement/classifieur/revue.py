"""Human review of what the classifier is not sure about (21.2, EF-24).

A group below the confidence threshold, a proposed motif, an atypical process:
all of it goes to a human, with the reason. Three hours of interview on
measured facts beat fifteen days of workshops on impressions (9.1) - but the
facts still need a human to say "yes, that is how we work".
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from gisement.types.communs import SEUIL_CONFIANCE_CLASSIFICATION
from gisement.types.mesure import Motif, Processus, RevueHumaine, StatutValidation

#: Share of atypical cases above which a process is worth a human look.
SEUIL_ATYPIQUE_REVUE = Decimal("0.30")


def a_revoir(motifs: Sequence[Motif], campagne_id: str = "") -> tuple[RevueHumaine, ...]:
    """Every motif that needs a human decision, with its reason."""
    revues: list[RevueHumaine] = []
    for motif in motifs:
        raison = raison_revue(motif)
        if raison:
            revues.append(
                RevueHumaine(
                    id=f"REV-{motif.id}",
                    campagne_id=campagne_id or motif.campagne_id,
                    objet=motif.id,
                    raison=raison,
                    confiance=motif.confiance,
                )
            )
    return tuple(revues)


def raison_revue(motif: Motif) -> str:
    if motif.nouveau:
        return "motif absent du catalogue : a valider et a proposer au catalogue (EF-21)"
    if motif.confiance < SEUIL_CONFIANCE_CLASSIFICATION:
        return f"confiance {motif.confiance} inferieure au seuil {SEUIL_CONFIANCE_CLASSIFICATION}"
    if motif.part_atypique > SEUIL_ATYPIQUE_REVUE:
        return f"part de cas atypiques {motif.part_atypique} : le motif dominant est douteux"
    if motif.occurrences.mediane <= 0:
        return "aucune occurrence mesuree : le groupe est probablement du bruit"
    return ""


def processus_a_valider(processus: Sequence[Processus]) -> tuple[Processus, ...]:
    """EF-24 - the aggregation is submitted to the service manager."""
    return tuple(p for p in processus if p.validation == StatutValidation.EN_ATTENTE)


def motif_sans_volume(motif: Motif) -> bool:
    return motif.occurrences.mediane <= 0
