"""Measurement side of the data model: activity, fingerprint group, motif,
process (spec chapter 9.2 and 22).

Three levels of description (9.2):
    activity  -> an observable elementary gesture, raw unit
    motif     -> a recognised family of repetitive activities, unit of calculus
    process   -> motifs contributing to a business outcome, unit of decision

Frozen by lot 0. No field here may hold a person identifier: the only
individual-related column is `groupe_pseudonyme` (22.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from gisement.types.communs import Canal, Repartition, StatutDuree, StatutValidation


@dataclass(frozen=True)
class Activite:
    """One observable elementary gesture, already sanitised.

    `groupe_pseudonyme` is a group label (a service, a shift), never a person
    and never a reversible pseudonym of a person.
    """

    id: str
    corpus_id: str
    canal: Canal
    signature: str
    horodatage: datetime
    texte: str = ""
    duree_mesuree_minutes: Decimal | None = None
    duree_statut: StatutDuree = StatutDuree.INFERREE
    groupe_pseudonyme: str = ""
    service: str = ""
    systemes: tuple[str, ...] = ()
    atypique: bool = False


@dataclass(frozen=True)
class GroupeEmpreinte:
    """21.2 - activities sharing the same deterministic fingerprint.

    The model is called once per group, not once per activity: this is what
    holds the budget (annex G.1, a factor of about 80).
    """

    empreinte: str
    canal: Canal
    signature: str = ""
    """The readable signature (`verbe::objets::systemes`), kept for labelling."""

    activites: tuple[str, ...] = ()
    occurrences: int = 0
    occurrences_mensuelles: tuple[int, ...] = ()
    """Counts per month of the window: what the median is computed on."""

    exemple_texte: str = ""
    systemes: tuple[str, ...] = ()
    services: tuple[str, ...] = ()
    canaux: tuple[Canal, ...] = ()
    taille_groupe_individus: int = 0
    """Number of distinct groups behind the measure - drives the k >= 5 rule."""

    repartition_horaire: Repartition = Repartition.DIFFUSE
    duree_mesuree_minutes: Decimal | None = None
    duree_ecart_minutes: Decimal = Decimal(0)
    duree_nb_cas: int = 0
    duree_statut: StatutDuree = StatutDuree.INFERREE
    part_atypique: Decimal = Decimal(0)
    nb_atypiques: int = 0


@dataclass(frozen=True)
class OccurrencesMensuelles:
    """13.1 correction 4 - the monthly series, median and seasonal amplitude."""

    serie: tuple[Decimal, ...] = ()
    """The monthly counts of the window."""

    mediane: Decimal = Decimal(0)
    """13.1 correction 4 - the median, never the mean: a peak month is not a
    monthly volume."""

    minimum: Decimal = Decimal(0)
    maximum: Decimal = Decimal(0)
    """Published seasonal amplitude (annex D). They may be derived from the
    weekly extremes x 4.33 when the monthly counts are smoother than the weeks
    (decision D-14): annex A.1 publishes both a 210-465 amplitude and a 42
    standard deviation, which only coexist at that reading."""

    ecart_type: Decimal = Decimal(0)
    nb_mois: int = 0

    @property
    def amplitude(self) -> Decimal:
        if self.mediane <= 0:
            return Decimal(0)
        return (self.maximum - self.minimum) / self.mediane


@dataclass(frozen=True)
class Motif:
    """A motif of the catalogue recognised on the campaign (table `motifs`)."""

    id: str
    campagne_id: str
    nom: str
    catalogue_ref: str
    confiance: Decimal
    occurrences: OccurrencesMensuelles = field(default_factory=OccurrencesMensuelles)
    duree_unitaire_minutes: Decimal = Decimal(0)
    duree_statut: StatutDuree = StatutDuree.INFERREE
    duree_ecart_minutes: Decimal = Decimal(0)
    duree_nb_cas: int = 0
    repartition: Repartition = Repartition.DIFFUSE
    part_atypique: Decimal = Decimal(0)
    part_atypique_nb_cas: int = 0
    canaux: tuple[Canal, ...] = ()
    services: tuple[str, ...] = ()
    """The services the motif was measured in. The aggregation into processes is
    keyed on motif + service (lot 11), because the same gesture done by two
    departments is two different measurements."""

    empreintes: tuple[str, ...] = ()
    nouveau: bool = False
    """EF-21 - True when the motif was created because none matched."""

    proposition_catalogue: str = ""
    en_revue_humaine: bool = False


@dataclass(frozen=True)
class EcartProcedure:
    """EF-25 / 9.1 - gap between the written procedure and the observed work.

    The gap is itself a finding, often the most useful one.
    """

    procedure_ref: str
    declare: str
    observe: str
    majeur: bool
    part_pratique_divergente: Decimal = Decimal(0)
    preuve_canaux: tuple[Canal, ...] = ()


@dataclass(frozen=True)
class Processus:
    """A set of motifs contributing to one business outcome (table `processus`)."""

    id: str
    campagne_id: str
    nom: str
    service: str
    motif_ids: tuple[str, ...] = ()
    validation: StatutValidation = StatutValidation.EN_ATTENTE
    validation_commentaire: str = ""
    valide_par: str = ""
    ecart_procedure: EcartProcedure | None = None
    canaux: tuple[Canal, ...] = ()
    famille_poste: str = "administratif"
    """Key into `Tenant.taux_horaires.par_famille` (13.4)."""

    changements_douze_mois: int = 0
    visibilite_dirigeant: bool = False
    saisonnier: bool = False


@dataclass(frozen=True)
class RevueHumaine:
    """21.2 - ambiguous groups and atypical processes go to human review."""

    id: str
    campagne_id: str
    objet: str
    raison: str
    confiance: Decimal = Decimal(0)
    traite: bool = False
    decision: str = ""
    traite_par: str = ""
    traite_le: datetime | None = None
