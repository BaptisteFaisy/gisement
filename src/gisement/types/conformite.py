"""Privacy side of the data model: chapter 18 and annex C.

The five hard rules R1 to R5 are evaluated on *structured facts* - never on
free text - by `gisement.politique`. What is declared here is the shape of a
request and of the decision a gateway returns.

R5 is the decisive one: the rules are enforced by the gateway before the tool
runs, never by an instruction in a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from gisement.types.communs import SEUIL_AGGREGATION_DEFAUT, Canal, Role


class Regle(StrEnum):
    """The rules a request can violate. Each refusal names the rule."""

    K5 = "regle_k5"
    INDIVIDU = "regle_individu"
    FILTRE_PERSONNE = "regle_filtre_personne"
    COMBINAISON = "regle_combinaison"
    ATTRIBUT_RARE = "regle_attribut_rare"
    CITATION = "regle_citation"
    CONFORMITE = "regle_conformite"
    SUSPENSION = "regle_suspension"
    BUDGET = "regle_budget"
    CORPUS_BRUT = "regle_corpus_brut"
    EXPORT = "regle_export"
    TENANT = "regle_tenant"
    CANAL_NON_AUTORISE = "regle_canal_non_autorise"
    QUOTA_REQUETES = "regle_quota_requetes"


#: R1 - groupings that would attribute work to an individual.
GROUPEMENTS_INTERDITS: tuple[str, ...] = (
    "individu",
    "personne",
    "salarie",
    "employe",
    "pseudonyme",
    "pseudo",
    "matricule",
    "nom",
    "prenom",
    "email",
    "poste",
)

#: R1 - filter keys that identify a person, rejected before evaluation.
FILTRES_PERSONNE: tuple[str, ...] = (
    "individu",
    "personne",
    "salarie",
    "employe",
    "pseudonyme",
    "pseudo",
    "matricule",
    "nom",
    "prenom",
    "email",
    "telephone",
)

#: 18.4 - quasi-identifiers too rare to be offered as a filter at all.
ATTRIBUTS_QUASI_IDENTIFIANTS_RARES: tuple[str, ...] = (
    "langue_parlee",
    "temps_partiel",
    "jour_travaille",
    "anciennete",
    "date_naissance",
    "commune_domicile",
    "vehicule",
    "badge",
    "poste_telephonique",
    "adresse_ip",
)

#: R1 - what a published output may never contain.
SORTIES_INTERDITES: tuple[str, ...] = (
    "citation_non_agregee",
    "classement_individuel",
    "score_individuel",
    "temps_travail_individuel",
)

#: Tools exposed through the gateway (annex C).
OUTIL_MESURE = "Mesure__agregat"
OUTIL_CORPUS = "Corpus__lire"
OUTIL_EXPORT = "Export__produire"
OUTILS_PASSERELLE: tuple[str, ...] = (OUTIL_MESURE, OUTIL_CORPUS, OUTIL_EXPORT)


@dataclass(frozen=True)
class RequeteMesure:
    """A request that reaches the gateway. Structured facts only."""

    outil: str
    tenant_id: str
    utilisateur: str
    role: Role
    campagne_id: str
    canal: Canal | None = None
    filtres: dict[str, str] = field(default_factory=dict)
    groupements: tuple[str, ...] = ()
    sortie: tuple[str, ...] = ()
    citations: bool = False
    corpus_id: str | None = None
    taille_groupe: int | None = None
    """Number of individuals the requested group would cover."""

    taille_resultat_apres_filtres: int | None = None
    """18.4 - evaluated *after* the filters are applied."""

    requetes_precedentes: int = 0
    """Number of requests already made by this user on this campaign."""


@dataclass(frozen=True)
class Decision:
    """What the gateway answers: allow, or refuse naming the rule."""

    autorisee: bool
    regles_violees: tuple[Regle, ...] = ()
    motif: str = ""
    empreinte_requete: str = ""
    seuil_agregation: int = SEUIL_AGGREGATION_DEFAUT

    @property
    def refusee(self) -> bool:
        return not self.autorisee


@dataclass(frozen=True)
class AccesJournalise:
    """EF-53 / ENF-07 - every access to pseudonymised data is logged."""

    id: str
    horodatage: datetime
    tenant_id: str
    campagne_id: str
    utilisateur: str
    role: Role
    outil: str
    autorise: bool
    regles_violees: tuple[Regle, ...] = ()
    empreinte_requete: str = ""
    motif: str = ""


@dataclass(frozen=True)
class ExclusionOpposition:
    """24.3 point 5 - a worker objects; their data is excluded and it is logged."""

    campagne_id: str
    groupe_pseudonyme: str
    demandeur: str
    motif: str
    date: datetime
    seuil_apres_exclusion: int = SEUIL_AGGREGATION_DEFAUT
