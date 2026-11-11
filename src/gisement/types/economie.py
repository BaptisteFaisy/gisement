"""Economic side of the data model (spec chapter 13, annex A).

Frozen by lot 0. Two hard rules live here:

* EF-35 / ENF-13 - every amount is `Decimal`, computed by code, never by a
  model. A model classifies facts; `gisement.calcul` does the arithmetic.
* EF-31 - a gain is never published as a single number: `Intervalle` is part
  of the contract, not an option.

The reference case of annex A (R2) is the acceptance test of this contract:
48.0 gross hours, 18.4 net hours, 772.80 EUR per month, 13.7 months payback,
a naive/real factor of 2.61.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from gisement.types.communs import (
    GRILLE_TJM_DEFAUT,
    NIVEAU_CONFIANCE,
    TAUX_MAINTENANCE_DEFAUT,
    TIRAGES_MONTE_CARLO,
    FormeIncertitude,
    MotifDeconseil,
    Repartition,
    Risque,
    StatutDuree,
    TypeAutomatisation,
    Vague,
)
from gisement.types.mesure import OccurrencesMensuelles


@dataclass(frozen=True)
class Incertitude:
    """17.2 - distribution of one parameter for the Monte-Carlo simulation."""

    forme: FormeIncertitude
    centre: Decimal
    ecart: Decimal = Decimal(0)
    """Standard deviation (NORMALE) or half width (UNIFORME). Ignored if FIXE."""

    nom: str = ""


@dataclass(frozen=True)
class ComposanteTransfert:
    """13.1 correction 2 - one component of the transferred work.

    Either a rate applied to the occurrences (`taux` + `duree_minutes`), or a
    flat allowance (`forfait_heures`). Annex A.3 uses three components:
    review of the automated output, handling of the rejects, supervision.
    """

    nom: str
    taux: Decimal | None = None
    duree_minutes: Decimal | None = None
    forfait_heures: Decimal | None = None

    def heures(self, occurrences: Decimal) -> Decimal:
        if self.forfait_heures is not None:
            return self.forfait_heures
        if self.taux is None or self.duree_minutes is None:
            return Decimal(0)
        return occurrences * self.taux * self.duree_minutes / 60


@dataclass(frozen=True)
class CoutAutomatisation:
    """EF-32 - what automating costs: build, tool subscription, maintenance."""

    jours: Decimal = Decimal(0)
    tjm: Decimal = GRILLE_TJM_DEFAUT
    abonnement_mensuel: Decimal = Decimal(0)
    taux_maintenance: Decimal = TAUX_MAINTENANCE_DEFAUT

    def developpement(self) -> Decimal:
        return self.jours * self.tjm


@dataclass(frozen=True)
class FaitsFaisabilite:
    """Facts classified by the model; the decision tree in code chooses (14.3)."""

    etape_supprimable_amont: bool = False
    api_ou_flux_natif: bool = False
    travail_deterministe: bool = False
    interface_stable: bool = False
    jugement_requis: bool = False
    donnee_sensible: bool = False
    obligation_legale_humaine: bool = False
    dependance_externe_non_contractuelle: bool = False


@dataclass(frozen=True)
class EntreeGisement:
    """Everything `gisement.calcul` needs. Measured facts, client supplied rate.

    `taux_horaire` is None when the client refused to give it (13.4): the
    engine then publishes hours and no euros, and says so.
    """

    processus_id: str
    occurrences: OccurrencesMensuelles = field(default_factory=OccurrencesMensuelles)
    duree_unitaire_minutes: Decimal = Decimal(0)
    duree_statut: StatutDuree = StatutDuree.INFERREE
    duree_ecart_minutes: Decimal = Decimal(0)
    duree_nb_cas: int = 0
    repartition: Repartition = Repartition.DIFFUSE
    part_atypique: Decimal = Decimal(0)
    part_atypique_nb_cas: int = 0
    transfert: tuple[ComposanteTransfert, ...] = ()
    taux_horaire: Decimal | None = None
    cout: CoutAutomatisation = field(default_factory=CoutAutomatisation)
    faits: FaitsFaisabilite = field(default_factory=FaitsFaisabilite)
    graine: int = 0
    tirages: int = TIRAGES_MONTE_CARLO


@dataclass(frozen=True)
class Intervalle:
    """A published interval (EF-31). `niveau` is the confidence level, 90 %."""

    bas: Decimal
    haut: Decimal
    niveau: Decimal = NIVEAU_CONFIANCE

    def contient(self, valeur: Decimal) -> bool:
        return self.bas <= valeur <= self.haut

    @property
    def largeur(self) -> Decimal:
        return self.haut - self.bas


@dataclass(frozen=True)
class DecompositionCout:
    """Annex A.4 - the cost side, itemised so a CFO can check it."""

    developpement: Decimal = Decimal(0)
    outil_annuel: Decimal = Decimal(0)
    maintenance_annuelle: Decimal = Decimal(0)
    annee_1: Decimal = Decimal(0)
    recurrent: Decimal = Decimal(0)


@dataclass(frozen=True)
class Gisement:
    """EF-30 to EF-34 - the measured deposit of one process."""

    processus_id: str
    temps_brut_heures: Decimal
    coefficient_fragmentation: Decimal
    temps_fragmente_heures: Decimal
    temps_transfere_heures: Decimal
    detail_transfert: tuple[tuple[str, Decimal], ...]
    temps_ineliminable_heures: Decimal
    temps_net_heures: Decimal
    temps_net_intervalle: Intervalle
    cout: DecompositionCout
    taux_horaire: Decimal | None = None
    gain_mensuel: Decimal | None = None
    gain_mensuel_intervalle: Intervalle | None = None
    gain_annuel: Decimal | None = None
    gain_naif_mensuel: Decimal | None = None
    ecart_naif: Decimal | None = None
    delai_retour_mois: Decimal | None = None
    delai_retour_naif_mois: Decimal | None = None
    gain_trois_ans: Decimal | None = None
    tirages: int = TIRAGES_MONTE_CARLO
    graine: int = 0


@dataclass(frozen=True)
class Faisabilite:
    """EF-40 / EF-41 - the automation type, with the decision trace."""

    processus_id: str
    type: TypeAutomatisation
    motifs_decision: tuple[str, ...] = ()
    api_existe: bool = False
    interface_stable: bool = False
    jugement_requis: bool = False
    donnee_sensible: bool = False
    obligation_legale: bool = False


@dataclass(frozen=True)
class Deconseille:
    """EF-44 / 16.2 - 'do not automate', with its re-examination condition."""

    processus_id: str
    motif: MotifDeconseil
    seuil_atteint: str
    condition_reexamen: str
    valeurs: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class CriterePriorite:
    """15.2 - one normalised criterion of the priority score, 0..1."""

    gain: Decimal = Decimal(0)
    faisabilite: Decimal = Decimal(0)
    rapidite: Decimal = Decimal(0)
    visibilite: Decimal = Decimal(0)
    securite_juridique: Decimal = Decimal(0)


@dataclass(frozen=True)
class Projet:
    """The unit sold by the MSP: one sequenced automation project."""

    id: str
    processus_id: str
    gisement: Gisement
    faisabilite: Faisabilite
    risque: Risque = Risque.MOYEN
    criteres: CriterePriorite = field(default_factory=CriterePriorite)
    score: Decimal = Decimal(0)
    vague: Vague = Vague.AUCUNE
    rang: int = 0
    deconseille: Deconseille | None = None
    justification_vague: str = ""


@dataclass(frozen=True)
class Portefeuille:
    """EF-42 / EF-43 - the sequenced portfolio, not a list sorted by gain."""

    campagne_id: str
    projets: tuple[Projet, ...] = ()
    deconseilles: tuple[Deconseille, ...] = ()
    vague1_existe: bool = False
    recommandation_elargissement: str = ""
    gain_net_annuel: Intervalle | None = None
    part_deconseilles: Decimal = Decimal(0)


@dataclass(frozen=True)
class SuiviTrimestriel:
    """EF-63 / 17.3 - realised against predicted. Append-only (22.1)."""

    id: str
    projet_id: str
    trimestre: str
    gain_predit: Decimal
    gain_mesure: Decimal
    ecart: Decimal
    statut: str
    parametre_fautif: str = ""
    commentaire: str = ""


@dataclass(frozen=True)
class PrecisionCumulee:
    """KPI-6 - the credibility of the tool, published every quarter."""

    nb_trimestres: int = 0
    nb_projets: int = 0
    ecart_moyen: Decimal = Decimal(0)
    part_conformes: Decimal = Decimal(0)
    part_invalides: Decimal = Decimal(0)
