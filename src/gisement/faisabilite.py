"""Feasibility: the decision tree of the five automation types (chapter 14).

The model supplies **facts** ("is there an API?", "does the work require
judgement?"); the code chooses the type (EF-40, 14.3). A model never decides a
type, exactly as it never computes an amount.

The deliberate bias of 14.2 lives here: type A - remove the step instead of
automating it - is tested first, because it costs ten times less and produces a
permanent gain.
"""

from __future__ import annotations

from decimal import Decimal

from gisement.types.communs import CHANGEMENTS_INSTABILITE, Risque, TypeAutomatisation
from gisement.types.economie import Faisabilite, FaitsFaisabilite, Gisement
from gisement.types.mesure import Processus

#: Share of atypical cases above which the risk is no longer "low".
SEUIL_ATYPIQUE_RISQUE_MOYEN = Decimal("0.25")

#: Number of changes in twelve months above which the process is still moving.
SEUIL_CHANGEMENTS_RISQUE_MOYEN = 2


def type_automatisation(faits: FaitsFaisabilite) -> tuple[TypeAutomatisation, tuple[str, ...]]:
    """Apply the decision tree of 14.3 and return the type with its trace."""
    if faits.etape_supprimable_amont:
        return TypeAutomatisation.A, ("l'etape peut etre supprimee en amont",)
    if faits.api_ou_flux_natif:
        return TypeAutomatisation.B, ("une API ou un flux natif existe et couvre le besoin",)
    if faits.travail_deterministe and faits.interface_stable:
        return TypeAutomatisation.C, ("aucune API, travail deterministe et repetitif, interface stable",)
    if faits.jugement_requis:
        return TypeAutomatisation.D, ("le travail exige comprehension, langage ou jugement",)
    return TypeAutomatisation.E, (
        "aucun critere de faisabilite n'est rempli",
        "ni suppression d'etape, ni API, ni interface stable, ni jugement formalisable",
    )


def evaluer_faisabilite(processus: Processus, faits: FaitsFaisabilite) -> Faisabilite:
    """EF-41 - the type, its decision trace and the criteria behind it."""
    retenu, trace = type_automatisation(faits)
    motifs = list(trace)
    if faits.donnee_sensible:
        motifs.append("donnee sensible presente : traitement humain a privilegier")
    if faits.obligation_legale_humaine:
        motifs.append("obligation legale de traitement humain")
    if faits.dependance_externe_non_contractuelle:
        motifs.append("dependance a une interface tierce non contractuelle")
    if processus.changements_douze_mois >= CHANGEMENTS_INSTABILITE:
        motifs.append(f"processus encore mouvant : {processus.changements_douze_mois} changements en 12 mois")
    return Faisabilite(
        processus_id=processus.id,
        type=retenu,
        motifs_decision=tuple(motifs),
        api_existe=faits.api_ou_flux_natif,
        interface_stable=faits.interface_stable,
        jugement_requis=faits.jugement_requis,
        donnee_sensible=faits.donnee_sensible,
        obligation_legale=faits.obligation_legale_humaine,
    )


def evaluer_risque(
    faits: FaitsFaisabilite,
    part_atypique: Decimal = Decimal(0),
    changements: int = 0,
    gisement: Gisement | None = None,
) -> Risque:
    """Risk on declared criteria only (15.2) - never on a feeling."""
    if faits.jugement_requis or faits.obligation_legale_humaine or faits.donnee_sensible:
        return Risque.ELEVE
    if faits.dependance_externe_non_contractuelle or not faits.interface_stable:
        return Risque.MOYEN
    if part_atypique > SEUIL_ATYPIQUE_RISQUE_MOYEN:
        return Risque.MOYEN
    if changements >= SEUIL_CHANGEMENTS_RISQUE_MOYEN:
        return Risque.MOYEN
    if gisement is not None and gisement.temps_net_heures <= 0:
        return Risque.MOYEN
    return Risque.FAIBLE


def est_automatisable(faisabilite: Faisabilite) -> bool:
    """True for the four actionable types, False for category E."""
    return faisabilite.type != TypeAutomatisation.E
