"""Calls collector: the coordination work no system traces (10.4)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.canaux import commun
from gisement.canaux.appels.source import SourceAppels
from gisement.canaux.appels.transcribe import TranscriptionsFigees
from gisement.canaux.base import ParametresCollecte, Source
from gisement.types.communs import Canal, StatutDuree
from gisement.types.mesure import Activite

SPEC = commun.SpecCanal(
    canal=Canal.APPELS,
    chemin="appels/appels.json",
    kind=commun.KIND_JSON,
    champs_signature=("sujet",),
    champs_texte=("sujet", "description"),
    champ_duree=None,
    statut_duree=StatutDuree.INFERREE,
)
# A transcript segment is a fragment of a conversation, not the duration of the
# task it mentions: the calls channel contributes volumes and the share of the
# call spent on a gesture (10.4), and the unit duration stays the motif's
# typical one, flagged inferred (9.3). Publishing 36 seconds as the duration of
# "look up a precedent" would be a lie.


def source_fichiers(racine: str | Path, transcripteur: Any = None) -> Source:
    return SourceAppels(racine, transcripteur or TranscriptionsFigees(racine))


def collecter(source: Source, parametres: ParametresCollecte) -> tuple[tuple[Activite, ...], dict]:
    activites, rapport = commun.collecter(SPEC, source, parametres)
    rapport["minutes_transcrites"] = round(getattr(source, "minutes", 0.0), 2)
    rapport["piis_occultees"] = getattr(source, "pii_occultees", 0)
    rapport["exclus_sans_consentement"] = getattr(source, "sans_consentement", 0)
    rapport["nb_appels"] = getattr(source, "nb_appels", 0)
    return activites, rapport


def mesurer_volume(source: Source) -> int:
    return commun.mesurer_volume(source)


def couverture(activites: Sequence[Activite], declare_heures: Decimal) -> Decimal:
    return commun.couverture(activites, declare_heures)
