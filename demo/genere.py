#!/usr/bin/env python3
"""Generate the synthetic client of the demo (lot 3, annex F).

    python3 demo/genere.py --sortie demo/donnees
    python3 demo/genere.py --verifier            # prove reproducibility (ENF-08)

Everything is derived from two committed artefacts: the ground truth
(`demo/spec-processus.json`) and the motif catalogue (`catalogue/motifs/*.json`).
The same seed gives the same bytes, so the corpus can be committed and the
pipeline can run offline in CI without Amazon Transcribe or Bedrock Data
Automation (spec 26.4).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from demo import canaux_gen as cg  # noqa: E402  (path bootstrap above)
from demo import procedures  # noqa: E402
from demo.listes import CLIENT, EFFECTIFS_PAR_SERVICE, FILIGRANE, NOMS, PRENOMS  # noqa: E402
from demo.moteur import CAPACITES, Plan, planifier  # noqa: E402

VERITE = RACINE / "demo" / "spec-processus.json"
CATALOGUE = RACINE / "catalogue" / "motifs"
NOM_MANIFESTE = "manifeste.json"
ACTIVITES_ETIQUETEES = 200

#: Files that live in `demo/donnees` but are **not** written by the generator:
#: `attendus/non_attribution.json` is the 50 requests of R7, owned by lot 0.
HORS_GENERATEUR = frozenset({"attendus/non_attribution.json"})


def charger_verite() -> dict:
    """The ground truth, enriched with the canonical sentence of each motif."""
    verite = json.loads(VERITE.read_text(encoding="utf-8"))
    motifs: dict[str, dict] = {}
    for chemin in sorted(CATALOGUE.glob("*.json")):
        for motif in json.loads(chemin.read_text(encoding="utf-8")):
            motifs[motif["ref"]] = motif
    verite["catalogue"] = motifs
    return verite


def generer(sortie: Path, verite: dict) -> dict:
    """Write the whole demo corpus and return its manifest."""
    graine = int(verite["graine"])
    plan = planifier(verite, graine)
    rng = random.Random(graine)
    occurrences = list(plan.occurrences)
    sortie.mkdir(parents=True, exist_ok=True)
    tickets = cg.ecrire_tickets(occurrences, plan, rng)
    courriels = cg.ecrire_courriels(occurrences, plan, rng)
    journaux = cg.ecrire_journaux(occurrences, plan, rng)
    documents, extractions, sensibles = cg.ecrire_documents(occurrences, plan, rng)
    appels, transcriptions = cg.ecrire_appels(occurrences, plan, rng)
    _ecrire_canaux(sortie, tickets, courriels, journaux, documents, extractions, appels, transcriptions)
    _ecrire_procedures(sortie)
    manifeste = _manifeste(verite, plan, tickets, courriels, journaux, documents, appels)
    cg.ecrire_json(sortie / NOM_MANIFESTE, manifeste)
    _ecrire_attendus(sortie, verite, plan, tickets, courriels, journaux, documents, sensibles)
    return manifeste


def _ecrire_canaux(
    sortie: Path,
    tickets: list,
    courriels: list,
    journaux: list,
    documents: list,
    extractions: list,
    appels: list,
    transcriptions: list,
) -> None:
    cg.ecrire_jsonl(sortie / "tickets" / "tickets.jsonl", tickets)
    cg.ecrire_jsonl(sortie / "courriels" / "courriels.jsonl", courriels)
    cg.ecrire_csv(sortie / "journaux" / "journaux.csv", cg.entetes_journaux(), journaux)
    cg.ecrire_json(sortie / "documents" / "documents.json", documents)
    for extraction in extractions:
        cg.ecrire_json(sortie / "documents" / "extractions" / f"{extraction['document_id']}.json", extraction)
    cg.ecrire_json(sortie / "appels" / "appels.json", appels)
    for transcription in transcriptions:
        cg.ecrire_json(
            sortie / "appels" / "transcriptions" / f"{transcription['appel_id']}.json", transcription
        )


def _ecrire_procedures(sortie: Path) -> None:
    for ref in procedures.refs():
        chemin = sortie / "procedures" / f"{ref}.md"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(procedures.rendre(ref, FILIGRANE), encoding="utf-8")


def _manifeste(
    verite: dict, plan: Plan, tickets: list, courriels: list, journaux: list, documents: list, appels: list
) -> dict:
    client = verite["client"]
    return {
        "version": "1.0",
        "watermark": FILIGRANE,
        "graine": verite["graine"],
        "client": {
            **{k: v for k, v in client.items() if k != "filigrane"},
            "nom_generique": CLIENT["nom"],
            "effectif_par_service": EFFECTIFS_PAR_SERVICE,
        },
        "fenetre": client["fenetre"],
        "mois": list(plan.mois),
        "taux_horaires": client["taux_horaires"],
        "volumes": {
            "tickets": len(tickets),
            "courriels": len(courriels),
            "journaux": len(journaux),
            "documents": len(documents),
            "appels": len(appels),
            "minutes_transcrites": round(sum(a["duree_minutes"] for a in appels), 2),
            "pages_extraites": sum(d["pages"] for d in documents),
        },
        "volumes_nominaux": dict(CAPACITES),
        "activites_par_canal": dict(plan.par_canal),
        "bruit_par_canal": dict(plan.bruit_par_canal),
        "couverture": verite["couverture"],
        "listes": {"prenoms": list(PRENOMS), "noms": list(NOMS)},
        "note": (
            "Jeu entierement synthetique. Aucun donnee personnelle reelle (ENF-11). "
            "Les transcriptions d'appels et les extractions de documents sont figees dans ce "
            "depot : aucun appel a Amazon Transcribe ni a Bedrock Data Automation pendant le "
            "developpement (regle 1 du paragraphe 26.4)."
        ),
    }


def _ecrire_attendus(
    sortie: Path,
    verite: dict,
    plan: Plan,
    tickets: list,
    courriels: list,
    journaux: list,
    documents: list,
    sensibles: list,
) -> None:
    attendus = sortie / "attendus"
    mesures = _mesures_par_processus(plan)
    processus = [{**p, "occurrences_generees": mesures.get(p["id"], {})} for p in verite["processus"]]
    cg.ecrire_json(
        attendus / "processus.json",
        {
            "version": "1.0",
            "watermark": FILIGRANE,
            "graine": verite["graine"],
            "nb_processus": len(processus),
            "processus": processus,
        },
    )
    cg.ecrire_json(
        attendus / "motifs.json",
        {
            "version": "1.0",
            "watermark": FILIGRANE,
            "nb_motifs_implantes": len(mesures.get("__motifs__", {})),
            "motifs": mesures.get("__motifs__", {}),
        },
    )
    cg.ecrire_json(
        attendus / "sensibles.json",
        {
            "version": "1.0",
            "watermark": FILIGRANE,
            "nb_documents": len(sensibles),
            "documents": sensibles,
        },
    )
    _ecrire_etiquettes(attendus, verite, tickets, courriels, journaux, documents)


def _ecrire_etiquettes(
    attendus: Path, verite: dict, tickets: list, courriels: list, journaux: list, documents: list
) -> None:
    """200 hand-labelled activities (spec 27): the label comes from the gesture."""
    geste_vers_motif = {m["modele_texte"]: r for r, m in verite["catalogue"].items()}
    etiquettes = _etiqueter(tickets, courriels, journaux, documents, geste_vers_motif, verite)
    cg.ecrire_json(
        attendus / "activites_etiquetees.json",
        {
            "version": "1.0",
            "watermark": FILIGRANE,
            "nb_activites": len(etiquettes),
            "activites": etiquettes,
        },
    )


def _mesures_par_processus(plan: Plan) -> dict:
    par_processus: dict[str, dict[str, int]] = {}
    par_motif: dict[str, int] = {}
    for oc in plan.occurrences:
        compte = par_processus.setdefault(oc.processus, {})
        cle = f"mois_{oc.mois + 1:02d}"
        compte[cle] = compte.get(cle, 0) + 1
        compte["total"] = compte.get("total", 0) + 1
        par_motif[oc.motif] = par_motif.get(oc.motif, 0) + 1
    par_processus["__motifs__"] = par_motif
    return par_processus


def _etiqueter(
    tickets: list,
    courriels: list,
    journaux: list,
    documents: list,
    geste_vers_motif: dict[str, str],
    verite: dict,
) -> list[dict]:
    """200 hand-labelled activities (spec 27): the label comes from the gesture."""
    rng = random.Random(int(verite["graine"]) + 1)
    candidats: list[dict] = []
    for record in tickets:
        candidats.append(_etiquette("tickets", record["id"], record["sujet"], geste_vers_motif))
    for record in courriels:
        candidats.append(_etiquette("courriels", record["id"], record["objet"], geste_vers_motif))
    for index, ligne in enumerate(journaux, start=1):
        candidats.append(_etiquette("journaux", f"J-{index:06d}", ligne["action"], geste_vers_motif))
    for record in documents:
        candidats.append(_etiquette("documents", record["id"], record["titre"], geste_vers_motif))
    etiquettes = [c for c in candidats if c["motif_attendu"]]
    rng.shuffle(etiquettes)
    return etiquettes[:ACTIVITES_ETIQUETEES]


def _etiquette(canal: str, identifiant: str, geste: str, geste_vers_motif: dict[str, str]) -> dict:
    return {
        "canal": canal,
        "id": identifiant,
        "texte": geste,
        "motif_attendu": geste_vers_motif.get(geste, ""),
    }


def empreintes(racine: Path) -> dict[str, str]:
    """SHA-256 of every generated file, keyed by its relative path."""
    resultat = {}
    for chemin in sorted(racine.rglob("*")):
        if chemin.is_file():
            resultat[str(chemin.relative_to(racine))] = hashlib.sha256(chemin.read_bytes()).hexdigest()
    return resultat


def verifier(sortie: Path, verite: dict) -> tuple[bool, list[str]]:
    """Regenerate in a temp directory and compare, byte for byte (ENF-08)."""
    temporaire = Path(tempfile.mkdtemp(prefix="gisement-verif-"))
    try:
        generer(temporaire, verite)
        obtenu = empreintes(temporaire)
        attendu = {c: e for c, e in empreintes(sortie).items() if c not in HORS_GENERATEUR}
        ecarts = [cle for cle in sorted(set(attendu) | set(obtenu)) if attendu.get(cle) != obtenu.get(cle)]
        return not ecarts, ecarts
    finally:
        shutil.rmtree(temporaire, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--sortie", default=str(RACINE / "demo" / "donnees"))
    parseur.add_argument("--verifier", action="store_true", help="prove reproducibility")
    args = parseur.parse_args(argv)
    verite = charger_verite()
    sortie = Path(args.sortie)
    if args.verifier:
        identique, ecarts = verifier(sortie, verite)
        if not identique:
            print(f"ECHEC reproductibilite : {len(ecarts)} fichier(s) different(s)")
            for cle in ecarts[:10]:
                print(f"  - {cle}")
            return 1
        print("REPRODUCTIBLE - deux generations donnent des fichiers identiques octet pour octet")
        return 0
    manifeste = generer(sortie, verite)
    volumes = manifeste["volumes"]
    print(f"genere dans {sortie}")
    print("  " + " | ".join(f"{k}={v}" for k, v in volumes.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
