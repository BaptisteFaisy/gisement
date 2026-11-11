"""Monthly occurrence statistics: the median, never the mean (13.1 correction 4).

A volume measured on a peak month is not a monthly volume. The median of the
window is the figure that feeds the economic model; the seasonal amplitude is
published next to it, never hidden (R11).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from gisement.types.communs import arrondi, decimal
from gisement.types.mesure import OccurrencesMensuelles


def mediane(valeurs: Sequence[Decimal]) -> Decimal:
    """Median of a sorted sample, average of the two central values if even."""
    if not valeurs:
        return Decimal(0)
    tries = sorted(valeurs)
    milieu = len(tries) // 2
    if len(tries) % 2:
        return tries[milieu]
    return (tries[milieu - 1] + tries[milieu]) / 2


def ecart_type(valeurs: Sequence[Decimal]) -> Decimal:
    """Sample standard deviation (n - 1): the window is a sample, not a population."""
    if len(valeurs) < 2:
        return Decimal(0)
    moyenne = sum(valeurs, Decimal(0)) / Decimal(len(valeurs))
    carres = sum(((v - moyenne) ** 2 for v in valeurs), Decimal(0))
    variance = carres / Decimal(len(valeurs) - 1)
    return arrondi(variance.sqrt(), 2)


def racine_carree(valeur: Decimal) -> Decimal:
    """Square root of a Decimal, four decimals: enough for a standard error."""
    if valeur <= 0:
        return Decimal(0)
    return arrondi(valeur.sqrt(), 4)


def statistiques(serie: Sequence[Decimal | int | str]) -> OccurrencesMensuelles:
    """Build the monthly statistics of a channel from its raw counts."""
    valeurs = tuple(decimal(v) for v in serie)
    if not valeurs:
        return OccurrencesMensuelles()
    brute = ecart_type(valeurs)
    return OccurrencesMensuelles(
        serie=valeurs,
        mediane=mediane(valeurs),
        minimum=min(valeurs),
        maximum=max(valeurs),
        ecart_type=arrondi(brute, 2),
        nb_mois=len(valeurs),
    )


def erreur_type_mediane(occurrences: OccurrencesMensuelles) -> Decimal:
    """Standard error of the median over the window (decision D-14).

    `sigma / sqrt(n)` for the mean, times the 1.25 factor of the median's
    asymptotic efficiency on a normal sample. This is what the Monte-Carlo
    draws: a duration measured on 1 840 cases is not uncertain by +/-20 %.
    """
    if occurrences.nb_mois <= 0:
        return Decimal(0)
    return racine_carree(occurrences.ecart_type**2 / Decimal(occurrences.nb_mois))


def moyenne(valeurs: Sequence[Decimal]) -> Decimal:
    """The mean, published next to the median to show the trap (R11)."""
    if not valeurs:
        return Decimal(0)
    return arrondi(sum(valeurs, Decimal(0)) / Decimal(len(valeurs)), 2)


def amplitude_publiee(occurrences: OccurrencesMensuelles) -> str:
    """The seasonal amplitude as it is printed in a report: "[210 - 465]"."""
    return f"[{occurrences.minimum} - {occurrences.maximum}]"
