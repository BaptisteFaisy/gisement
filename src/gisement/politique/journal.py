"""The access log (EF-53, ENF-07) and the request quota (18.4).

Every decision is logged, allowed or refused: the log of refusals is what
feeds the 1:20 moment of the demo, and what a DPO reads to check that nobody
tried to isolate an individual. The log is append-only; the purge at the end of
a campaign leaves a proof behind (ENF-06).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from gisement.politique.regles import ContextePolitique
from gisement.serialisation import empreinte, vers_json
from gisement.types.communs import SEUIL_AGGREGATION_DEFAUT
from gisement.types.conformite import AccesJournalise, Decision, Regle, RequeteMesure


@dataclass(frozen=True)
class PreuvePurge:
    """ENF-06 - a purge is proven, not asserted."""

    nb_entrees_purgees: int
    empreinte_avant: str
    purge_le: datetime


@dataclass
class JournalAcces:
    """Append-only log of every gateway decision."""

    campagne_id: str = ""
    tenant_id: str = ""
    chemin: Path | None = None
    _entrees: list[AccesJournalise] = field(default_factory=list)

    def enregistrer(
        self,
        requete: RequeteMesure,
        decision: Decision,
        contexte: ContextePolitique | None = None,
        horodatage: datetime | None = None,
    ) -> AccesJournalise:
        entree = AccesJournalise(
            id=f"ACC-{len(self._entrees) + 1:06d}",
            horodatage=horodatage or datetime.now(UTC),
            tenant_id=requete.tenant_id,
            campagne_id=requete.campagne_id,
            utilisateur=requete.utilisateur,
            role=requete.role,
            outil=requete.outil,
            autorise=decision.autorisee,
            regles_violees=decision.regles_violees,
            empreinte_requete=decision.empreinte_requete or empreinte(requete),
            motif=decision.motif,
        )
        self._entrees.append(entree)
        if self.chemin is not None:
            self._ecrire_ligne(entree)
        return entree

    def _ecrire_ligne(self, entree: AccesJournalise) -> None:
        import json

        assert self.chemin is not None
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        with self.chemin.open("a", encoding="utf-8") as fichier:
            fichier.write(json.dumps(vers_json(entree), ensure_ascii=False, sort_keys=True) + "\n")

    def entrees(self) -> tuple[AccesJournalise, ...]:
        return tuple(self._entrees)

    def refus(self) -> tuple[AccesJournalise, ...]:
        return tuple(e for e in self._entrees if not e.autorise)

    def autorisations(self) -> tuple[AccesJournalise, ...]:
        return tuple(e for e in self._entrees if e.autorise)

    def par_regle(self) -> dict[Regle, int]:
        compte: dict[Regle, int] = {}
        for entree in self.refus():
            for regle in entree.regles_violees:
                compte[regle] = compte.get(regle, 0) + 1
        return compte

    def par_utilisateur(self) -> dict[str, int]:
        compte: dict[str, int] = {}
        for entree in self._entrees:
            compte[entree.utilisateur] = compte.get(entree.utilisateur, 0) + 1
        return compte

    def purger(self, horodatage: datetime | None = None) -> PreuvePurge:
        """Destroy the log at the end of the campaign, and prove it."""
        preuve = PreuvePurge(
            nb_entrees_purgees=len(self._entrees),
            empreinte_avant=empreinte(tuple(self._entrees)),
            purge_le=horodatage or datetime.now(UTC),
        )
        self._entrees.clear()
        if self.chemin is not None and self.chemin.exists():
            self.chemin.unlink()
        return preuve


@dataclass
class CompteurRequetes:
    """18.4 - bound and log the number of queries per user, to spot probing."""

    quota: int = 200
    _compteurs: dict[tuple[str, str], int] = field(default_factory=dict)

    def incrementer(self, utilisateur: str, campagne_id: str) -> int:
        cle = (utilisateur, campagne_id)
        self._compteurs[cle] = self._compteurs.get(cle, 0) + 1
        return self._compteurs[cle]

    def nb(self, utilisateur: str, campagne_id: str) -> int:
        return self._compteurs.get((utilisateur, campagne_id), 0)

    def depasse(self, utilisateur: str, campagne_id: str) -> bool:
        return self.nb(utilisateur, campagne_id) > self.quota

    def requetes(self, utilisateur: str, campagne_id: str) -> int:
        """What the gateway context needs to evaluate the quota rule."""
        return self.nb(utilisateur, campagne_id)


def contexte_avec_quota(
    contexte: ContextePolitique, compteur: CompteurRequetes, utilisateur: str
) -> ContextePolitique:
    """Refresh a context with the current request count of one user."""
    return ContextePolitique(
        campagne_id=contexte.campagne_id,
        tenant_id=contexte.tenant_id,
        conforme=contexte.conforme,
        suspendue=contexte.suspendue,
        seuil=contexte.seuil,
        canaux_autorises=contexte.canaux_autorises,
        budget_restant=contexte.budget_restant,
        requetes_utilisateur=compteur.requetes(utilisateur, contexte.campagne_id),
        quota_requetes=compteur.quota,
        corpus_assainis=contexte.corpus_assainis,
    )


def seuil_agregation_defaut() -> int:
    return SEUIL_AGGREGATION_DEFAUT


def budget_restant(plafond: Decimal, consomme: Decimal) -> Decimal:
    return plafond - consomme
