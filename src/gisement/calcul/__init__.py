"""The economic engine of Gisement (chapter 13, annex A).

Public API:

    from gisement.calcul import calculer, entree_depuis_spec, statistiques

Nothing here talks to a model, and nothing here returns a float (ENF-13).
"""

from __future__ import annotations

from gisement.calcul.corrections import (
    coefficient_fragmentation,
    decomposer_cout,
    delai_retour,
    ecart_au_naif,
    occurrences_effectives,
    temps_brut,
    temps_fragmente,
    temps_ineliminable,
    temps_net,
    temps_transfere,
)
from gisement.calcul.incertitudes import incertitudes
from gisement.calcul.monte_carlo import intervalle, quantile, simuler
from gisement.calcul.moteur import (
    calculer,
    calculer_portefeuille,
    entree_depuis_spec,
    entrees_depuis_verite,
    gisement_total,
)
from gisement.calcul.occurrences import (
    amplitude_publiee,
    erreur_type_mediane,
    mediane,
    moyenne,
    statistiques,
)

__all__ = [
    "amplitude_publiee",
    "calculer",
    "calculer_portefeuille",
    "coefficient_fragmentation",
    "decomposer_cout",
    "delai_retour",
    "ecart_au_naif",
    "entree_depuis_spec",
    "entrees_depuis_verite",
    "erreur_type_mediane",
    "gisement_total",
    "incertitudes",
    "intervalle",
    "mediane",
    "moyenne",
    "occurrences_effectives",
    "quantile",
    "simuler",
    "statistiques",
    "temps_brut",
    "temps_fragmente",
    "temps_ineliminable",
    "temps_net",
    "temps_transfere",
]
