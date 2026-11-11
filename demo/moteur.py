"""Allocation plan and record builders of the synthetic client (lot 3).

The ground truth (`demo/spec-processus.json`) says how many occurrences of each
process happen in each month of the window. This module turns that plan into
raw channel records, so that a collector measuring the generated corpus finds
back the volumes of the ground truth - and so the three traps of annex F.3 are
actually present in the data instead of being promised.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime

from demo.listes import (
    BRUIT_COURRIELS,
    BRUIT_TICKETS,
    DOCUMENTS,
    FILIGRANE,
    PRODUITS,
    SYSTEMES,
    personne,
    societe,
)

#: The calls channel is a sample of the coordination work: it carries at most
#: this many exchanges, spread over the recorded calls (annex F.2: six hours).
CAPACITE_APPELS = 600

#: Nominal channel volumes of annex F.2, plus the call-segment capacity.
CAPACITES: dict[str, int] = {
    "journaux": 12400,
    "tickets": 4800,
    "courriels": 2000,
    "appels": CAPACITE_APPELS,
    "documents": 200,
}

#: Total recorded call time of the campaign (annex F.2: six hours).
MINUTES_APPELS = 360

#: Preference of a channel for a motif family: the realistic place of the trace.
PREFERENCE: dict[str, tuple[str, ...]] = {
    "RESS": ("courriels", "journaux", "tickets"),
    "RAPPR": ("journaux", "documents", "tickets"),
    "VERI": ("tickets", "journaux", "documents"),
    "RELAN": ("tickets", "courriels", "journaux"),
    "CLASS": ("documents", "journaux", "tickets"),
    "REPO": ("journaux", "documents", "tickets"),
    "COORD": ("appels", "tickets", "courriels"),
    "RECH": ("tickets", "appels", "documents"),
}

#: Processes whose channel split is imposed by the spec rather than by capacity.
POIDS_IMPOSES: dict[str, dict[str, float]] = {
    # annex D: 78 % of the supplier orders arrive by email, the EDI portal is unused.
    "P-07": {"courriels": 0.78, "journaux": 0.15, "tickets": 0.07},
}

JOURS_OUVRES = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class Occurrence:
    """One activity of one process, assigned to one channel."""

    processus: str
    motif: str
    service: str
    mois: int
    rang: int
    canal: str
    atypique: bool
    geste: str
    jours: float
    systemes: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    occurrences: tuple[Occurrence, ...]
    par_canal: dict[str, int]
    bruit_par_canal: dict[str, int]
    mois: tuple[str, ...]


def mois_de_la_fenetre(fenetre: dict) -> tuple[str, ...]:
    """The month labels of the window, oldest first."""
    debut = date.fromisoformat(fenetre["debut"])
    return tuple(
        f"{debut.year + (debut.month - 1 + i) // 12:04d}-{(debut.month - 1 + i) % 12 + 1:02d}"
        for i in range(int(fenetre["nb_mois"]))
    )


def _ordre_canaux(canaux: tuple[str, ...], motif: str, impose: dict | None = None) -> tuple[str, ...]:
    """Channels of a process, ordered by where the trace realistically lands."""
    if impose:
        return tuple(c for c in canaux if c in impose)
    preferes = PREFERENCE.get(motif.split("-")[0], ())
    return tuple(sorted(canaux, key=lambda c: (preferes.index(c) if c in preferes else 9, c)))


def _eligibles(ordre: tuple[str, ...], reste: dict[str, int]) -> list[str]:
    eligibles = [c for c in ordre if reste.get(c, 0) > 0]
    if not eligibles:
        # every channel of this process is full: fall back on the least loaded
        # one of the corpus, so a nominal volume is never exceeded
        eligibles = [c for c in CAPACITES if reste.get(c, 0) > 0]
    return eligibles or list(CAPACITES)


def _choisir_canal(
    canaux: tuple[str, ...],
    motif: str,
    reste: dict[str, int],
    rng: random.Random,
    rang: int,
    impose: dict | None = None,
) -> str:
    """Pick a channel: imposed weights, else the least loaded eligible one."""
    ordre = _ordre_canaux(canaux, motif, impose)
    eligibles = _eligibles(ordre, reste)
    if impose:
        return _tirage_pondere(eligibles, impose, rng)
    return min(eligibles, key=lambda c: (-reste.get(c, 0), c, rang))


def _tirage_pondere(eligibles: list[str], poids: dict[str, float], rng: random.Random) -> str:
    total = sum(poids.get(c, 0.05) for c in eligibles)
    tirage = rng.random() * total
    cumul = 0.0
    for canal in eligibles:
        cumul += poids.get(canal, 0.05)
        if tirage <= cumul:
            return canal
    return eligibles[-1]


def choisir_motif(processus: dict, rng: random.Random) -> str:
    """The primary motif carries 80 % of the occurrences, the others the rest."""
    motifs = processus["motifs"]
    if len(motifs) == 1 or rng.random() < 0.80:
        return motifs[0]
    return motifs[rng.randrange(1, len(motifs))]


def planifier(verite: dict, graine: int) -> Plan:
    """Spread every occurrence of every process over the five channels."""
    rng = random.Random(graine)
    reste = dict(CAPACITES)
    occurrences: list[Occurrence] = []
    par_canal = dict.fromkeys(CAPACITES, 0)
    mois = mois_de_la_fenetre(verite["client"]["fenetre"])
    for processus in verite["processus"]:
        gestes = _gestes(processus, verite)
        impose = POIDS_IMPOSES.get(processus["id"])
        for index_mois, volume in enumerate(processus["occurrences"]["serie"]):
            for rang in range(_arrondi(volume)):
                motif = choisir_motif(processus, rng)
                canal = _choisir_canal(tuple(processus["canaux"]), motif, reste, rng, rang, impose)
                reste[canal] = max(0, reste.get(canal, 0) - 1)
                par_canal[canal] += 1
                occurrences.append(
                    Occurrence(
                        processus=processus["id"],
                        motif=motif,
                        service=processus["service"],
                        mois=index_mois,
                        rang=rang,
                        canal=canal,
                        atypique=_atypique(processus, rng),
                        geste=_geste_du_motif(motif, gestes, processus),
                        jours=float(processus["duree_unitaire_minutes"]),
                        systemes=_systemes(processus, verite),
                    )
                )
    bruit = {c: max(0, CAPACITES[c] - par_canal[c]) for c in CAPACITES}
    return Plan(tuple(occurrences), par_canal, bruit, mois)


def _geste_du_motif(motif: str, gestes: tuple[str, ...], processus: dict) -> str:
    """The canonical sentence of the chosen motif (fixed, so it groups)."""
    index = processus["motifs"].index(motif) if motif in processus["motifs"] else 0
    return gestes[index % len(gestes)]


def _arrondi(valeur: object) -> int:
    return round(float(valeur))


def _atypique(processus: dict, rng: random.Random) -> bool:
    return rng.random() < float(processus["part_atypique"])


def _gestes(processus: dict, verite: dict) -> tuple[str, ...]:
    """The canonical sentences of the motifs of a process (fixed, so that two
    occurrences of the same gesture share one fingerprint)."""
    gestes = []
    for ref in processus["motifs"]:
        motif = verite["catalogue"].get(ref)
        if motif:
            gestes.append(motif["modele_texte"])
    return tuple(gestes) or (processus["nom"],)


def _systemes(processus: dict, verite: dict) -> tuple[str, ...]:
    systemes: list[str] = []
    for ref in processus["motifs"]:
        motif = verite["catalogue"].get(ref)
        if motif:
            systemes.extend(motif.get("systemes", ()))
    return tuple(dict.fromkeys(systemes)) or ("erp",)


def instant(mois_label: str, repartition: str, rng: random.Random) -> datetime:
    """A working timestamp inside the month, spread according to 13.1."""
    annee, mois = mois_label.split("-")[0], mois_label.split("-")[1]
    annee_int, mois_int = int(annee), int(mois)
    jour = rng.randint(1, 28)
    while date(annee_int, mois_int, jour).weekday() not in JOURS_OUVRES:
        jour = rng.randint(1, 28)
    if repartition == "regroupee":
        heure = rng.choice((9, 10, 14, 15))
        minute = rng.randint(0, 59)
    elif repartition == "semi_regroupee":
        heure = rng.choice((8, 9, 10, 11, 14, 15, 16, 17))
        minute = rng.randint(0, 59)
    elif repartition == "interruptive":
        heure = rng.randint(8, 18)
        minute = rng.randint(0, 59)
    else:
        heure = rng.randint(7, 18)
        minute = rng.randint(0, 59)
    return datetime(annee_int, mois_int, jour, heure, minute, rng.randint(0, 59))


def details(rng: random.Random, atypique: bool) -> dict[str, object]:
    """Instance details: they vary, and they never feed the fingerprint."""
    return {
        "societe": societe(rng),
        "produit": rng.choice(PRODUITS),
        "montant": f"{rng.uniform(80, 9500):.2f}",
        "contact": personne(rng),
        "atypique": atypique,
        "mention": "cas inhabituel, hors catalogue" if atypique else "cas standard",
    }


def libelle_bruit(canal: str, rng: random.Random) -> str:
    if canal == "courriels":
        return rng.choice(BRUIT_COURRIELS)
    if canal == "documents":
        return rng.choice([nom for _, nom in DOCUMENTS])
    return rng.choice(BRUIT_TICKETS)


def systeme_libelle(cle: str) -> str:
    return SYSTEMES.get(cle, cle.title())


def filigrane() -> str:
    return FILIGRANE
