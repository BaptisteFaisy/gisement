"""The engine learns from what actually happened (idea #4, chapter 17.3).

After four quarters, the base of realised-against-predicted becomes an asset
nobody can copy (8.2). This module turns that base into corrected defaults:
when the realised gain is systematically above the prediction, the default
coefficients were too prudent, and the next mapping says so before the client
has to discover it.

Calibration is **bounded and explainable**: one step of 10 % per quarter, a
floor and a ceiling per coefficient, and the number of projects behind the
change is published with it. An engine that rewrote its own coefficients freely
would be unauditable - and an unauditable figure is a figure nobody signs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from gisement.suivi.base import precision_cumulee
from gisement.types.communs import TAUX_REVUE_DEFAUT, arrondi, decimal
from gisement.types.economie import SuiviTrimestriel

PAS_DE_CALIBRATION = Decimal("0.10")
#: Outside this band around 1.0 nothing moves: a 5 % gap is noise, not a signal.
BANDE_MORTE = Decimal("0.15")

#: Bounds a coefficient may never leave, whatever the history says.
BORNES: dict[str, tuple[Decimal, Decimal]] = {
    "taux_revue": (Decimal("0.05"), Decimal("0.50")),
    "coefficient_fragmentation": (Decimal("0.40"), Decimal("0.95")),
    "part_atypique": (Decimal("0.00"), Decimal("0.60")),
}

DEFAUTS: dict[str, Decimal] = {
    "coefficient_fragmentation": Decimal("0.70"),
    "part_atypique": Decimal("0.15"),
    "taux_revue": TAUX_REVUE_DEFAUT,
}


@dataclass(frozen=True)
class CoefficientCalibre:
    """One corrected default, with the evidence behind the correction."""

    nom: str
    valeur_par_defaut: Decimal
    valeur_calibree: Decimal
    echantillons: int
    confiance: Decimal
    ratio_realise: Decimal
    commentaire: str


def ratio_par_projet(suivis: Sequence[SuiviTrimestriel]) -> dict[str, Decimal]:
    """Realised / predicted per project, averaged over its quarters."""
    par_projet: dict[str, list[Decimal]] = {}
    for suivi in suivis:
        if suivi.gain_predit <= 0:
            continue
        par_projet.setdefault(suivi.projet_id, []).append(suivi.gain_mesure / suivi.gain_predit)
    return {
        projet: arrondi(sum(ratios, Decimal(0)) / decimal(len(ratios)), 4)
        for projet, ratios in par_projet.items()
    }


def calibrer(
    suivis: Sequence[SuiviTrimestriel], defauts: Mapping[str, Decimal] | None = None
) -> tuple[CoefficientCalibre, ...]:
    """Correct the defaults from the observed realised/predicted ratios.

    A realised gain above the prediction means the corrections were too harsh:
    the review rate and the atypical share go down, the fragmentation
    coefficient goes up. Below, the opposite. Inside the dead band, nothing
    moves.
    """
    valeurs = dict(defauts or DEFAUTS)
    ratios = ratio_par_projet(suivis)
    if not ratios:
        return tuple(
            CoefficientCalibre(
                nom=nom,
                valeur_par_defaut=valeur,
                valeur_calibree=valeur,
                echantillons=0,
                confiance=Decimal(0),
                ratio_realise=Decimal(1),
                commentaire="aucun realise disponible : le defaut est conserve",
            )
            for nom, valeur in sorted(valeurs.items())
        )
    moyen = arrondi(sum(ratios.values(), Decimal(0)) / decimal(len(ratios)), 4)
    confiance = precision_cumulee(suivis).part_conformes
    return tuple(
        _calibrer_un(nom, valeur, moyen, len(ratios), confiance) for nom, valeur in sorted(valeurs.items())
    )


def _calibrer_un(
    nom: str, defaut: Decimal, ratio: Decimal, echantillons: int, confiance: Decimal
) -> CoefficientCalibre:
    sens = _sens(nom, ratio)
    nouvelle = _borner(nom, defaut * (Decimal(1) + sens * PAS_DE_CALIBRATION))
    return CoefficientCalibre(
        nom=nom,
        valeur_par_defaut=defaut,
        valeur_calibree=arrondi(nouvelle, 4),
        echantillons=echantillons,
        confiance=arrondi(confiance, 4),
        ratio_realise=ratio,
        commentaire=_commentaire(nom, ratio, defaut, nouvelle, echantillons),
    )


def _sens(nom: str, ratio: Decimal) -> Decimal:
    """+1 raise, -1 lower, 0 keep - and the direction depends on the coefficient."""
    if abs(ratio - Decimal(1)) < BANDE_MORTE:
        return Decimal(0)
    superieur = ratio > Decimal(1)
    if nom == "coefficient_fragmentation":
        return Decimal(1) if superieur else Decimal(-1)
    # review rate and atypical share: more realised gain means they were too high
    return Decimal(-1) if superieur else Decimal(1)


def _borner(nom: str, valeur: Decimal) -> Decimal:
    basse, haute = BORNES.get(nom, (Decimal(0), Decimal(1)))
    return max(basse, min(haute, valeur))


def _commentaire(nom: str, ratio: Decimal, defaut: Decimal, nouvelle: Decimal, echantillons: int) -> str:
    ecart = arrondi((ratio - Decimal(1)) * 100, 1)
    if nouvelle == defaut:
        return (
            f"{nom} : realise a {ecart} % de l'ecart predit, sous la bande de calibration ; "
            f"le defaut {defaut} est conserve ({echantillons} projets suivis)"
        )
    return (
        f"{nom} : realise {ecart} % par rapport au predit sur {echantillons} projets ; "
        f"defaut {defaut} -> {arrondi(nouvelle, 4)} (un pas de 10 % par trimestre, borne)"
    )


def appliquer(coefficients: Sequence[CoefficientCalibre]) -> dict[str, Decimal]:
    """The calibrated defaults, as a dict a campaign can be re-run with."""
    return {c.nom: c.valeur_calibree for c in coefficients}
