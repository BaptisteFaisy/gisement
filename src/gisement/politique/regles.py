"""The rules of the gateway, as data (chapter 18, annex C, decision D-09).

One registry, two consumers: `passerelle.evaluer()` enforces it, and
`agentcore.exporter_politique_agentcore()` publishes it for AgentCore Policy.
The two cannot drift, because there is only one list.

R5 is the point of the whole chapter: the rules are applied **before** the tool
runs, on structured facts. They are not a sentence in a prompt. An agent that
tries to produce an individual measure gets a refusal naming the rule, and the
refusal is logged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from gisement.types.communs import SEUIL_AGGREGATION_DEFAUT, Canal, decimal
from gisement.types.conformite import (
    ATTRIBUTS_QUASI_IDENTIFIANTS_RARES,
    FILTRES_PERSONNE,
    GROUPEMENTS_INTERDITS,
    OUTIL_CORPUS,
    OUTIL_EXPORT,
    OUTIL_MESURE,
    OUTILS_PASSERELLE,
    SORTIES_INTERDITES,
    Regle,
    RequeteMesure,
)

#: Outputs that would rank or score a person (R1).
SORTIES_INDIVIDUELLES = tuple(s for s in SORTIES_INTERDITES if s != "citation_non_agregee")


@dataclass(frozen=True)
class ContextePolitique:
    """Everything the gateway knows before deciding. Structured facts only."""

    campagne_id: str
    tenant_id: str
    conforme: bool
    suspendue: bool
    seuil: int = SEUIL_AGGREGATION_DEFAUT
    canaux_autorises: tuple[str, ...] = tuple(c.value for c in Canal)
    budget_restant: Decimal = Decimal(0)
    requetes_utilisateur: int = 0
    quota_requetes: int = 200
    corpus_assainis: frozenset[str] = frozenset()
    """Fail closed: a corpus that was not declared sanitised is not readable."""


@dataclass(frozen=True)
class RegleSpec:
    """One rule: which tools it guards, its condition, and how to test it."""

    regle: Regle
    condition: str
    message: str
    verificateur: Callable[[RequeteMesure, ContextePolitique], bool]
    outils: tuple[str, ...] = OUTILS_PASSERELLE

    def violee(self, requete: RequeteMesure, contexte: ContextePolitique) -> bool:
        if self.outils and requete.outil not in self.outils:
            return False
        return self.verificateur(requete, contexte)


def _taille_groupe_non_etablie(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    """R2, fail closed: a measure whose group size is unknown is not a measure.

    The comparison uses the EFFECTIVE threshold (`seuil_effectif`), never the
    raw one: a client can raise the threshold, never lower it below five.
    """
    return requete.taille_groupe is None or requete.taille_groupe < seuil_effectif(contexte)


def _groupe_de_travail(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    return requete.outil == OUTIL_MESURE and _taille_groupe_non_etablie(requete, contexte)


def _combinaison(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    """18.4 - filters are evaluated *after* application, on the resulting size."""
    if not requete.filtres:
        return False
    taille = requete.taille_resultat_apres_filtres
    return taille is not None and taille < seuil_effectif(contexte)


def _attribut_rare(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    return any(cle in ATTRIBUTS_QUASI_IDENTIFIANTS_RARES for cle in requete.filtres)


def _sortie_individuelle(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    return any(s in SORTIES_INDIVIDUELLES for s in requete.sortie)


def _quota(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    deja = max(contexte.requetes_utilisateur, requete.requetes_precedentes)
    return deja > contexte.quota_requetes


def _corpus_brut(requete: RequeteMesure, contexte: ContextePolitique) -> bool:
    return requete.corpus_id is None or requete.corpus_id not in contexte.corpus_assainis


REGLES: tuple[RegleSpec, ...] = (
    RegleSpec(
        regle=Regle.TENANT,
        condition="requete.tenant_id == contexte.tenant_id",
        message="Le tenant de la requete ne correspond pas a celui du jeton.",
        verificateur=lambda r, c: r.tenant_id != c.tenant_id,
    ),
    RegleSpec(
        regle=Regle.CONFORMITE,
        condition="contexte.conforme == vrai",
        message="Aucune mesure sans validation enregistree du DPO et des representants du personnel.",
        verificateur=lambda r, c: not c.conforme,
    ),
    RegleSpec(
        regle=Regle.SUSPENSION,
        condition="contexte.suspendue == faux",
        message="La mesure est suspendue : le dispositif est a l'arret.",
        verificateur=lambda r, c: c.suspendue,
    ),
    RegleSpec(
        regle=Regle.BUDGET,
        condition="contexte.budget_restant > 0",
        message="Le budget de la campagne est epuise : arret propre.",
        verificateur=lambda r, c: c.budget_restant <= 0,
    ),
    RegleSpec(
        regle=Regle.CANAL_NON_AUTORISE,
        condition="requete.canal dans contexte.canaux_autorises",
        message="Ce canal n'est pas declare dans le perimetre de la mesure.",
        verificateur=lambda r, c: r.canal is not None and r.canal.value not in c.canaux_autorises,
    ),
    RegleSpec(
        regle=Regle.QUOTA_REQUETES,
        condition="requetes_utilisateur <= contexte.quota_requetes",
        message="Le nombre de requetes de cet utilisateur est borne : exploration systematique suspectee.",
        verificateur=_quota,
    ),
    RegleSpec(
        regle=Regle.INDIVIDU,
        condition="requete.groupements ne contient aucun identifiant de personne",
        message="Aucune attribution individuelle : ce groupement designe une personne.",
        verificateur=lambda r, c: any(g in GROUPEMENTS_INTERDITS for g in r.groupements),
    ),
    RegleSpec(
        regle=Regle.INDIVIDU,
        condition="requete.sortie ne contient ni classement ni score ni temps individuel",
        message="Aucune sortie ne peut porter un classement, un score ou un temps individuel.",
        verificateur=_sortie_individuelle,
    ),
    RegleSpec(
        regle=Regle.FILTRE_PERSONNE,
        condition="requete.filtres ne contient aucune cle identifiant une personne",
        message="Un identifiant de personne n'est pas accepte comme filtre.",
        verificateur=lambda r, c: any(k in FILTRES_PERSONNE for k in r.filtres),
    ),
    RegleSpec(
        regle=Regle.ATTRIBUT_RARE,
        condition="requete.filtres ne contient aucun attribut quasi-identifiant rare",
        message="Cet attribut est trop rare pour etre propose comme filtre : il re-identifierait.",
        verificateur=_attribut_rare,
    ),
    RegleSpec(
        regle=Regle.K5,
        condition=f"requete.groupe.taille >= contexte.seuil_agregation ({SEUIL_AGGREGATION_DEFAUT})",
        message="Mesure portant sur moins de cinq individus : elle est supprimee, pas arrondie.",
        verificateur=_groupe_de_travail,
    ),
    RegleSpec(
        regle=Regle.COMBINAISON,
        condition="taille_resultat_apres_filtres >= contexte.seuil_agregation",
        message="La combinaison de filtres isole moins de cinq individus.",
        verificateur=_combinaison,
    ),
    RegleSpec(
        regle=Regle.CITATION,
        condition="requete.citations == faux et aucune sortie non aggregée",
        message="Aucune citation non aggregée : elle pourrait reveler qui a travaille.",
        verificateur=lambda r, c: r.citations or "citation_non_agregee" in r.sortie,
    ),
    RegleSpec(
        regle=Regle.CORPUS_BRUT,
        condition="corpus.pseudonymise_le != nul et corpus.sensibles_filtres == vrai",
        message="Aucune lecture d'un corpus brut non assaini.",
        verificateur=_corpus_brut,
        outils=(OUTIL_CORPUS,),
    ),
    RegleSpec(
        regle=Regle.EXPORT,
        condition="export.citations toutes aggregées",
        message="Un export ne peut pas contenir de citation non aggregée.",
        verificateur=lambda r, c: r.citations or "citation_non_agregee" in r.sortie,
        outils=(OUTIL_EXPORT,),
    ),
)


def regles_violees(requete: RequeteMesure, contexte: ContextePolitique) -> tuple[Regle, ...]:
    """Every rule the request breaks, in the order of the registry."""
    trouvees: list[Regle] = []
    for spec in REGLES:
        if spec.violee(requete, contexte) and spec.regle not in trouvees:
            trouvees.append(spec.regle)
    return tuple(trouvees)


def messages(requete: RequeteMesure, contexte: ContextePolitique) -> tuple[str, ...]:
    """The human readable reasons, for the DPO and for the screen."""
    return tuple(spec.message for spec in REGLES if spec.violee(requete, contexte))


def seuil_effectif(contexte: ContextePolitique) -> int:
    """The threshold can be raised by a client, never lowered below five."""
    return max(contexte.seuil, SEUIL_AGGREGATION_DEFAUT)


def budget_suffisant(contexte: ContextePolitique, cout_estime: Decimal | None = None) -> bool:
    """ENF-09 - a run stops cleanly when the ceiling is reached."""
    if cout_estime is None:
        return contexte.budget_restant > 0
    return contexte.budget_restant >= decimal(cout_estime)
