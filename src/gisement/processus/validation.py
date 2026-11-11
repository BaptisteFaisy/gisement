"""Human validation of the aggregation (EF-24, 11.3).

The interview did not disappear, it moved: it no longer discovers, it validates
what was measured and explains what could not be. Every intervention is traced
and moves the figure, which is what makes the measure co-produced rather than
imposed.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from gisement.types.mesure import Processus, StatutValidation


def valider(processus: Processus, par: str, commentaire: str = "") -> Processus:
    """The service manager confirms the measured volume."""
    return replace(
        processus,
        validation=StatutValidation.VALIDEE,
        valide_par=par,
        validation_commentaire=commentaire,
    )


def contester(processus: Processus, par: str, explication: str) -> Processus:
    """The service manager contests a volume, with an explanation (11.3)."""
    return replace(
        processus,
        validation=StatutValidation.CONTESTEE,
        valide_par=par,
        validation_commentaire=explication,
    )


def completer(processus: Processus, par: str, commentaire: str) -> Processus:
    """The service manager completes the description or signals an invisible task."""
    return replace(
        processus,
        validation=StatutValidation.COMPLETEE,
        valide_par=par,
        validation_commentaire=commentaire,
    )


def a_valider(processus: tuple[Processus, ...] | list[Processus]) -> tuple[Processus, ...]:
    return tuple(p for p in processus if p.validation == StatutValidation.EN_ATTENTE)


def sont_valides(processus: tuple[Processus, ...] | list[Processus]) -> bool:
    """A portfolio is publishable only once every process has been looked at."""
    return all(p.validation != StatutValidation.EN_ATTENTE for p in processus)


def horodatage_maintenant() -> datetime:
    return datetime.now(UTC)
