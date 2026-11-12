"""The planner: a sequence is not a schedule (idea #9).

The sequencer answers "in which order"; the planner answers "when, with whom".
A MSP has a limited bench - two consultants, fifteen billable days each per
month - and some projects must follow others (move the suppliers to the EDI
portal *before* automating the residual orders, or you automate a volume that
is about to disappear).

The algorithm is a deterministic greedy: every month, take the eligible projects
(dependencies satisfied) by descending priority score, and fill the month's
capacity. A project is never split across months - a half-delivered automation
delivers nothing.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from gisement.types.communs import TypeAutomatisation, arrondi, decimal
from gisement.types.economie import Projet

TJM_DEFAUT = Decimal("650")


@dataclass(frozen=True)
class Dependance:
    """One project must finish before another starts."""

    projet_id: str
    apres: tuple[str, ...]
    raison: str = ""


@dataclass(frozen=True)
class Capacite:
    """The MSP's bench: how many consultant-days are available per month."""

    consultants: int = 2
    jours_par_mois: int = 15

    def jours_disponibles(self) -> Decimal:
        return decimal(self.consultants * self.jours_par_mois)


@dataclass(frozen=True)
class TachePlanifiee:
    projet_id: str
    debut_mois: int
    fin_mois: int
    jours: Decimal
    dependances_respectees: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    taches: tuple[TachePlanifiee, ...]
    impossibles: tuple[str, ...]
    raisons: Mapping[str, str]
    duree_totale_mois: int
    capacite_utilisee: Decimal
    gain_cumule: Decimal


def jours_necessaires(projet: Projet, tjm: Decimal = TJM_DEFAUT) -> Decimal:
    """Build days from the first-year cost, rounded **up**.

    A project is not split into half days: 4.1 days of work occupies a
    consultant for five days, and pretending otherwise is how a plan slips.
    """
    if tjm <= 0:
        return Decimal(0)
    return (
        arrondi(projet.gisement.cout.annee_1 / tjm, 0).__ceil__()
        if False
        else _plafond(projet.gisement.cout.annee_1 / tjm)
    )


def _plafond(valeur: Decimal) -> Decimal:
    """Ceiling to a whole number of days."""

    return Decimal(math.ceil(float(valeur)))


def dependances_de(projet_id: str, dependances: Sequence[Dependance]) -> tuple[str, ...]:
    for dependance in dependances:
        if dependance.projet_id == projet_id:
            return tuple(dependance.apres)
    return ()


def _cycles(projets: Sequence[Projet], dependances: Sequence[Dependance]) -> set[str]:
    """Every project caught in a dependency cycle."""
    graphe = {p.processus_id: dependances_de(p.processus_id, dependances) for p in projets}
    dans_cycle: set[str] = set()
    for depart in graphe:
        vus: set[str] = set()
        pile = [depart]
        while pile:
            noeud = pile.pop()
            if noeud in vus:
                if noeud == depart:
                    dans_cycle.add(depart)
                continue
            vus.add(noeud)
            pile.extend(graphe.get(noeud, ()))
    return dans_cycle


def planifier(
    projets: Sequence[Projet],
    dependances: Sequence[Dependance] = (),
    capacite: Capacite = Capacite(),
    horizon_mois: int = 24,
    tjm: Decimal = TJM_DEFAUT,
) -> Plan:
    """Schedule the actionable projects month by month, capacity-aware."""
    actionnables = [
        p for p in projets if p.deconseille is None and p.faisabilite.type != TypeAutomatisation.E
    ]
    cycles = _cycles(actionnables, dependances)
    jours = {p.processus_id: jours_necessaires(p, tjm) for p in actionnables}
    taches: list[TachePlanifiee] = []
    impossibles: dict[str, str] = {}
    for projet in actionnables:
        identifiant = projet.processus_id
        if identifiant in cycles:
            impossibles[identifiant] = "dependance circulaire"
        elif jours[identifiant] > capacite.jours_disponibles():
            impossibles[identifiant] = (
                f"depasse la capacite mensuelle ({jours[identifiant]} jours > "
                f"{capacite.jours_disponibles()} jours)"
            )
    planifiables = [p for p in actionnables if p.processus_id not in impossibles]
    _remplir(planifiables, jours, dependances, capacite, horizon_mois, taches, impossibles)
    return _construire(taches, impossibles, capacite, horizon_mois, projets)


def _remplir(
    planifiables: Sequence[Projet],
    jours: Mapping[str, Decimal],
    dependances: Sequence[Dependance],
    capacite: Capacite,
    horizon: int,
    taches: list[TachePlanifiee],
    impossibles: dict[str, str],
) -> None:
    """Greedy fill: one month at a time, best score first."""
    restants = {p.processus_id: p for p in planifiables}
    fin: dict[str, int] = {}
    mois = 1
    while restants and mois <= horizon:
        eligibles = [p for identifiant, p in restants.items() if _pret(identifiant, dependances, fin)]
        eligibles.sort(key=lambda p: (-p.score, p.processus_id))
        disponible = capacite.jours_disponibles()
        for projet in eligibles:
            besoin = jours[projet.processus_id]
            if besoin <= disponible:
                taches.append(
                    TachePlanifiee(
                        projet_id=projet.processus_id,
                        debut_mois=mois,
                        fin_mois=mois,
                        jours=besoin,
                        dependances_respectees=dependances_de(projet.processus_id, dependances),
                    )
                )
                disponible -= besoin
                fin[projet.processus_id] = mois
                del restants[projet.processus_id]
        mois += 1
    for identifiant in restants:
        blocage = _blocage(identifiant, dependances, fin, impossibles)
        impossibles[identifiant] = blocage


def _pret(projet_id: str, dependances: Sequence[Dependance], fin: Mapping[str, int]) -> bool:
    return all(ant in fin for ant in dependances_de(projet_id, dependances))


def _blocage(
    projet_id: str,
    dependances: Sequence[Dependance],
    fin: Mapping[str, int],
    impossibles: Mapping[str, str],
) -> str:
    for ant in dependances_de(projet_id, dependances):
        if ant in impossibles:
            return f"dependance non satisfaite : {ant} ({impossibles[ant]})"
        if ant not in fin:
            return f"dependance non satisfaite : {ant}"
    return "hors horizon de planification"


def _construire(
    taches: Sequence[TachePlanifiee],
    impossibles: Mapping[str, str],
    capacite: Capacite,
    horizon: int,
    projets: Sequence[Projet],
) -> Plan:
    triees = tuple(sorted(taches, key=lambda t: (t.debut_mois, t.projet_id)))
    jours_total = sum((t.jours for t in triees), Decimal(0))
    capacite_totale = capacite.jours_disponibles() * decimal(horizon)
    gains = {p.processus_id: (p.gisement.gain_annuel or Decimal(0)) for p in projets}
    return Plan(
        taches=triees,
        impossibles=tuple(sorted(impossibles)),
        raisons=dict(impossibles),
        duree_totale_mois=max((t.fin_mois for t in triees), default=0),
        capacite_utilisee=arrondi(jours_total / capacite_totale, 4) if capacite_totale else Decimal(0),
        gain_cumule=arrondi(sum((gains.get(t.projet_id, Decimal(0)) for t in triees), Decimal(0)), 2),
    )


def chemin_critique(
    projets: Sequence[Projet], dependances: Sequence[Dependance], tjm: Decimal = TJM_DEFAUT
) -> tuple[str, ...]:
    """The longest dependency chain, in days: what sets the earliest end date."""
    jours = {p.processus_id: jours_necessaires(p, tjm) for p in projets}
    memo: dict[str, tuple[Decimal, tuple[str, ...]]] = {}

    def parcourir(identifiant: str, vus: frozenset[str]) -> tuple[Decimal, tuple[str, ...]]:
        if identifiant in memo:
            return memo[identifiant]
        if identifiant in vus:
            return Decimal(0), ()
        meilleur = (Decimal(0), ())
        for ant in dependances_de(identifiant, dependances):
            if ant not in jours:
                continue
            cout, chaine = parcourir(ant, vus | {identifiant})
            if cout > meilleur[0]:
                meilleur = (cout, chaine)
        resultat = (meilleur[0] + jours.get(identifiant, Decimal(0)), meilleur[1] + (identifiant,))
        memo[identifiant] = resultat
        return resultat

    if not projets:
        return ()
    return max((parcourir(p.processus_id, frozenset()) for p in projets), key=lambda c: c[0])[1]


def gantt(plan: Plan) -> str:
    """An ASCII Gantt: one line per task, one cell per month."""
    if not plan.taches:
        return "(aucune tache planifiee)"
    horizon = max(t.fin_mois for t in plan.taches)
    lignes = []
    for tache in plan.taches:
        barre = "".join(
            "#" if tache.debut_mois <= m <= tache.fin_mois else "." for m in range(1, horizon + 1)
        )
        lignes.append(f"{tache.projet_id:6s} |{barre}| {tache.jours} j")
    return "\n".join(lignes)


def est_actionnable(projet: Projet) -> bool:
    return projet.deconseille is None and projet.faisabilite.type != TypeAutomatisation.E
