"""The tickets channel of the REAL corpus: two real trackers, one real window.

    python3 -m reel.collecteurs.tickets --depuis 2025-05-01 --jusqu 2025-10-31

A real client migrates. The Apache Kafka project still has its Jira, but most of
the work of the last years happens in GitHub issues and pull requests: reading
only one of the two measures work that is no longer done. This collector reads
**both**, over real HTTPS, and writes one channel file where `systeme` says
which tool a record came from.

Nothing is invented:
  - the volume is the real count of real tickets of a real component or label;
  - the identities are real, and the product's own sanitiser removes them at
    ingestion (R3), in the structured fields *and* in the free text;
  - the **duration is not published as measured**: neither Jira (`timespent` is
    empty on this project) nor GitHub time-stamps the work. The field stays
    null, so the engine infers the duration from the versioned catalogue and
    says so. The real resolution delay is kept, and published as a delay.

The raw download goes to `reel/brut/` (gitignored, never served by the portal).
"""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from typing import Any

from gisement.connecteurs import ClientHttpReel, SourceJira, normaliser_ticket
from gisement.connecteurs.github import SourceGithub
from gisement.types.communs import Canal, decimal
from reel.collecteurs.commun import (
    DONNEES,
    LONGUEUR_DESCRIPTION,
    assainir,
    ecrire_brut,
    ecrire_jsonl,
    horodatage,
    provenance,
    tronquer,
)

BASE_JIRA = "https://issues.apache.org/jira/rest/api/2"
PROPRIETAIRE, DEPOT = "apache", "kafka"
SEUIL_ATYPIQUE_ALLERS_RETOURS = 5
PRIORITES_ATYPIQUES = frozenset({"blocker", "critical"})
SORTIE = DONNEES / "tickets" / "tickets.jsonl"


def jql(projet: str, depuis: str, jusqu: str) -> str:
    """The real perimeter: one project, one window, the tickets with a component.

    The window is on the **creation** date: a ticket created in 2013 and closed
    last month belongs to the work of 2013, and mixing the two would spread one
    campaign over fourteen years.
    """
    return (
        f"project = {projet} AND component is not EMPTY AND resolution != Unresolved "
        f'AND created >= "{depuis}" AND created <= "{jusqu}" ORDER BY created ASC'
    )


def telecharger_jira(projet: str, depuis: str, jusqu: str, pas: int) -> list[dict[str, Any]]:
    """The real Jira, paginated by offset (`startAt` / `total`)."""
    source = SourceJira(
        ClientHttpReel(), projet=projet, base=BASE_JIRA, jql=jql(projet, depuis, jusqu), pas=pas
    )
    return list(source.pages_brutes())


def telecharger_github(depuis: str, jusqu: str, pas: int) -> list[dict[str, Any]]:
    """The real GitHub tracker. A token is read from the environment if present,
    and is never written anywhere: it only raises the rate limit."""
    jeton = os.environ.get("GITHUB_TOKEN", "")
    entetes = {"Authorization": f"Bearer {jeton}"} if jeton else {}
    client = ClientHttpReel(entetes=entetes)
    source = SourceGithub(client, PROPRIETAIRE, DEPOT, depuis=depuis, jusqu=jusqu, pas=pas)
    return list(source.bruts())


def vers_jira(brut: dict[str, Any]) -> dict[str, Any]:
    """A raw GitHub issue in the Jira shape the shared normaliser reads."""
    return SourceGithub(None, PROPRIETAIRE, DEPOT).vers_jira(brut)


def _slug(nom: Any) -> str:
    return str(nom or "").strip().lower().replace("-", "_").replace(" ", "_")


def composants_jira(projet: str) -> tuple[str, ...]:
    """The real component list of the real project - one request, cached on disk.

    A real GitHub label is not a real perimeter: `ci-approved` and
    `backport-candidate` are workflow tags. The intersection of the two real
    lists (the Jira components and the GitHub labels) is what makes one
    perimeter key out of two trackers, so a label that is not a real component
    of the project does not become a process.
    """
    from gisement.serialisation import lire_json
    from reel.collecteurs.commun import BRUT, ecrire_json

    cache = BRUT / "composants_jira.json"
    if cache.exists():
        return tuple(lire_json(cache))
    racine = BASE_JIRA.rsplit("/rest", 1)[0]
    reponse = ClientHttpReel().get(f"{racine}/rest/api/2/project/{projet}/components")
    noms = tuple(sorted({_slug(c.get("name")) for c in reponse if c.get("name")}))
    ecrire_json(cache, list(noms))
    return noms


def service_reel(champs: dict[str, Any], connus: tuple[str, ...]) -> str:
    """The real perimeter key: the first component this tool really knows."""
    for composant in champs.get("components") or []:
        slug = _slug(composant.get("name") if isinstance(composant, dict) else composant)
        if not connus or slug in connus:
            return slug
    return "sans_composant"


def _delai_jours(champs: dict[str, Any]) -> Decimal | None:
    """The real elapsed delay between creation and resolution, in days."""
    from datetime import datetime

    debut, fin = (
        horodatage(champs.get("created")),
        horodatage(champs.get("resolutiondate") or champs.get("closed_at")),
    )
    if not debut or not fin:
        return None
    try:
        delta = datetime.fromisoformat(fin) - datetime.fromisoformat(debut)
    except ValueError:
        return None
    return decimal(round(delta.total_seconds() / 86400.0, 2))


def _atypique(champs: dict[str, Any]) -> bool:
    """A real, observable rule: many round trips, or a blocking priority."""
    priorite = str((champs.get("priority") or {}).get("name", "")).lower()
    commentaires = int((champs.get("comment") or {}).get("total", 0) or 0)
    return commentaires >= SEUIL_ATYPIQUE_ALLERS_RETOURS or priorite in PRIORITES_ATYPIQUES


def normaliser(brut: dict[str, Any], source: str, connus: tuple[str, ...] = ()) -> dict[str, Any]:
    """A real Jira or GitHub issue -> the frozen ticket schema of CONTRACTS §5."""
    if source == "github":
        brut = vers_jira(brut)
    champs = brut.get("fields", {})
    ticket = normaliser_ticket(brut, source)
    ticket.update(
        {
            "service": service_reel(champs, connus),
            "site": "apache",
            "description": tronquer(champs.get("description"), LONGUEUR_DESCRIPTION),
            "horodatage": horodatage(champs.get("created")),
            "duree_traitement_minutes": None,
            "statut": str((champs.get("status") or {}).get("name", "")).lower(),
            "allers_retours": int((champs.get("comment") or {}).get("total", 0) or 0),
            "atypique": _atypique(champs),
            "delai_resolution_jours": str(_delai_jours(champs) or ""),
            "labels": [str(x) for x in (champs.get("labels") or [])],
            "resolution": str((champs.get("resolution") or {}).get("name", "")),
            "provenance": "reel",
        }
    )
    return ticket


def identites_reelles(bruts: list[dict[str, Any]], source: str) -> tuple[str, ...]:
    """The real identities the structured fields carry: they must leave the text too."""
    vues: set[str] = set()
    for brut in bruts:
        champs = brut.get("fields", {}) if source == "jira" else brut
        if source == "github":
            for clef in ("assignee", "user"):
                personne = champs.get(clef) or {}
                if personne.get("login"):
                    vues.add(str(personne["login"]))
            continue
        for clef in ("assignee", "reporter"):
            personne = champs.get(clef) or {}
            for cle in ("displayName", "name"):
                if isinstance(personne, dict) and personne.get(cle):
                    vues.add(str(personne[cle]))
    return tuple(v for v in vues if v)


def _median(valeurs: list[Decimal]) -> str:
    triees = sorted(valeurs)
    return str(triees[len(triees) // 2]) if triees else ""


def collecter(depuis: str, jusqu: str, sources: tuple[str, ...], pas: int) -> dict[str, Any]:
    """Download both real trackers, normalise, sanitise once, write once."""
    bruts: list[dict[str, Any]] = []
    origines: list[str] = []
    figures: dict[str, Any] = {}
    if "jira" in sources:
        bruts_jira = telecharger_jira("KAFKA", depuis, jusqu, pas)
        bruts.extend(bruts_jira)
        origines.extend(["jira"] * len(bruts_jira))
        figures["jira"] = len(bruts_jira)
    if "github" in sources:
        bruts_github = telecharger_github(depuis, jusqu, pas)
        bruts.extend(bruts_github)
        origines.extend(["github"] * len(bruts_github))
        figures["github"] = len(bruts_github)
    _, empreinte = ecrire_brut("tickets.jsonl.gz", bruts)
    connus = composants_jira("KAFKA")
    tickets = [normaliser(brut, origine, connus) for brut, origine in zip(bruts, origines, strict=True)]
    identites = identites_reelles(
        [b for b, o in zip(bruts, origines, strict=True) if o == "jira"], "jira"
    ) + identites_reelles([b for b, o in zip(bruts, origines, strict=True) if o == "github"], "github")
    propres, rapport = assainir(tickets, Canal.TICKETS, identites)
    ecrire_jsonl(SORTIE, propres)
    for origine, nombre in figures.items():
        provenance(
            f"tickets/{origine}",
            "Apache Jira" if origine == "jira" else "GitHub Issues (apache/kafka)",
            BASE_JIRA if origine == "jira" else f"https://github.com/{PROPRIETAIRE}/{DEPOT}/issues",
            nombre,
            sum(1 for t in propres if t["systeme"] == origine),
            empreinte,
        )
    rapport.update(
        {
            "sources": figures,
            "fenetre": [depuis, jusqu],
            "delai_resolution_median_jours": _median(
                [decimal(t["delai_resolution_jours"]) for t in propres if t["delai_resolution_jours"]]
            ),
            "part_atypique_reelle": str(round(sum(t["atypique"] for t in propres) / max(1, len(propres)), 4)),
            "duree": "non mesuree : aucun des deux outils reels ne horodate le travail",
        }
    )
    return rapport


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--depuis", default="2025-05-01")
    parseur.add_argument("--jusqu", default="2025-10-31")
    parseur.add_argument("--sources", default="jira,github")
    parseur.add_argument("--pas", type=int, default=100)
    args = parseur.parse_args(argv)
    rapport = collecter(args.depuis, args.jusqu, tuple(args.sources.split(",")), args.pas)
    print(json.dumps(rapport, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
