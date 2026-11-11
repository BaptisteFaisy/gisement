"""Documents collector.

Documents show the artefacts, not the activity (10.2): the re-keyed form, the
hand kept spreadsheet, the procedure nobody follows. The collector reads the
frozen extractions, drops the documents that carry a sensitive category before
storage (EF-12), and counts the pages it would bill (KPI-8, annex G.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.canaux import commun
from gisement.canaux.base import ParametresCollecte, Source
from gisement.canaux.documents.data_automation import ExtractionFigee
from gisement.canaux.documents.source import SourceDocuments
from gisement.types.communs import Canal, StatutDuree
from gisement.types.mesure import Activite

SPEC = commun.SpecCanal(
    canal=Canal.DOCUMENTS,
    chemin="documents/documents.json",
    kind=commun.KIND_JSON,
    champs_signature=("titre",),
    champs_texte=("titre", "texte_libre"),
    champ_duree=None,
    statut_duree=StatutDuree.INFERREE,
)


def source_fichiers(racine: str | Path, extracteur: Any = None) -> Source:
    return SourceDocuments(racine, extracteur or ExtractionFigee(racine))


def collecter(source: Source, parametres: ParametresCollecte) -> tuple[tuple[Activite, ...], dict]:
    activites, rapport = commun.collecter(SPEC, source, parametres)
    rapport["pages_extraites"] = getattr(source, "pages_extraites", 0)
    return activites, rapport


def mesurer_volume(source: Source) -> int:
    return commun.mesurer_volume(source)


def couverture(activites: Sequence[Activite], declare_heures: Decimal) -> Decimal:
    return commun.couverture(activites, declare_heures)
