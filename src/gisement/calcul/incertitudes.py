"""Where the uncertainty comes from (17.2, decisions D-02 and D-14).

Three sources, each measured rather than guessed:
  - sampling: the standard error of the monthly counts over the window;
  - unit duration: measured standard error, or a prudent +/-40 % band when the
    duration was inferred instead of measured;
  - model corrections: the fragmentation coefficient and the review rates are
    bounded by a band, not fixed at a single value.

A duration measured on 1 840 cases is not uncertain by 20 %: the spread comes
from `sigma / sqrt(n)`, which is what makes the published interval honest.
"""

from __future__ import annotations

from decimal import Decimal

from gisement.calcul.occurrences import erreur_type_mediane
from gisement.types.communs import (
    DUREE_INFEREE_MARGE,
    INCERTITUDE_FRAGMENTATION,
    INCERTITUDE_TAUX_RELATIVE,
    FormeIncertitude,
    StatutDuree,
    arrondi,
)
from gisement.types.economie import EntreeGisement, Incertitude

#: An atypical share measured on at least this many cases is trusted at 2 %.
SEUIL_CAS_ATYPIQUES = 100
ECART_ATYPIQUE_MESURE = Decimal("0.02")
ECART_ATYPIQUE_ESTIME = Decimal("0.05")


def incertitude_occurrences(entree: EntreeGisement) -> Incertitude:
    return Incertitude(
        nom="occurrences",
        forme=FormeIncertitude.NORMALE,
        centre=entree.occurrences.mediane,
        ecart=erreur_type_mediane(entree.occurrences),
    )


def incertitude_duree(entree: EntreeGisement) -> Incertitude:
    if entree.duree_statut == StatutDuree.MESUREE and entree.duree_nb_cas > 0:
        ecart = entree.duree_ecart_minutes / Decimal(entree.duree_nb_cas).sqrt()
        forme = FormeIncertitude.NORMALE
    else:
        ecart = entree.duree_unitaire_minutes * DUREE_INFEREE_MARGE
        forme = FormeIncertitude.UNIFORME
    return Incertitude(
        nom="duree_unitaire", forme=forme, centre=entree.duree_unitaire_minutes, ecart=arrondi(ecart, 4)
    )


def incertitude_fragmentation(entree: EntreeGisement) -> Incertitude:
    from gisement.calcul.corrections import coefficient_fragmentation

    return Incertitude(
        nom="coefficient_fragmentation",
        forme=FormeIncertitude.UNIFORME,
        centre=coefficient_fragmentation(entree.repartition),
        ecart=INCERTITUDE_FRAGMENTATION,
    )


def incertitude_atypique(entree: EntreeGisement) -> Incertitude:
    ecart = (
        ECART_ATYPIQUE_MESURE if entree.part_atypique_nb_cas >= SEUIL_CAS_ATYPIQUES else ECART_ATYPIQUE_ESTIME
    )
    return Incertitude(
        nom="part_atypique",
        forme=FormeIncertitude.NORMALE,
        centre=entree.part_atypique,
        ecart=ecart,
    )


def incertitudes_taux(entree: EntreeGisement) -> dict[str, Incertitude]:
    """One band per transfer component that carries a rate."""
    resultats: dict[str, Incertitude] = {}
    for composante in entree.transfert:
        if composante.taux is None:
            continue
        resultats[f"taux:{composante.nom}"] = Incertitude(
            nom=f"taux:{composante.nom}",
            forme=FormeIncertitude.UNIFORME,
            centre=composante.taux,
            ecart=composante.taux * INCERTITUDE_TAUX_RELATIVE,
        )
    return resultats


def incertitudes(entree: EntreeGisement) -> dict[str, Incertitude]:
    """Every distribution the Monte-Carlo draws from, keyed by name."""
    toutes = {
        "occurrences": incertitude_occurrences(entree),
        "duree_unitaire": incertitude_duree(entree),
        "coefficient_fragmentation": incertitude_fragmentation(entree),
        "part_atypique": incertitude_atypique(entree),
    }
    toutes.update(incertitudes_taux(entree))
    return toutes
