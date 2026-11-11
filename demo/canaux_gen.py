"""Writers of the five channels (lot 3). One function per channel, one schema
per channel: the exact shapes frozen in `docs/CONTRACTS.md` section 5.
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from demo.listes import CATEGORIES_SENSIBLES, DOCUMENTS, FILIGRANE, PLANTES_SENSIBLES, courriel, personne
from demo.moteur import MINUTES_APPELS, Occurrence, Plan, details, instant, libelle_bruit, systeme_libelle


def ecrire_tickets(occurrences: list[Occurrence], plan: Plan, rng: random.Random) -> list[dict]:
    records: list[dict] = []
    tickets_utiles = [o for o in occurrences if o.canal == "tickets"]
    for index, oc in enumerate(tickets_utiles, start=1):
        det = details(rng, oc.atypique)
        records.append(
            {
                "id": f"T-{index:06d}",
                "horodatage": instant(plan.mois[oc.mois], "diffuse", rng).isoformat(),
                "service": oc.service,
                "site": "lyon" if rng.random() < 0.7 else "villeurbanne",
                "agent": personne(rng),
                "sujet": oc.geste,
                "description": _description(oc.geste, det),
                "systeme": oc.systemes[0],
                "duree_traitement_minutes": round(oc.jours * rng.uniform(0.7, 1.3), 1),
                "statut": "clos",
                "allers_retours": rng.randint(0, 3),
                "groupe": _groupe(oc.service, rng),
                "watermark": FILIGRANE,
            }
        )
    for _ in range(plan.bruit_par_canal["tickets"]):
        records.append(
            {
                "id": f"T-{len(records) + 1:06d}",
                "horodatage": instant(
                    plan.mois[rng.randrange(len(plan.mois))], "interruptive", rng
                ).isoformat(),
                "service": rng.choice(["adv", "support", "comptabilite", "approvisionnements"]),
                "site": "lyon",
                "agent": personne(rng),
                "sujet": libelle_bruit("tickets", rng),
                "description": "demande ponctuelle hors perimetre de la mesure",
                "systeme": "itsm",
                "duree_traitement_minutes": round(rng.uniform(1, 12), 1),
                "statut": "clos",
                "allers_retours": rng.randint(0, 2),
                "groupe": _groupe("support", rng),
                "watermark": FILIGRANE,
            }
        )
    return records


def _groupe(service: str, rng: random.Random) -> str:
    from demo.listes import groupe

    return groupe(service, rng)


def ecrire_courriels(occurrences: list[Occurrence], plan: Plan, rng: random.Random) -> list[dict]:
    records: list[dict] = []
    for oc in [o for o in occurrences if o.canal == "courriels"]:
        det = details(rng, oc.atypique)
        expediteur = f"contact@{det['societe'].lower()}.{FILIGRANE.split()[0].lower()}.example"
        destinataire = courriel(personne(rng))
        records.append(
            {
                "id": f"M-{len(records) + 1:06d}",
                "horodatage": instant(plan.mois[oc.mois], "semi_regroupee", rng).isoformat(),
                "expediteur": expediteur,
                "destinataires": [destinataire],
                "objet": oc.geste,
                "corps": _corps(oc.geste, det),
                "service": oc.service,
                "stratum": f"{oc.service}_mois_{oc.mois + 1:02d}",
                "piece_jointe": "bon_commande.pdf" if rng.random() < 0.6 else None,
                "watermark": FILIGRANE,
            }
        )
    for _ in range(plan.bruit_par_canal["courriels"]):
        records.append(
            {
                "id": f"M-{len(records) + 1:06d}",
                "horodatage": instant(plan.mois[rng.randrange(len(plan.mois))], "diffuse", rng).isoformat(),
                "expediteur": f"direction@{FILIGRANE.split()[0].lower()}.example",
                "destinataires": [courriel(personne(rng))],
                "objet": libelle_bruit("courriels", rng),
                "corps": "message hors du perimetre de la mesure, conserve comme bruit de fond",
                "service": rng.choice(["adv", "support"]),
                "stratum": "bruit",
                "piece_jointe": None,
                "watermark": FILIGRANE,
            }
        )
    return records


def ecrire_journaux(occurrences: list[Occurrence], plan: Plan, rng: random.Random) -> list[dict]:
    lignes: list[dict] = []
    for oc in [o for o in occurrences if o.canal == "journaux"]:
        det = details(rng, oc.atypique)
        lignes.append(
            {
                "horodatage": instant(plan.mois[oc.mois], "semi_regroupee", rng).isoformat(),
                "service": oc.service,
                "action": oc.geste,
                "entite": f"{det['societe']} {det['produit']} {det['montant']}",
                "systeme": systeme_libelle(oc.systemes[0]),
                "groupe": _groupe(oc.service, rng),
                "duree_secondes": max(1, int(oc.jours * 60 * rng.uniform(0.8, 1.2))),
                "watermark": FILIGRANE,
            }
        )
    for _ in range(plan.bruit_par_canal["journaux"]):
        lignes.append(
            {
                "horodatage": instant(plan.mois[rng.randrange(len(plan.mois))], "diffuse", rng).isoformat(),
                "service": rng.choice(["adv", "support", "comptabilite"]),
                "action": "Connexion et navigation",
                "entite": "session",
                "systeme": "ERP",
                "groupe": _groupe("adv", rng),
                "duree_secondes": rng.randint(5, 120),
                "watermark": FILIGRANE,
            }
        )
    return lignes


def entetes_journaux() -> list[str]:
    return ["horodatage", "service", "action", "entite", "systeme", "groupe", "duree_secondes", "watermark"]


def ecrire_documents(
    occurrences: list[Occurrence], plan: Plan, rng: random.Random
) -> tuple[list[dict], list[dict], list[dict]]:
    """Documents, frozen extractions, and the planted sensitive ones (R8)."""
    documents: list[dict] = []
    extractions: list[dict] = []
    sensibles: list[dict] = []
    occurrences_docs = [o for o in occurrences if o.canal == "documents"]
    total = len(occurrences_docs) + plan.bruit_par_canal["documents"]
    for index in range(total):
        oc = occurrences_docs[index] if index < len(occurrences_docs) else None
        identifiant = f"D-{index + 1:06d}"
        type_doc, titre_type = DOCUMENTS[index % len(DOCUMENTS)]
        texte = _texte_document(index % 2 == 1, rng, titre_type)
        det = details(rng, bool(oc and oc.atypique))
        documents.append(_document(identifiant, type_doc, titre_type, oc, plan, rng))
        extractions.append(_extraction(identifiant, det, texte, rng))
        if index % 2 == 1:
            sensibles.append(
                {"document_id": identifiant, "categorie": _categorie(texte), "texte": texte, "type": type_doc}
            )
    return documents, extractions, sensibles


def _document(
    identifiant: str, type_doc: str, titre_type: str, oc: Occurrence | None, plan: Plan, rng: random.Random
) -> dict:
    return {
        "id": identifiant,
        "type": type_doc,
        "titre": (oc.geste if oc else titre_type),
        "chemin": f"documents/{identifiant}.pdf",
        "pages": 1,  # annex G.3: 200 documents = 200 pages of Data Automation
        "service": (oc.service if oc else "comptabilite"),
        "horodatage": _date_document(oc, plan, rng),
        "watermark": FILIGRANE,
    }


def _extraction(identifiant: str, det: dict, texte: str, rng: random.Random) -> dict:
    """A frozen Bedrock Data Automation output (rule 1 of 26.4)."""
    return {
        "document_id": identifiant,
        "confiance": round(rng.uniform(0.82, 0.99), 2),
        "champs": {
            "numero": f"{rng.randint(10000, 99999)}",
            "tiers": det["societe"],
            "montant_ht": det["montant"],
            "texte_libre": texte,
        },
        "tableaux": [
            {
                "nom": "lignes",
                "colonnes": ["ref", "qte", "pu"],
                "lignes": [[det["produit"], rng.randint(1, 40), f"{rng.uniform(10, 900):.2f}"]],
            }
        ],
        "categories_sensibles_detectees": [],
        "watermark": FILIGRANE,
    }


def _description(geste: str, det: dict) -> str:
    return f"{geste} - {det['societe']} {det['produit']} {det['montant']} EUR ({det['mention']})"


def _corps(geste: str, det: dict) -> str:
    return (
        f"Bonjour, {geste.lower()} pour la reference {det['produit']} ({det['montant']} EUR). "
        f"Contact : {det['contact']}. {det['mention']}."
    )


def _date_document(oc: Occurrence | None, plan: Plan, rng: random.Random) -> str:
    mois = oc.mois if oc else rng.randrange(len(plan.mois))
    return instant(plan.mois[mois], "regroupee", rng).date().isoformat()


def _extraction(identifiant: str, det: dict, texte: str, rng: random.Random) -> dict:
    """A frozen Bedrock Data Automation output (rule 1 of 26.4)."""
    return {
        "document_id": identifiant,
        "confiance": round(rng.uniform(0.82, 0.99), 2),
        "champs": {
            "numero": f"{rng.randint(10000, 99999)}",
            "tiers": det["societe"],
            "montant_ht": det["montant"],
            "texte_libre": texte,
        },
        "tableaux": [
            {
                "nom": "lignes",
                "colonnes": ["ref", "qte", "pu"],
                "lignes": [[det["produit"], rng.randint(1, 40), f"{rng.uniform(10, 900):.2f}"]],
            }
        ],
        "categories_sensibles_detectees": [],
        "watermark": FILIGRANE,
    }


def _categorie(texte: str) -> str:
    for categorie, formules in PLANTES_SENSIBLES.items():
        if any(f in texte for f in formules):
            return categorie
    return CATEGORIES_SENSIBLES[0]


def _texte_document(sensible: bool, rng: random.Random, titre: str) -> str:
    if not sensible:
        return f"{titre} - piece comptable standard, aucune donnee sensible"
    categorie = CATEGORIES_SENSIBLES[rng.randrange(len(CATEGORIES_SENSIBLES))]
    return f"{titre} - {rng.choice(PLANTES_SENSIBLES[categorie])}"


def ecrire_appels(
    occurrences: list[Occurrence], plan: Plan, rng: random.Random
) -> tuple[list[dict], list[dict]]:
    """Calls and their frozen transcripts: six hours in total (annex F.2)."""
    par_appel: dict[str, list[Occurrence]] = defaultdict(list)
    for oc in [o for o in occurrences if o.canal == "appels"]:
        par_appel[f"{oc.processus}-{oc.mois:02d}"].append(oc)
    cles = sorted(par_appel)
    total_segments = sum(len(par_appel[c]) for c in cles) or 1
    secondes_par_segment = (MINUTES_APPELS * 60) / total_segments
    appels: list[dict] = []
    transcriptions: list[dict] = []
    for index, cle in enumerate(cles, start=1):
        segments = par_appel[cle]
        premier = segments[0]
        appel_id = f"A-{index:04d}"
        duree = round(len(segments) * secondes_par_segment / 60, 2)
        appels.append(
            {
                "id": appel_id,
                "duree_minutes": duree,
                "horodatage": instant(plan.mois[premier.mois], "regroupee", rng).isoformat(),
                "service": premier.service,
                "consentement": True,
                "type": "reunion" if len(segments) > 6 else "appel",
                "transcription": f"appels/transcriptions/{appel_id}.json",
                "watermark": FILIGRANE,
            }
        )
        transcriptions.append(_transcription(appel_id, segments, duree, secondes_par_segment, rng))
    return appels, transcriptions


def _transcription(
    appel_id: str, segments: list[Occurrence], duree: float, secondes: float, rng: random.Random
) -> dict:
    texte_segments = []
    curseur = 0.0
    for position, oc in enumerate(segments):
        debut = curseur
        fin = min(duree * 60, curseur + secondes)
        curseur = fin
        det = details(rng, oc.atypique)
        texte_segments.append(
            {
                "debut": round(debut, 2),
                "fin": round(fin, 2),
                "locuteur": f"LOC-{position % 5 + 1}",
                "texte": f"{oc.geste} ; reference {det['produit']} ; {det['mention']}",
            }
        )
    return {
        "appel_id": appel_id,
        "langue": "fr-FR",
        "duree_minutes": duree,
        "piis_occultees": rng.randint(1, 9),
        "segments": texte_segments,
        "watermark": FILIGRANE,
    }


def ecrire_jsonl(chemin: Path, records: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as fichier:
        for record in records:
            fichier.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def ecrire_json(chemin: Path, contenu: object) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def ecrire_csv(chemin: Path, entetes: list[str], lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.DictWriter(fichier, fieldnames=entetes)
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
