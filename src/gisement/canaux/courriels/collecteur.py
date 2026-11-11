"""Email collector.

Email is the channel that reveals the work no tool traces: requests, hand
overs, chases (10.1). It has no measured duration, so its activities are
flagged as inferred (9.3) and the report says so.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.canaux import commun
from gisement.canaux.base import ParametresCollecte, Source
from gisement.canaux.courriels.echantillonnage import echantillonner_stratifie
from gisement.canaux.courriels.source import SourceMessagerie
from gisement.types.communs import Canal, StatutDuree
from gisement.types.mesure import Activite

SPEC = commun.SpecCanal(
    canal=Canal.COURRIELS,
    chemin="courriels/courriels.jsonl",
    kind=commun.KIND_JSONL,
    champs_signature=("objet",),
    champs_texte=("objet", "corps"),
    champ_duree=None,
    statut_duree=StatutDuree.INFERREE,
)


def source_fichiers(racine: str | Path) -> Source:
    return commun.source_fichiers(SPEC, racine)


def source_messagerie(client: Any, perimetre: str = "") -> Source:
    """The real mailbox adapter (Graph, IMAP, Workspace...)."""
    return SourceMessagerie(client, Canal.COURRIELS, perimetre)


def collecter(
    source: Source, parametres: ParametresCollecte, cible: int | None = None
) -> tuple[tuple[Activite, ...], dict]:
    """Ingest the mailbox, sampling first when a target size is given."""
    if cible is None:
        activites, rapport = commun.collecter(SPEC, source, parametres)
        return activites, rapport

    echantillon: dict[str, Any] = {}

    def filtrer(flux: Iterator[dict]) -> Iterator[dict]:
        brut = list(flux)
        retenus, strates = echantillonner_stratifie(brut, cible, parametres.graine)
        echantillon["cible"] = cible
        echantillon["retenu"] = len(retenus)
        echantillon["strates"] = strates
        return iter(retenus)

    activites, rapport = commun.collecter(SPEC, source, parametres, avant=filtrer)
    rapport.update({f"echantillon_{cle}": valeur for cle, valeur in echantillon.items()})
    return activites, rapport


def mesurer_volume(source: Source) -> int:
    return commun.mesurer_volume(source)


def couverture(activites: Sequence[Activite], declare_heures: Decimal) -> Decimal:
    return commun.couverture(activites, declare_heures)
