"""Shared vocabulary of Gisement: enumerations, money helpers, hard constants.

Frozen by lot 0 (see `docs/CONTRACTS.md`). Every other lot imports from here
and never redefines a constant. Amounts are always `Decimal` (ENF-13): a
float never crosses a module boundary, and a model never computes a figure.

Identifiers are ASCII on purpose - every lot is written by a different
contributor and an accented constant is a typo waiting to happen. Domain
words stay in French because the deliverables are bilingual (EF-65).
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from enum import StrEnum

# ---------------------------------------------------------------------------
# Hard constants (spec chapters 13, 15, 16, 17, 18). Changing one is a
# decision recorded in docs/DECISIONS.md, never a local tweak.
# ---------------------------------------------------------------------------

SEUIL_AGGREGATION_DEFAUT = 5
"""R2 - minimum number of individuals behind any published measure."""

TAUX_REVUE_DEFAUT = Decimal("0.20")
"""Correction 2 - prudent default review rate when nothing is measured (13.1)."""

DUREE_INFEREE_MARGE = Decimal("0.40")
"""17.2 - +/-40 % band applied to a unit duration that was inferred."""

INCERTITUDE_FRAGMENTATION = Decimal("0.05")
"""17.2 - half width of the uniform band around a fragmentation coefficient."""

INCERTITUDE_TAUX_RELATIVE = Decimal("0.25")
"""17.2 - relative half width of the uniform band around a transfer rate.

Annex A.6 draws a 20 % review rate in [15 %, 25 %], i.e. +/-25 % of the rate.
An absolute band would be dishonest on a small rate: +/-5 points on a 5 %
reject rate means "between zero and double", which widens the published
interval far beyond what the measurement supports.
"""

TIRAGES_MONTE_CARLO = 10_000
"""17.2 - Monte-Carlo draws per gisement. Deterministic at a fixed seed."""

NIVEAU_CONFIANCE = Decimal("0.90")
"""17.2 - published confidence level (90 %)."""

QUANTILES_90 = (Decimal("0.05"), Decimal("0.95"))
"""Quantiles published for a 90 % confidence interval."""

GAIN_ANNUEL_MINIMAL = Decimal("3000")
"""16.1 - below this net annual gain a process is not worth automating."""

DELAI_RETOUR_MAXIMAL_MOIS = Decimal("36")
"""16.1 - beyond 36 months of payback a process is advised against."""

PART_ATYPIQUE_MAXIMALE = Decimal("0.40")
"""16.1 - above 40 % of atypical cases the judgement is not formalisable."""

CHANGEMENTS_INSTABILITE = 3
"""16.1 - three changes in twelve months: automating would freeze a moving target."""

VAGUE1_DELAI_MAX_MOIS = Decimal("6")
"""15.3 - wave 1 must contain at least one project paying back in < 6 months."""

VAGUE1_BUDGET_MAX = Decimal("15000")
"""15.3 - total budget of wave 1 stays below 15 000 EUR."""

VAGUE2_DELAI_MAX_MOIS = Decimal("18")
"""15.3 - wave 2 pays back in less than 18 months."""

SEUIL_CONFIANCE_CLASSIFICATION = Decimal("0.70")
"""21.2 - below this confidence a group goes to human review."""

COHORTE_CLIENTS_MINIMALE = 5
"""25 - a cross-client cohort publishes only from five clients upwards."""

GRILLE_TJM_DEFAUT = Decimal("650")
"""Annex A.4 - default daily rate used by the demo client."""

TAUX_MAINTENANCE_DEFAUT = Decimal("0.08")
"""Annex A.4 - default annual maintenance rate on top of the build cost."""


class Canal(StrEnum):
    """The five observation channels (spec chapter 10)."""

    TICKETS = "tickets"
    COURRIELS = "courriels"
    DOCUMENTS = "documents"
    APPELS = "appels"
    JOURNAUX = "journaux"


CANAUX: tuple[Canal, ...] = (
    Canal.TICKETS,
    Canal.COURRIELS,
    Canal.DOCUMENTS,
    Canal.APPELS,
    Canal.JOURNAUX,
)


class StatutDuree(StrEnum):
    """9.3 - a measured duration and an inferred one are never mixed."""

    MESUREE = "mesuree"
    INFERREE = "inferree"


class Repartition(StrEnum):
    """13.1 correction 1 - how the occurrences spread over the day."""

    REGROUPEE = "regroupee"
    SEMI_REGROUPEE = "semi_regroupee"
    DIFFUSE = "diffuse"
    INTERRUPTIVE = "interruptive"


COEFFICIENTS_FRAGMENTATION: dict[Repartition, Decimal] = {
    Repartition.REGROUPEE: Decimal("0.90"),
    Repartition.SEMI_REGROUPEE: Decimal("0.70"),
    Repartition.DIFFUSE: Decimal("0.45"),
    Repartition.INTERRUPTIVE: Decimal("0.85"),
}


class TypeAutomatisation(StrEnum):
    """14.1 - the five automation types, E being 'do not automate'."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class MotifDeconseil(StrEnum):
    """16.1 - the six reasons to advise against automating a process."""

    VOLUME_INSUFFISANT = "volume_insuffisant"
    RETOUR_TROP_LONG = "retour_trop_long"
    JUGEMENT_NON_FORMALISABLE = "jugement_non_formalisable"
    OBLIGATION_LEGALE = "obligation_legale"
    INSTABILITE = "instabilite"
    DEPENDANCE_EXTERNE = "dependance_externe"


class Risque(StrEnum):
    """15.2 - risk level of a project, declared criteria only."""

    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"


class Vague(StrEnum):
    """15.3 - the three waves of the sequence."""

    AMORCAGE = "vague_1"
    STRUCTUREL = "vague_2"
    TRANSFORMATION = "vague_3"
    AUCUNE = "aucune"


class StatutCampagne(StrEnum):
    """Lifecycle of a measurement campaign (EF-01 to EF-05)."""

    BROUILLON = "brouillon"
    CONFORMITE_ATTENDUE = "conformite_attendue"
    PRETE = "prete"
    EN_COURS = "en_cours"
    SUSPENDUE = "suspendue"
    TERMINEE = "terminee"
    ECHEC = "echec"


class StatutValidation(StrEnum):
    """11.3 - a service manager confirms, contests or completes a measure."""

    EN_ATTENTE = "en_attente"
    VALIDEE = "validee"
    CONTESTEE = "contestee"
    COMPLETEE = "completee"


class StatutSuivi(StrEnum):
    """17.3 - predicted against realised, three statuses."""

    CONFORME = "conforme"
    ECART_MODERE = "ecart_modere"
    PREDICTION_INVALIDE = "prediction_invalide"


ECART_CONFORME = Decimal("0.15")
ECART_INVALIDE = Decimal("0.40")


class FormeIncertitude(StrEnum):
    """17.2 - shape of the distribution of a parameter."""

    NORMALE = "normale"
    UNIFORME = "uniforme"
    FIXE = "fixe"


class Langue(StrEnum):
    """EF-65 - every deliverable exists in French and in English."""

    FR = "fr"
    EN = "en"


class Role(StrEnum):
    """Chapter 7 - the roles of the portal, DPO being a first class one."""

    COMMANDITAIRE = "commanditaire"
    RESPONSABLE_SERVICE = "responsable_service"
    DPO = "dpo"
    CONSULTANT_MSP = "consultant_msp"
    RESPONSABLE_COMPTE = "responsable_compte"
    AGENT_COLLECTEUR = "agent_collecteur"
    AGENT_CLASSIFIEUR = "agent_classifieur"
    AGENT_REDACTEUR = "agent_redacteur"


# ---------------------------------------------------------------------------
# Money helpers. Every amount produced by the economic engine passes here.
# ---------------------------------------------------------------------------


def decimal(valeur: float | int | str | Decimal) -> Decimal:
    """Coerce to `Decimal` without ever going through a binary float."""
    if isinstance(valeur, Decimal):
        return valeur
    return Decimal(str(valeur))


def arrondi(valeur: Decimal, nombre: int = 2) -> Decimal:
    """Round half up to `nombre` decimals - the only rounding of the project."""
    quantum = Decimal(1).scaleb(-nombre)
    return valeur.quantize(quantum, rounding=ROUND_HALF_UP)


def euros(valeur: Decimal) -> Decimal:
    """Amount in euros, two decimals."""
    return arrondi(valeur, 2)


def heures(valeur: Decimal) -> Decimal:
    """Hours, one decimal (published as '18,4 h/mois')."""
    return arrondi(valeur, 1)


def mois(valeur: Decimal) -> Decimal:
    """Payback delay in months, one decimal, banker's rounding (decision D-17).

    Annex A.2 publishes 10 584 / 2 016 = 5.2 months: the exact quotient is
    5.25, so the spec rounds half to even. Half-up would print 5.3 and break
    the reference table that the executive report prints for every process.
    """
    return valeur.quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)


def facteur(valeur: Decimal) -> Decimal:
    """A factor such as the naive/real gap, two decimals (KPI-4: 2,61)."""
    return arrondi(valeur, 2)


def pourcentage(valeur: Decimal, nombre: int = 1) -> Decimal:
    """Ratio 0..1 published as a percentage."""
    return arrondi(valeur * 100, nombre)
