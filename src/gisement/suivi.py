"""Quarterly follow-up: realised against predicted (lot 17, EF-63, KPI-6).

This is what makes the service recurring and not repeatable: after four
quarters Gisement knows what was really gained, and that base of realised
against predicted becomes an asset nobody can copy (17.3, 8.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from gisement.types.communs import (
    ECART_CONFORME,
    ECART_INVALIDE,
    StatutSuivi,
    arrondi,
    decimal,
)
from gisement.types.economie import Gisement, PrecisionCumulee, SuiviTrimestriel


def comparer(gain_predit: Decimal, gain_mesure: Decimal, projet_id: str, trimestre: str) -> SuiviTrimestriel:
    """One quarter of realised against predicted, with its status (17.3)."""
    if gain_predit <= 0:
        ecart = Decimal(0)
        statut = StatutSuivi.CONFORME
    else:
        ecart = arrondi(abs(gain_mesure - gain_predit) / gain_predit, 4)
        statut = _statut(ecart)
    return SuiviTrimestriel(
        id=f"SUIVI-{projet_id}-{trimestre}",
        projet_id=projet_id,
        trimestre=trimestre,
        gain_predit=gain_predit,
        gain_mesure=gain_mesure,
        ecart=ecart,
        statut=statut.value,
        parametre_fautif=_parametre_fautif(gain_predit, gain_mesure, ecart),
    )


def _statut(ecart: Decimal) -> StatutSuivi:
    if ecart < ECART_CONFORME:
        return StatutSuivi.CONFORME
    if ecart <= ECART_INVALIDE:
        return StatutSuivi.ECART_MODERE
    return StatutSuivi.PREDICTION_INVALIDE


def _parametre_fautif(gain_predit: Decimal, gain_mesure: Decimal, ecart: Decimal) -> str:
    """Name the parameter to revise when the prediction missed (17.3)."""
    if ecart < ECART_CONFORME:
        return ""
    sous_estime = gain_mesure > gain_predit
    if sous_estime:
        return "coefficient de fragmentation trop prudent (le temps libere est plus reel)"
    return "part ineliminable ou taux de revue sous-estime (le gain reel est plus faible)"


def precision_cumulee(suivis: Sequence[SuiviTrimestriel]) -> PrecisionCumulee:
    """KPI-6 - the credibility of the tool, published every quarter."""
    if not suivis:
        return PrecisionCumulee()
    ecart_total = sum((s.ecart for s in suivis), Decimal(0))
    conformes = sum(1 for s in suivis if s.statut == StatutSuivi.CONFORME.value)
    invalides = sum(1 for s in suivis if s.statut == StatutSuivi.PREDICTION_INVALIDE.value)
    n = decimal(len(suivis))
    return PrecisionCumulee(
        nb_trimestres=len({s.trimestre for s in suivis}),
        nb_projets=len({s.projet_id for s in suivis}),
        ecart_moyen=arrondi(ecart_total / n, 4),
        part_conformes=arrondi(decimal(conformes) / n, 4),
        part_invalides=arrondi(decimal(invalides) / n, 4),
    )


def ecart_trimestriel(gisement: Gisement, gain_mesure: Decimal, trimestre: str) -> SuiviTrimestriel:
    """Convenience: compare a quarter against a predicted gisement."""
    return comparer(gisement.gain_mensuel or Decimal(0), gain_mesure, gisement.processus_id, trimestre)
