"""Differential privacy on the published aggregates (idea #7, chapter 18.4).

k >= 5 stops a direct re-identification; it does not stop an inference attack on
a published aggregate. Adding calibrated Laplace noise makes the publication
differentially private: whether one person is in the group or not, the published
number is almost the same.

It is **opt-in** (`actif=False` by default): a mapping sold to a CFO needs exact
figures, and the honest answer is to publish both - the exact aggregate inside
the k >= 5 guarantee, and the noised one when the client asks for a published
dataset. The report says which one it is showing.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from gisement.types.communs import arrondi, decimal

#: Default budget. epsilon = 1 is the usual "strong but usable" setting.
EPSILON_DEFAUT = Decimal("1.0")
DELTA_DEFAUT = Decimal("0.000001")


@dataclass(frozen=True)
class ParametresDP:
    """The privacy budget of a publication."""

    epsilon: Decimal = EPSILON_DEFAUT
    delta: Decimal = DELTA_DEFAUT
    actif: bool = False


def echelle(sensibilite: Decimal, epsilon: Decimal) -> Decimal:
    """Laplace scale b = sensitivity / epsilon."""
    if epsilon <= 0:
        raise ValueError("epsilon doit etre strictement positif")
    return sensibilite / epsilon


def bruit_laplace(parametres: ParametresDP, valeur: Decimal, sensibilite: Decimal, graine: int) -> Decimal:
    """One noised value, deterministic at a fixed seed (ENF-08)."""
    if not parametres.actif:
        return valeur
    b = echelle(sensibilite, parametres.epsilon)
    rng = random.Random(graine)
    # inverse CDF of a centred Laplace, drawn without numpy
    u = rng.random()
    ecart = abs(u - 0.5)
    if ecart >= 0.5:  # the draw landed on the boundary: no noise
        return arrondi(decimal(valeur), 2)
    bruit = -float(b) * math.copysign(1.0, u - 0.5) * math.log(1.0 - 2.0 * ecart)
    return arrondi(decimal(valeur) + decimal(repr(bruit)), 2)


def bruit_agregat(
    parametres: ParametresDP,
    valeurs: Sequence[Decimal],
    sensibilite: Decimal,
    graine: int,
) -> Decimal:
    """Noise the sum, not each term: one draw per published aggregate."""
    total = sum(valeurs, Decimal(0))
    return bruit_laplace(parametres, total, sensibilite, graine)


def sensibilite_comptage() -> Decimal:
    """Sensitivity of a count: one person changes it by one at most."""
    return Decimal(1)


def sensibilite_somme(borne_par_element: Decimal) -> Decimal:
    """Sensitivity of a sum: one person changes it by at most their own value."""
    return decimal(borne_par_element)


def seuil_revelation(nombre_groupes: int) -> Decimal:
    """How much one individual can weigh in a published aggregate (18.4)."""
    if nombre_groupes <= 0:
        return Decimal(0)
    return arrondi(Decimal(1) / Decimal(nombre_groupes), 4)


def resume_garanties(parametres: ParametresDP, nombre_groupes: int) -> str:
    """The sentence a DPO can read: what is guaranteed, in plain French."""
    if not parametres.actif:
        return (
            "Aucune perturbation appliquee : l'agregat reste exact. La garantie repose sur "
            "l'agregation minimale k >= 5, le filtrage des attributs quasi-identifiants et le "
            "bornage des requetes."
        )
    return (
        f"Bruit differentiel actif : epsilon = {parametres.epsilon}, delta = {parametres.delta}, "
        f"sur {nombre_groupes} groupes ; une personne pese au plus "
        f"{seuil_revelation(nombre_groupes)} de l'agregat publie."
    )
