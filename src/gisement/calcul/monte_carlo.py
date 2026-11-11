"""Monte-Carlo simulation of the interval (17.2, EF-31, R4).

No published figure is a single number: the net hours and the monthly gain come
with a 90 % interval. The interval is simulated, not approximated by a formula,
and it is deterministic: the seed is part of the campaign, so two runs give
strictly identical bounds.

Draws are made in binary floating point for speed (10 000 draws per deposit);
every value that leaves this module is a rounded `Decimal` (ENF-13).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from decimal import Decimal

from gisement.calcul.incertitudes import incertitudes
from gisement.types.communs import QUANTILES_90, TIRAGES_MONTE_CARLO, FormeIncertitude, heures
from gisement.types.economie import EntreeGisement, Intervalle


def quantile(valeurs: Sequence[float], q: Decimal) -> float:
    """The q-quantile of an already sorted sample, nearest rank."""
    if not valeurs:
        return 0.0
    index = round(float(q) * (len(valeurs) - 1))
    return valeurs[max(0, min(index, len(valeurs) - 1))]


def intervalle(valeurs: Sequence[float]) -> Intervalle:
    """The published 90 % interval of a sorted sample of draws."""
    bas, haut = QUANTILES_90
    return Intervalle(
        bas=heures(Decimal(repr(quantile(valeurs, bas)))),
        haut=heures(Decimal(repr(quantile(valeurs, haut)))),
    )


def _tirer(forme: str, centre: float, ecart: float, rng: random.Random) -> float:
    if ecart <= 0.0:
        return centre
    if forme == FormeIncertitude.NORMALE.value:
        return rng.gauss(centre, ecart)
    return rng.uniform(centre - ecart, centre + ecart)


def tirer_net(entree: EntreeGisement, rng: random.Random, distributions: dict) -> float:
    """One draw of the net monthly hours."""
    occ = max(0.0, _tirer_forme(distributions["occurrences"], rng))
    duree = max(0.0, _tirer_forme(distributions["duree_unitaire"], rng))
    coef = min(1.0, max(0.0, _tirer_forme(distributions["coefficient_fragmentation"], rng)))
    atypique = min(1.0, max(0.0, _tirer_forme(distributions["part_atypique"], rng)))
    effectives = occ * float(entree.part_volume_traitee)
    brut = effectives * duree / 60.0
    if entree.suppression_etape:
        return max(0.0, brut * coef)
    transfere = 0.0
    for composante in entree.transfert:
        cle = f"taux:{composante.nom}"
        if composante.taux is not None and cle in distributions:
            taux = min(1.0, max(0.0, _tirer_forme(distributions[cle], rng)))
            transfere += effectives * taux * float(composante.duree_minutes or 0) / 60.0
        elif composante.forfait_heures is not None:
            transfere += float(composante.forfait_heures)
    return max(0.0, brut * coef - transfere - brut * atypique)


def _tirer_forme(incertitude, rng: random.Random) -> float:
    return _tirer(incertitude.forme.value, float(incertitude.centre), float(incertitude.ecart), rng)


def simuler(
    entree: EntreeGisement, tirages: int = TIRAGES_MONTE_CARLO
) -> tuple[Intervalle, Intervalle | None]:
    """Simulate the net hours and, when a rate is known, the monthly gain."""
    rng = random.Random(entree.graine)
    distributions = incertitudes(entree)
    nets: list[float] = []
    for _ in range(tirages):
        nets.append(tirer_net(entree, rng, distributions))
    nets.sort()
    heures_intervalle = intervalle(nets)
    if entree.taux_horaire is None:
        return heures_intervalle, None
    taux = float(entree.taux_horaire)
    gains = sorted(v * taux for v in nets)
    return heures_intervalle, Intervalle(
        bas=Decimal(repr(quantile(gains, QUANTILES_90[0]))).quantize(Decimal("1")),
        haut=Decimal(repr(quantile(gains, QUANTILES_90[1]))).quantize(Decimal("1")),
    )
