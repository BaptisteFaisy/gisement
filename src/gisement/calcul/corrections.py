"""The four corrections to the naive calculation (chapter 13.1).

The naive calculation is `occurrences x duration x hourly rate`. It is
systematically too optimistic, for four measurable reasons. This module applies
them; it decides nothing and formats nothing.

Decision D-01: the ineliminable share is computed on the **gross** time, as
annex A.3 does, not on the fragmented time as the formula line of 13.2 reads.
Decision D-11: a type A action that removes the step carries neither transfer
nor ineliminable share - there is no automated output left to review.
"""

from __future__ import annotations

from decimal import Decimal

from gisement.types.communs import COEFFICIENTS_FRAGMENTATION, Repartition, arrondi, mois
from gisement.types.economie import ComposanteTransfert, CoutAutomatisation, DecompositionCout, EntreeGisement

ZERO = Decimal(0)
SOIXANTE = Decimal(60)


def coefficient_fragmentation(repartition: Repartition) -> Decimal:
    """13.1 correction 1 - the value of freed time depends on its continuity."""
    return COEFFICIENTS_FRAGMENTATION[repartition]


def occurrences_effectives(entree: EntreeGisement) -> Decimal:
    """The share of the measured volume the project actually addresses."""
    return entree.occurrences.mediane * entree.part_volume_traitee


def temps_brut(entree: EntreeGisement) -> Decimal:
    """Gross monthly hours: effective occurrences x unit duration."""
    return occurrences_effectives(entree) * entree.duree_unitaire_minutes / SOIXANTE


def temps_fragmente(entree: EntreeGisement, brut: Decimal) -> Decimal:
    """13.1 correction 1 applied."""
    return brut * coefficient_fragmentation(entree.repartition)


def detail_transfert(
    composantes: tuple[ComposanteTransfert, ...], occurrences: Decimal
) -> tuple[tuple[str, Decimal], ...]:
    """Hours per transfer component, so a CFO can check the line."""
    return tuple((c.nom, arrondi(c.heures(occurrences), 4)) for c in composantes)


def temps_transfere(
    entree: EntreeGisement, occurrences: Decimal
) -> tuple[Decimal, tuple[tuple[str, Decimal], ...]]:
    """13.1 correction 2 - automating moves work, it does not delete it."""
    if entree.suppression_etape:
        return ZERO, ()
    detail = detail_transfert(entree.transfert, occurrences)
    return sum((v for _, v in detail), ZERO), detail


def temps_ineliminable(entree: EntreeGisement, brut: Decimal) -> Decimal:
    """13.1 correction 3 - the part that needs judgement or a signature (D-01)."""
    if entree.suppression_etape:
        return ZERO
    return brut * entree.part_atypique


def temps_net(fragmente: Decimal, transfere: Decimal, ineliminable: Decimal) -> Decimal:
    """Net recoverable hours, floored at zero: a negative deposit does not exist."""
    return max(ZERO, fragmente - transfere - ineliminable)


def decomposer_cout(cout: CoutAutomatisation) -> DecompositionCout:
    """EF-32 - build, tool subscription, maintenance, first year, recurring."""
    developpement = cout.developpement()
    outil_annuel = cout.abonnement_mensuel * Decimal(12)
    maintenance = developpement * cout.taux_maintenance
    return DecompositionCout(
        developpement=arrondi(developpement, 2),
        outil_annuel=arrondi(outil_annuel, 2),
        maintenance_annuelle=arrondi(maintenance, 2),
        annee_1=arrondi(developpement + outil_annuel + maintenance, 2),
        recurrent=arrondi(outil_annuel + maintenance, 2),
    )


def delai_retour(cout_annee_1: Decimal, gain_mensuel: Decimal | None) -> Decimal | None:
    """Months before the automation cost is recovered (EF-33)."""
    if gain_mensuel is None or gain_mensuel <= 0:
        return None
    return mois(cout_annee_1 / gain_mensuel)


def gain_trois_ans(gain_annuel: Decimal, annee_1: Decimal, recurrent: Decimal) -> Decimal:
    """Three-year gain, net of the first year and two recurring years."""
    return arrondi(gain_annuel * 3 - (annee_1 + recurrent * 2), 2)


def ecart_au_naif(gain_naif: Decimal | None, gain_net: Decimal | None) -> Decimal | None:
    """KPI-4 - the factor between the promised gain and the real one."""
    if gain_naif is None or gain_net is None or gain_net <= 0:
        return None
    return arrondi(gain_naif / gain_net, 2)
