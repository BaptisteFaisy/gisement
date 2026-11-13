"""Campaign side of the data model (spec chapter 22).

Frozen by lot 0. A campaign is the unit of work: one client scope, one data
window, one seed, one measured cost. Nothing here carries a person identity -
the column is always a group pseudonym (22.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from gisement.types.communs import (
    SEUIL_AGGREGATION_DEFAUT,
    Canal,
    Langue,
    Role,
    StatutCampagne,
)


@dataclass(frozen=True)
class TauxHoraires:
    """13.4 - hourly loaded rates, supplied by the client, never guessed.

    Keyed by job family ("famille de poste"). When `fournis` is False the
    reports publish hours and no euros, and say so.
    """

    fournis: bool
    par_famille: dict[str, Decimal] = field(default_factory=dict)
    devise: str = "EUR"

    def taux(self, famille: str) -> Decimal | None:
        if not self.fournis:
            return None
        return self.par_famille.get(famille)


@dataclass(frozen=True)
class Tenant:
    """One client of the MSP. Isolation is strict (EF-70) and the identity is
    derived from the token, never from free text (EF-71)."""

    id: str
    nom_client: str
    effectif: int
    taux_horaires: TauxHoraires
    retention_jours: int = 180
    langue_defaut: Langue = Langue.FR


@dataclass(frozen=True)
class Perimetre:
    """EF-01 - declared scope: services, sites, window, authorised channels."""

    services: tuple[str, ...]
    sites: tuple[str, ...]
    fenetre_debut: date
    fenetre_fin: date
    canaux_autorises: tuple[Canal, ...]
    volume_travail_estime_heures: Decimal | None = None
    """Declared by the service managers; denominator of the coverage (10.3)."""

    def nb_mois(self) -> int:
        """Length of the window in whole months, at least one."""
        delta = (self.fenetre_fin.year - self.fenetre_debut.year) * 12
        delta += self.fenetre_fin.month - self.fenetre_debut.month
        return max(1, delta)


@dataclass(frozen=True)
class Conformite:
    """EF-02 / EF-03 - the compliance record. No ingestion without it."""

    campagne_id: str
    finalite: str
    canaux_autorises: tuple[Canal, ...]
    seuil_agregation: int = SEUIL_AGGREGATION_DEFAUT
    validation_dpo: bool = False
    validation_cse: bool = False
    valide_le: datetime | None = None
    valide_par: str | None = None
    suspension: bool = False
    suspendu_le: datetime | None = None
    suspendu_par: str | None = None
    retention_jours: int = 180
    categories_filtrees: tuple[str, ...] = (
        "sante",
        "opinion_syndicale",
        "opinion_politique",
        "religion",
        "vie_sexuelle",
        "origine_pretendue_ethnie",
        "donnee_genetique",
    )

    def est_valide(self) -> bool:
        """EF-04 - both the DPO and the staff representatives, not suspended."""
        return self.validation_dpo and self.validation_cse and not self.suspension


@dataclass(frozen=True)
class CoutCampagne:
    """ENF-10 / KPI-8 - cost measured during the run, never estimated after."""

    transcribe_minutes: Decimal = Decimal(0)
    transcribe_usd: Decimal = Decimal(0)
    data_automation_pages: int = 0
    data_automation_usd: Decimal = Decimal(0)
    jetons_entree: int = 0
    jetons_sortie: int = 0
    inference_usd: Decimal = Decimal(0)
    appels_modele: int = 0
    total_usd: Decimal = Decimal(0)
    budget_plafond_usd: Decimal = Decimal(20)

    def budget_restant(self) -> Decimal:
        return self.budget_plafond_usd - self.total_usd


@dataclass(frozen=True)
class Couverture:
    """EF-16 / KPI-3 - coverage published per channel and globally (10.3)."""

    par_canal: dict[Canal, Decimal] = field(default_factory=dict)
    volume_couvert_heures: Decimal = Decimal(0)
    volume_estime_heures: Decimal = Decimal(0)
    non_couvert: tuple[str, ...] = ()

    @property
    def globale(self) -> Decimal:
        if self.volume_estime_heures <= 0:
            return Decimal(0)
        return self.volume_couvert_heures / self.volume_estime_heures


@dataclass(frozen=True)
class Corpus:
    """One sanitised corpus produced by one collector for one channel."""

    id: str
    campagne_id: str
    canal: Canal
    volume: int
    chemin: str
    pseudonymise_le: datetime | None = None
    sensibles_filtres: bool = False
    exclusions_sensibles: int = 0
    graine: int = 0

    def est_assaini(self) -> bool:
        """Policy gate: a corpus is readable only once sanitised (annex C)."""
        return self.pseudonymise_le is not None and self.sensibles_filtres


@dataclass(frozen=True)
class Campagne:
    """The campaign itself (chapter 22, table `campagnes`)."""

    id: str
    tenant_id: str
    perimetre: Perimetre
    graine: int
    statut: StatutCampagne = StatutCampagne.BROUILLON
    conformite: Conformite | None = None
    couverture: Couverture = field(default_factory=Couverture)
    cout: CoutCampagne = field(default_factory=CoutCampagne)
    corpus: tuple[Corpus, ...] = ()
    cree_le: datetime | None = None
    langues: tuple[Langue, ...] = (Langue.FR, Langue.EN)
    client_nom: str = ""
    """The name of the client the campaign measures, from the corpus manifest."""

    def peut_ingerer(self) -> bool:
        """EF-04 - refusal is explicit, not silent."""
        return self.conformite is not None and self.conformite.est_valide()

    def est_suspendue(self) -> bool:
        return self.statut == StatutCampagne.SUSPENDUE or (
            self.conformite is not None and self.conformite.suspension
        )


@dataclass(frozen=True)
class EntreeRegistre:
    """Chapter 22 - append-only, hash-chained compliance register."""

    id: str
    campagne_id: str
    tenant_id: str
    qui: str
    role: Role
    quoi: str
    quand: datetime
    donnees: dict[str, str] = field(default_factory=dict)
    empreinte_precedente: str = ""
    empreinte: str = ""
