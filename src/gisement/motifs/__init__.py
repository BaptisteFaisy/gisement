"""The motif catalogue (annex B): forty motifs in eight families, as data."""

from __future__ import annotations

from gisement.motifs.catalogue import (
    COMPTES_PAR_FAMILLE,
    RACINE_CATALOGUE,
    CandidatMotif,
    Catalogue,
    MotifCatalogue,
    charger_catalogue,
    motif_depuis_dict,
)
from gisement.motifs.recherche import candidats, meilleur_candidat, score_motif
from gisement.motifs.validation import nombres_valides, refs_en_double, valider_catalogue

__all__ = [
    "COMPTES_PAR_FAMILLE",
    "RACINE_CATALOGUE",
    "CandidatMotif",
    "Catalogue",
    "MotifCatalogue",
    "candidats",
    "charger_catalogue",
    "meilleur_candidat",
    "motif_depuis_dict",
    "nombres_valides",
    "refs_en_double",
    "score_motif",
    "valider_catalogue",
]
