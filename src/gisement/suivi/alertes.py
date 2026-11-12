"""Drift alerts: a prediction that misses is a signal, not an incident (idea #4).

Three things deserve an alert, and each one has an owner:
* a prediction invalidated (> 40 % off) - the economic model must be reviewed;
* a moderate gap (15-40 %) - the faulty parameter is named for calibration;
* a volume that moved by more than 30 % between two campaigns - a new deposit
  appeared, or a process degraded, and both are worth a project.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from gisement.types.communs import ECART_CONFORME, ECART_INVALIDE, arrondi
from gisement.types.economie import Gisement, SuiviTrimestriel

GRAVITE_INFO = "info"
GRAVITE_SURVEILLER = "a_surveiller"
GRAVITE_CRITIQUE = "critique"

SEUIL_DERIVE_VOLUME = Decimal("0.30")


@dataclass(frozen=True)
class Alerte:
    projet_id: str
    gravite: str
    code: str
    message: str
    valeur: Decimal


def detecter(
    suivis: Sequence[SuiviTrimestriel],
    gisements: Mapping[str, Gisement] | None = None,
    volumes_precedents: Mapping[str, Decimal] | None = None,
    volumes_courants: Mapping[str, Decimal] | None = None,
) -> tuple[Alerte, ...]:
    """Every alert of a quarter, most severe first."""
    alertes = list(_alertes_de_suivi(suivis, gisements or {}))
    alertes.extend(_alertes_de_volume(volumes_precedents or {}, volumes_courants or {}))
    ordre = {GRAVITE_CRITIQUE: 0, GRAVITE_SURVEILLER: 1, GRAVITE_INFO: 2}
    alertes.sort(key=lambda a: (ordre.get(a.gravite, 3), a.projet_id))
    return tuple(alertes)


def _alertes_de_suivi(
    suivis: Sequence[SuiviTrimestriel], gisements: Mapping[str, Gisement]
) -> Sequence[Alerte]:
    alertes: list[Alerte] = []
    for suivi in suivis:
        if suivi.ecart < ECART_CONFORME:
            continue
        if suivi.ecart > ECART_INVALIDE:
            alertes.append(
                Alerte(
                    projet_id=suivi.projet_id,
                    gravite=GRAVITE_CRITIQUE,
                    code="prediction_invalide",
                    message=(
                        f"Prediction invalide sur {suivi.trimestre} : {suivi.gain_mesure} EUR realizes "
                        f"contre {suivi.gain_predit} EUR predits (ecart de "
                        f"{arrondi(suivi.ecart * 100, 0)} %). Le modele de calcul doit etre revu et "
                        f"l'ecart publie au client."
                    ),
                    valeur=suivi.ecart,
                )
            )
            continue
        alertes.append(
            Alerte(
                projet_id=suivi.projet_id,
                gravite=GRAVITE_SURVEILLER,
                code="gain_non_atteint" if suivi.gain_mesure < suivi.gain_predit else "gain_depasse",
                message=(
                    f"Ecart de {arrondi(suivi.ecart * 100, 0)} % sur {suivi.trimestre} "
                    f"({suivi.gain_mesure} EUR realizes / {suivi.gain_predit} EUR predits). "
                    f"Parametre en cause : {suivi.parametre_fautif or 'a identifier'}."
                ),
                valeur=suivi.ecart,
            )
        )
        del gisements  # the gisement is only used by the caller for context
    return alertes


def _alertes_de_volume(
    precedents: Mapping[str, Decimal], courants: Mapping[str, Decimal]
) -> Sequence[Alerte]:
    alertes: list[Alerte] = []
    for projet_id, courant in sorted(courants.items()):
        precedent = precedents.get(projet_id)
        if precedent is None or precedent <= 0:
            if precedent == Decimal(0) and courant > 0:
                alertes.append(
                    Alerte(
                        projet_id=projet_id,
                        gravite=GRAVITE_SURVEILLER,
                        code="gisement_apparu",
                        message=(
                            f"Un gisement est apparu : {courant} occurrences par mois, aucune "
                            f"a la campagne precedente. Un projet se prepare."
                        ),
                        valeur=courant,
                    )
                )
            continue
        variation = (courant - precedent) / precedent
        if abs(variation) >= SEUIL_DERIVE_VOLUME:
            alertes.append(
                Alerte(
                    projet_id=projet_id,
                    gravite=GRAVITE_SURVEILLER,
                    code="derive_volume",
                    message=(
                        f"Volume en {'hausse' if variation > 0 else 'baisse'} de "
                        f"{arrondi(abs(variation) * 100, 0)} % ({precedent} -> {courant} "
                        f"occurrences/mois). Le chiffre d'affaires du projet change."
                    ),
                    valeur=arrondi(variation, 4),
                )
            )
    return alertes


def resume(alertes: Sequence[Alerte]) -> str:
    """One line for the quarterly report."""
    if not alertes:
        return "Aucune alerte : les predictions tiennent et les volumes sont stables."
    critiques = sum(1 for a in alertes if a.gravite == GRAVITE_CRITIQUE)
    return (
        f"{len(alertes)} alerte(s) dont {critiques} critique(s) ; "
        f"la plus severe : {alertes[0].code} sur {alertes[0].projet_id}"
    )
