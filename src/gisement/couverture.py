"""Coverage of the measurement (10.3, EF-16, KPI-3).

A report that does not publish its coverage lies by omission: the first
consultant who reads it proves it in two questions. So the coverage is
computed, published as it is - 62 % is published as 62 % - and accompanied by
the list of what is **not** covered.

The denominator is declared by the service managers: the estimated volume of
repetitive administrative work of the perimeter over the window. The numerator
is what the five channels actually attached to a process, measured where a
timestamp exists and inferred from the motif's typical duration where it does
not (9.3).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from gisement.types.campagne import Couverture
from gisement.types.communs import Canal, arrondi, decimal, pourcentage

#: What the demo client declares is out of reach of the five channels.
NON_COUVERT_DEFAUT: tuple[str, ...] = (
    "travail de terrain (entrepot, livraisons)",
    "reunions non enregistrees",
    "echanges oraux informels",
    "messagerie instantanee hors perimetre",
)


def heures_par_canal(
    heures: Mapping[Canal, Decimal | float | str | int], declare_heures: Decimal
) -> Couverture:
    """Build the coverage object from the hours each channel attached."""
    normalise = {canal: decimal(valeur) for canal, valeur in heures.items()}
    couvert = sum(normalise.values(), Decimal(0))
    return Couverture(
        par_canal={canal: _part(valeur, declare_heures) for canal, valeur in normalise.items()},
        volume_couvert_heures=arrondi(couvert, 1),
        volume_estime_heures=decimal(declare_heures),
        non_couvert=NON_COUVERT_DEFAUT,
    )


def _part(heures: Decimal, declare: Decimal) -> Decimal:
    if declare <= 0:
        return Decimal(0)
    return arrondi(heures / declare, 4)


def couverture_globale(couverture: Couverture) -> Decimal:
    """The global coverage as a ratio in [0, 1], four decimals."""
    if couverture.volume_estime_heures <= 0:
        return Decimal(0)
    return arrondi(couverture.volume_couvert_heures / couverture.volume_estime_heures, 4)


def non_couvert(couverture: Couverture, declare: Sequence[str] = ()) -> tuple[str, ...]:
    """What is not covered: the declared list, or the default one."""
    return tuple(declare) if declare else couverture.non_couvert


def heures_non_couvertes(couverture: Couverture) -> Decimal:
    """The complement, in hours: what the mapping does not see."""
    return arrondi(max(Decimal(0), couverture.volume_estime_heures - couverture.volume_couvert_heures), 1)


def ligne_publication(couverture: Couverture, langue: str = "fr") -> str:
    """The sentence printed in the executive report (17.4)."""
    pourcent = pourcentage(couverture_globale(couverture), 0)
    heures = heures_non_couvertes(couverture)
    if langue == "en":
        return (
            f"{pourcent}% of the estimated work volume of the perimeter is covered by the "
            f"observed channels; {heures} hours are not, mainly: " + ", ".join(non_couvert(couverture)) + "."
        )
    return (
        f"{pourcent} % du volume de travail estime du perimetre est couvert par les canaux "
        f"observes ; {heures} heures ne le sont pas, principalement : "
        + ", ".join(non_couvert(couverture))
        + "."
    )


def par_canal_publication(couverture: Couverture) -> tuple[str, ...]:
    """One line per channel, so a manager sees where the measure is thin."""
    return tuple(
        f"{canal.value} : {pourcentage(part, 1)} %"
        for canal, part in sorted(couverture.par_canal.items(), key=lambda item: item[0].value)
    )
