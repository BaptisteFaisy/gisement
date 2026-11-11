"""Stratified, reproducible sampling of the mailbox (EF-13, 6.3).

The whole mailbox is never read: a stratified sample of 1 500 to 3 000 messages
is enough to estimate the volumes with a published interval, and reading more
would be disproportionate under labour law. The draw is seeded, the strata are
published, and the same seed gives the same sample (ENF-08).
"""

from __future__ import annotations

import random
from collections.abc import Sequence


def repartir(strates: dict[str, int], cible: int) -> dict[str, int]:
    """Proportional allocation by largest remainder: the total is exactly `cible`."""
    total = sum(strates.values())
    if total <= 0 or cible <= 0:
        return dict.fromkeys(strates, 0)
    if cible >= total:
        return dict(strates)
    bruts = {cle: nombre * cible / total for cle, nombre in strates.items()}
    entiers = {cle: int(valeur) for cle, valeur in bruts.items()}
    reste = cible - sum(entiers.values())
    ordre = sorted(bruts, key=lambda c: (-(bruts[c] - entiers[c]), c))
    for cle in ordre[:reste]:
        entiers[cle] += 1
    return entiers


def echantillonner_stratifie(
    enregistrements: Sequence[dict], cible: int, graine: int, cle_strate: str = "stratum"
) -> tuple[tuple[dict, ...], dict[str, int]]:
    """Sample `cible` records, proportionally per stratum, reproducibly."""
    if cible <= 0 or cible >= len(enregistrements):
        return tuple(enregistrements), _compter(enregistrements, cle_strate)
    par_strate: dict[str, list[dict]] = {}
    for record in enregistrements:
        par_strate.setdefault(str(record.get(cle_strate, "")), []).append(record)
    quotas = repartir({cle: len(v) for cle, v in par_strate.items()}, cible)
    rng = random.Random(graine)
    retenus: list[dict] = []
    for strate in sorted(par_strate):
        pool = sorted(par_strate[strate], key=lambda r: str(r.get("id", "")))
        quota = quotas.get(strate, 0)
        if quota >= len(pool):
            retenus.extend(pool)
        else:
            retenus.extend(rng.sample(pool, quota))
    retenus.sort(key=lambda r: str(r.get("id", "")))
    return tuple(retenus), quotas


def _compter(enregistrements: Sequence[dict], cle_strate: str) -> dict[str, int]:
    comptes: dict[str, int] = {}
    for record in enregistrements:
        cle = str(record.get(cle_strate, ""))
        comptes[cle] = comptes.get(cle, 0) + 1
    return comptes
