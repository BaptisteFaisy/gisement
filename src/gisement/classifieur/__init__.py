"""The motif classifier (lot 10): deterministic fingerprint first, model second."""

from __future__ import annotations

from gisement.classifieur.etiquetage import (
    SCHEMA_ETIQUETAGE,
    etiqueter,
    etiquette_groupe,
    invite_etiquetage,
)
from gisement.classifieur.groupes import (
    comptes_mensuels,
    grouper,
    inferer_repartition,
    part_atypique,
)
from gisement.classifieur.nouveaux import proposer_nouveau_motif, proposition, sont_nouveaux
from gisement.classifieur.revue import a_revoir, processus_a_valider, raison_revue

__all__ = [
    "SCHEMA_ETIQUETAGE",
    "a_revoir",
    "comptes_mensuels",
    "etiqueter",
    "etiquette_groupe",
    "grouper",
    "inferer_repartition",
    "invite_etiquetage",
    "part_atypique",
    "processus_a_valider",
    "proposer_nouveau_motif",
    "proposition",
    "raison_revue",
    "sont_nouveaux",
]
