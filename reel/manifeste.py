"""The manifest of the REAL corpus: provenance, window, volumes, denominator.

The synthetic manifest is a generator's output. This one is *read* from the real
artefacts downloaded by `reel/collecteurs/`: every figure comes from a file that
came out of a real public system, and the source, the licence and the checksum
of the raw download sit next to it.

Two rules are published rather than hidden:
  - a ticket and a CI step carry a **measured** duration; an email and a
    document do not, so their per-item handling time comes from
    `config/corpus_reel.json` and is printed in the manifest itself;
  - the client declares no hourly rate (13.4), so `taux_horaire` stays null and
    the real campaign publishes hours, not euros.

    python3 -m reel.manifeste --racine reel
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.serialisation import lire_json
from gisement.types.communs import decimal

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "config" / "corpus_reel.json"
CANAUX_FICHIERS = {
    "tickets": "donnees/tickets/tickets.jsonl",
    "courriels": "donnees/courriels/courriels.jsonl",
    "documents": "donnees/documents/documents.json",
}
JOURNAUX = "donnees/journaux/journaux.csv"
PROCEDURES = "donnees/procedures"
BRUT = "brut"


def charger_config() -> dict[str, Any]:
    """The versioned perimeter and published estimates of the real corpus."""
    return lire_json(CONFIG)


def lire_jsonl(chemin: Path) -> list[dict[str, Any]]:
    if not chemin.exists():
        return []
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    return [json.loads(ligne) for ligne in lignes if ligne.strip()]


def lire_csv(chemin: Path) -> list[dict[str, Any]]:
    if not chemin.exists():
        return []
    with chemin.open(encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier))


def compter(racine: Path) -> dict[str, int]:
    """Real record count per channel, read from the artefacts themselves."""
    comptes = {
        canal: len(lire_jsonl(racine / relatif))
        for canal, relatif in CANAUX_FICHIERS.items()
        if canal != "documents"
    }
    comptes["documents"] = len(_documents(racine))
    comptes["journaux"] = len(lire_csv(racine / JOURNAUX))
    comptes["procedures"] = len(list((racine / PROCEDURES).glob("*.md")))
    comptes["appels"] = 0
    return comptes


def _horodatages(racine: Path) -> list[str]:
    """The real window, read on the **work** channels only.

    A design document is the written procedure, not a unit of work: its real
    version date (a KIP edited last week about work done in 2025) would stretch
    the campaign window over years. Documents are excluded, and that is said.
    """
    valeurs: list[str] = []
    for brut in lire_jsonl(racine / CANAUX_FICHIERS["tickets"]):
        valeurs.append(str(brut.get("horodatage", "")))
    for brut in lire_jsonl(racine / CANAUX_FICHIERS["courriels"]):
        valeurs.append(str(brut.get("horodatage", "")))
    for brut in lire_csv(racine / JOURNAUX):
        valeurs.append(str(brut.get("horodatage", "")))
    return sorted(v for v in valeurs if len(v) >= 10)


def _documents(racine: Path) -> list[dict[str, Any]]:
    """`documents.json` may be a list or an object with a `documents` key."""
    chemin = racine / CANAUX_FICHIERS["documents"]
    if not chemin.exists():
        return []
    brut = lire_json(chemin)
    if isinstance(brut, dict):
        return list(brut.get("documents", []))
    return list(brut)


def fenetre(racine: Path) -> dict[str, Any]:
    """The real observation window: the earliest and latest real timestamp."""
    stamps = _horodatages(racine)
    if not stamps:
        aujourdhui = date.today().isoformat()
        return {"debut": aujourdhui, "fin": aujourdhui, "nb_mois": 1, "mois": []}
    debut, fin = stamps[0][:10], stamps[-1][:10]
    mois = sorted({s[:7] for s in stamps})
    return {
        "debut": debut,
        "fin": fin,
        "nb_mois": max(1, len(mois)),
        "mois": mois,
    }


def services(racine: Path) -> tuple[str, ...]:
    """The real services of the corpus: the Jira components and the CI jobs."""
    vus: set[str] = set()
    for brut in lire_jsonl(racine / CANAUX_FICHIERS["tickets"]):
        service = str(brut.get("service", "")).strip()
        if service:
            vus.add(service)
    for brut in lire_csv(racine / JOURNAUX):
        service = str(brut.get("service", "")).strip()
        if service:
            vus.add(service)
    return tuple(sorted(vus))


def heures_observees(racine: Path, config: dict[str, Any]) -> dict[str, Any]:
    """The coverage denominator: measured hours, plus one published rule.

    A real ticket of this client carries no handling time (its Jira never logs
    work, its GitHub tracker has no clock), so the denominator applies to every
    real record the median unit duration of the versioned catalogue - a figure
    that comes from the catalogue, not from an opinion. Where a duration **is**
    measured, it replaces the rule.
    """
    regle = decimal(config["estimations_publiees"]["minutes_par_enregistrement"])
    comptes = compter(racine)
    tickets = lire_jsonl(racine / CANAUX_FICHIERS["tickets"])
    journaux = lire_csv(racine / JOURNAUX)
    mesurees = sum(decimal(b.get("duree_traitement_minutes") or 0) for b in tickets)
    mesurees += sum((decimal(b.get("duree_secondes") or 0) for b in journaux), Decimal(0)) / 60
    nb_mesures = sum(1 for b in tickets if b.get("duree_traitement_minutes")) + sum(
        1 for b in journaux if b.get("duree_secondes")
    )
    nb_estimes = comptes["tickets"] + comptes["courriels"] + comptes["documents"] - nb_mesures
    detail = {
        "heures_mesurees": str((mesurees / 60).quantize(Decimal("0.1"))),
        "enregistres_estimes": nb_estimes,
        "minutes_par_enregistrement": str(regle),
    }
    total = mesurees / 60 + decimal(nb_estimes) * regle / 60
    detail["total_heures"] = str(total.quantize(Decimal("0.1")))
    return detail


def provenance(racine: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Sources, licences and the checksum of every raw download."""
    bruts: dict[str, Any] = {}
    dossier = racine / BRUT
    if dossier.exists():
        for fichier in sorted(dossier.iterdir()):
            if fichier.is_file():
                bruts[fichier.name] = {
                    "octets": fichier.stat().st_size,
                    "sha256": hashlib.sha256(fichier.read_bytes()).hexdigest(),
                }
    if (dossier / "provenance.json").exists():
        bruts.update(lire_json(dossier / "provenance.json"))
    return {
        "sources": config["sources"],
        "absents": config["absents"],
        "brut": bruts,
        "pseudonymisation": config["pseudonymisation"],
    }


def services_sous_seuil(racine: Path, seuil: int) -> list[str]:
    """The real components the corpus saw too little of: published as uncovered."""
    comptes: dict[str, int] = {}
    for brut in lire_jsonl(racine / CANAUX_FICHIERS["tickets"]):
        service = str(brut.get("service", "")).strip().lower()
        if service:
            comptes[service] = comptes.get(service, 0) + 1
    return sorted(s for s, n in comptes.items() if n < seuil)


def non_couvert(racine: Path, config: dict[str, Any]) -> list[str]:
    """What the real campaign does NOT cover, said out loud (R14)."""
    seuil = int(config.get("seuil_volume_processus", 25))
    raisons = [f"{a['canal']} : {a['raison']}" for a in config.get("absents", [])]
    sous_seuil = services_sous_seuil(racine, seuil)
    if sous_seuil:
        raisons.append(f"composants sous le seuil de {seuil} activites observees : " + ", ".join(sous_seuil))
    return raisons


def construire(racine: Path) -> dict[str, Any]:
    """The whole manifest, read from the artefacts (no figure is invented)."""
    config = charger_config()
    heures = heures_observees(racine, config)
    fenetre_reelle = fenetre(racine)
    vus = list(services(racine))
    client = dict(config["client"])
    client.update({"services": vus, "fenetre": fenetre_reelle})
    return {
        "version": "1.0",
        "corpus": "reel",
        "note": "Manifeste lu sur des artefacts reels telecharges ; voir `provenance`.",
        "client": client,
        "campagne": config["campagne"],
        "graine": int(config["campagne"]["graine"]),
        "fenetre": fenetre_reelle,
        "mois": fenetre_reelle["mois"],
        "services": vus,
        "activites_par_canal": {
            canal: nombre for canal, nombre in compter(racine).items() if canal != "procedures"
        },
        "procedures_ecrites": compter(racine)["procedures"],
        "couverture": {
            "volume_travail_estime_heures": heures["total_heures"],
            "regle": config["estimations_publiees"]["regle"],
            "detail_heures": heures,
            "non_couvert": non_couvert(racine, config),
        },
        "taux_horaire": config.get("taux_horaire"),
        "listes": {"prenoms": [], "noms": []},
        "filigrane": "CORPUS REEL - DONNEES PUBLIQUES ASF, PSEUDONYMISEES A L'INGESTION",
        **provenance(racine, config),
    }


def ecrire(racine: Path) -> Path:
    chemin = racine / "donnees" / "manifeste.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(construire(racine), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return chemin


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--racine", default=str(RACINE / "reel"))
    args = parseur.parse_args(argv)
    chemin = ecrire(Path(args.racine))
    print(f"manifeste ecrit : {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
