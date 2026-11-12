"""The documents and written-procedures channels of the REAL corpus.

    python3 -m reel.collecteurs.documents --max 150 --procedures 24

The real client's design documents are its **written procedures**: the KIPs of
the Apache Kafka project, on the ASF's public Confluence. Gisement reads them
last, to measure the gap with the observed work (9.1) - so this collector writes
both a real `documents.json` (the frozen schema) and a real procedure per KIP,
in the markdown shape `gisement.processus.procedure.lire_procedure` reads.

Two honest limits, said here rather than hidden:
  - the extraction is a **local deterministic extractor** (structure, tables,
    sensitive categories). In production this stage is Bedrock Data Automation;
    it needs AWS credentials and is not run here. The confidence published is
    the real share of the expected KIP structure that was found, not a guess.
  - the durations of this channel are not measured: a document has no handling
    time in the source, so the catalogue's typical duration applies.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from typing import Any

from gisement.assainissement import detecter_categories, pseudonymiser_texte
from gisement.connecteurs import ClientHttpReel
from gisement.connecteurs.confluence import SourceConfluence, html_vers_texte, tableaux
from gisement.types.communs import Canal
from reel.collecteurs.commun import (
    CLE_PSEUDONYMISATION,
    DONNEES,
    SEL_PSEUDONYMISATION,
    assainir,
    ecrire_brut,
    ecrire_json,
    horodatage,
    provenance,
    tronquer,
)

BASE_REELLE = "https://cwiki.apache.org/confluence/rest/api"
BASE_JIRA = "https://issues.apache.org/jira/rest/api/2"
CQL = 'space=KAFKA AND type=page AND title~"KIP" ORDER BY lastmodified DESC'
SECTIONS_ATTENDUES = (
    "motivation",
    "proposed changes",
    "public interfaces",
    "compatibility",
    "rejected alternatives",
)
MOTIF_KIP = re.compile(r"\bKIP-(\d+)\b", re.I)
MOTIF_JIRA = re.compile(r"\b([A-Z]{2,}-\d{2,6})\b")
MOTIF_STATUT = re.compile(r"\b(status|state)\s*[:\-]\s*([A-Za-z \-]{3,40})", re.I)
CARACTERES_PAR_PAGE = 3000
LONGUEUR_TEXTE = 4000


def telecharger(maximum: int, pas: int) -> list[dict[str, Any]]:
    """The real KIP pages, most recently modified first."""
    source = SourceConfluence(
        ClientHttpReel(timeout=60.0),
        espace="KAFKA",
        base=BASE_REELLE,
        cql=CQL,
        pas=pas,
        max_pages=math.ceil(maximum / pas),
    )
    bruts = []
    for brut in source.bruts():
        if MOTIF_KIP.search(str(brut.get("title", ""))):
            bruts.append(brut)
        if len(bruts) >= maximum:
            break
    return bruts


def _texte_reel(brut: dict[str, Any]) -> str:
    corps = (brut.get("body") or {}).get("storage") or {}
    return html_vers_texte(str(corps.get("value", "")))


def _reference(brut: dict[str, Any]) -> str:
    trouve = MOTIF_KIP.search(str(brut.get("title", "")) + " " + _texte_reel(brut)[:400])
    return f"KIP-{trouve.group(1)}" if trouve else f"PAGE-{brut.get('id')}"


def _statut_reel(texte: str) -> str:
    trouve = MOTIF_STATUT.search(texte[:3000])
    return " ".join(trouve.group(2).split()).lower() if trouve else ""


def _sections(texte: str) -> list[str]:
    minuscule = texte.lower()
    return [s for s in SECTIONS_ATTENDUES if s in minuscule]


def _confiance(texte: str) -> str:
    """A real score: the share of the expected KIP structure that is present."""
    if not texte:
        return "0"
    return str(round(len(_sections(texte)) / len(SECTIONS_ATTENDUES), 2))


def jira_lies(texte: str, limite: int = 10) -> list[str]:
    """The real tracker keys a KIP points at ("JIRA: KAFKA-15143")."""
    vus: list[str] = []
    for cle in MOTIF_JIRA.findall(texte[:6000]):
        if cle not in vus and not cle.startswith("KIP-"):
            vus.append(cle)
        if len(vus) >= limite:
            break
    return vus


def service_reel(cles: list[str], services_par_cle: dict[str, str]) -> str:
    """The real perimeter of a KIP: the component of the tracker issues it cites.

    A design document that names no tracked issue stays at project level: a
    component guessed from an English word ("core", "config", "tools" are also
    ordinary words) would invent a perimeter that does not exist.
    """
    comptes: dict[str, int] = {}
    for cle in cles:
        service = services_par_cle.get(cle)
        if service:
            comptes[service] = comptes.get(service, 0) + 1
    if not comptes:
        return "kafka"
    return max(comptes.items(), key=lambda item: (item[1], item[0]))[0]


def services_par_cle(cles: list[str]) -> dict[str, str]:
    """The real component of every cited tracker key, asked to the real Jira.

    A KIP cites issues that are often older than the campaign window, so the
    answer cannot come from the tickets already collected: it is asked to the
    real system, one batched JQL query per 50 keys, and cached on disk.
    """
    from gisement.connecteurs import ClientHttpReel, SourceJira
    from gisement.serialisation import lire_json
    from reel.collecteurs.commun import BRUT, ecrire_json

    cache = BRUT / "composants_par_cle.json"
    connu: dict[str, str] = dict(lire_json(cache)) if cache.exists() else {}
    manquantes = sorted({c for c in cles if c not in connu})
    client = ClientHttpReel()
    for lot in [manquantes[i : i + 50] for i in range(0, len(manquantes), 50)]:
        jql = f"issue in ({','.join(lot)})"
        source = SourceJira(client, projet="KAFKA", base=BASE_JIRA, jql=jql, champs=("components",))
        for brut in source.pages_brutes():
            champs = brut.get("fields", {})
            composants = champs.get("components") or []
            slug = _slug(composants[0].get("name")) if composants else ""
            connu[str(brut.get("key", ""))] = slug or "kafka"
        for cle in lot:
            connu.setdefault(cle, "")
    ecrire_json(cache, connu)
    return connu


def _slug(nom: Any) -> str:
    return str(nom or "").strip().lower().replace("-", "_").replace(" ", "_")


def pseudonymiser_texte_reel(texte: str, auteurs: tuple[str, ...]) -> str:
    """The real authors leave the procedure text, irreversibly."""
    propre, _ = pseudonymiser_texte(texte, CLE_PSEUDONYMISATION, SEL_PSEUDONYMISATION, noms=auteurs)
    return propre


def ecrire_procedure(ref: str, brut: dict[str, Any], texte: str, auteurs: tuple[str, ...]) -> str:
    """One real written procedure, in the shape the gap detector reads."""
    version = (brut.get("version") or {}).get("number", "?")
    quand = horodatage((brut.get("version") or {}).get("when", ""))[:10]
    lien = f"{BASE_REELLE.rsplit('/rest', 1)[0]}/pages/viewpage.action?pageId={brut.get('id')}"
    objet = _objet_reel(texte)
    corps = (
        f"<!-- source: {lien}, version {version}, date {quand} -->\n"
        f"# {ref} - {brut.get('title', '')}\n\n"
        "> CORPUS REEL - document de conception public de l'ASF, pseudonymise.\n\n"
        f"**Reference** : {ref}\n**Version** : {version} du {quand}\n\n"
        f"## Objet\n\n{objet}\n\n"
        f"## Modalites\n\n{_modalites(texte)}\n\n"
        "## Note de la mesure\n\n"
        "Section ecrite par la seconde passe de la mesure reelle "
        "(`reel/corpus.py`) : elle contient la repartition reelle des canaux "
        " observes pour ce perimetre, calculee par le code, jamais estimee.\n\n"
        "Ecart releve par la mesure : **a mesurer**\n"
    )
    chemin = DONNEES / "procedures" / f"{ref}.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(pseudonymiser_texte_reel(corps, auteurs), encoding="utf-8")
    return str(chemin.relative_to(DONNEES.parent))


def _objet_reel(texte: str) -> str:
    """The real declared intent: the Motivation, else the first real paragraph."""
    for titre in ("motivation", "proposed changes", "overview", "introduction"):
        trouve = re.search(rf"(?im)^\s*{titre}\s*$(.{{80,1200}})", texte)
        if trouve:
            return " ".join(trouve.group(1).split())[:1200]
    return tronquer(texte, 1200)


def _modalites(texte: str) -> str:
    sections = _sections(texte)
    retour = "Sections reellement presentes dans le document : " + (
        ", ".join(sections) if sections else "aucune des sections attendues"
    )
    return retour + f". Statut reel lu dans le document : {_statut_reel(texte) or 'non renseigne'}."


def normaliser(brut: dict[str, Any], services: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """A real page -> (documents.json entry, extraction). The procedure is written."""
    texte = _texte_reel(brut)
    ref = _reference(brut)
    cles = jira_lies(texte)
    auteurs = tuple(filter(None, [((brut.get("version") or {}).get("by") or {}).get("displayName", "")]))
    chemin = ecrire_procedure(ref, brut, texte, auteurs)
    document = {
        "id": ref,
        "type": "kip",
        "titre": tronquer(brut.get("title", ""), 200),
        "chemin": chemin,
        "pages": max(1, math.ceil(len(texte) / CARACTERES_PAR_PAGE)),
        "service": service_reel(cles, services),
        "jira_lie": cles,
        "horodatage": horodatage((brut.get("version") or {}).get("when", ""))[:10],
        "systeme": "confluence",
        "atypique": False,
        "provenance": "reel",
    }
    extraction = {
        "document_id": ref,
        "confiance": float(_confiance(texte)),
        "extracteur": "heuristique-local (Bedrock Data Automation en production, hors ligne ici)",
        "champs": {
            "kip": ref,
            "jira_lie": cles,
            "statut": _statut_reel(texte),
            "sections": _sections(texte),
            "texte_libre": pseudonymiser_texte_reel(texte[:LONGUEUR_TEXTE], auteurs),
        },
        "tableaux": tableaux((brut.get("body") or {}).get("storage", {}).get("value", "")),
        "categories_sensibles_detectees": list(detecter_categories(texte)),
    }
    return document, extraction


def collecter(maximum: int, pas: int) -> dict[str, Any]:
    """Download, extract, sanitise, write. Returns the real figures."""
    bruts = telecharger(maximum, pas)
    _, empreinte = ecrire_brut("documents.jsonl.gz", bruts)
    cles = [cle for brut in bruts for cle in jira_lies(_texte_reel(brut))]
    services = services_par_cle(cles)
    documents, extractions, auteurs = [], {}, set()
    for brut in bruts:
        document, extraction = normaliser(brut, services)
        documents.append(document)
        extractions[document["id"]] = extraction
        version = brut.get("version") or {}
        if (version.get("by") or {}).get("displayName"):
            auteurs.add(str(version["by"]["displayName"]))
        for historique in (brut.get("history") or {}).get("recent", [])[:3]:
            if (historique.get("by") or {}).get("displayName"):
                auteurs.add(str(historique["by"]["displayName"]))
    dossiers = DONNEES / "documents" / "extractions"
    dossiers.mkdir(parents=True, exist_ok=True)
    for identifiant, extraction in extractions.items():
        ecrire_json(dossiers / f"{identifiant}.json", extraction)
    propres, rapport = assainir(
        documents,
        Canal.DOCUMENTS,
        tuple(sorted(auteurs)),
        complement={"pages_reelles": sum(d["pages"] for d in documents)},
    )
    ecrire_json(DONNEES / "documents" / "documents.json", propres)
    provenance(
        "documents",
        "Confluence public ASF (espace KAFKA)",
        f"{BASE_REELLE}/content/search?cql={CQL}",
        len(bruts),
        len(propres),
        empreinte,
    )
    rapport["procedures_ecrites"] = len(list((DONNEES / "procedures").glob("*.md")))
    rapport["confiance_moyenne"] = str(
        round(sum(e["confiance"] for e in extractions.values()) / max(1, len(extractions)), 3)
    )
    return rapport


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--max", type=int, default=150)
    parseur.add_argument("--pas", type=int, default=25)
    args = parseur.parse_args(argv)
    print(json.dumps(collecter(args.max, args.pas), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
