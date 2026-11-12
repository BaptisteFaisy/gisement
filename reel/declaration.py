"""The declared perimeter of the REAL corpus - built from real artefacts only.

The demo perimeter (`demo/spec-processus.json`) is a ground truth written by the
generator. A real client has no ground truth, so nothing here is invented:

  - a **process** is a real Jira component of the project, kept when the real
    corpus shows enough volume in it (`--limite` keeps the biggest ones);
  - the **channels** of a process are the channels where the component really
    appears (component slug matched in the real tickets, emails, CI steps and
    design documents);
  - the **motifs and the feasibility facts** come from a real model reading the
    real design documents, recorded in `reel/modele/faits.json`; without that
    recording the builder falls back to conservative facts and says so;
  - the **written procedure** is a real KIP whose text really mentions the
    component, and `changements_douze_mois` counts the real KIPs of the trailing
    twelve months;
  - the **cost** comes from the versioned catalogue (`cout_jours_min/max`,
    `abonnement_mensuel`) and the published reference rate of
    `config/corpus_reel.json`. A figure is never produced by a model (EF-35).

    python3 -m reel.declaration --racine reel
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.motifs.catalogue import Catalogue, MotifCatalogue, charger_catalogue
from gisement.serialisation import lire_json
from reel.manifeste import CANAUX_FICHIERS, JOURNAUX, RACINE, charger_config, lire_csv, lire_jsonl

PROCEDURES = "donnees/procedures"
FAITS_MODELE = "modele/faits.json"
DECLARATION = "donnees/declaration.json"
SEUIL_VOLUME = 25
"""A real component below that many observed activities is not a process."""

FAITS_CONSERVATEURS = {
    "etape_supprimable_amont": False,
    "api_ou_flux_natif": False,
    "travail_deterministe": False,
    "interface_stable": False,
    "jugement_requis": True,
    "donnee_sensible": False,
    "obligation_legale_humaine": False,
    "dependance_externe_non_contractuelle": False,
}


def charger_corpus(racine: Path) -> dict[str, list[dict[str, Any]]]:
    """Every real record of the corpus, loaded once."""
    corpus = {
        "tickets": lire_jsonl(racine / CANAUX_FICHIERS["tickets"]),
        "courriels": lire_jsonl(racine / CANAUX_FICHIERS["courriels"]),
        "journaux": lire_csv(racine / JOURNAUX),
    }
    documents = racine / CANAUX_FICHIERS["documents"]
    brut = lire_json(documents) if documents.exists() else []
    corpus["documents"] = list(brut.get("documents", [])) if isinstance(brut, dict) else list(brut)
    return corpus


def _texte(brut: dict[str, Any]) -> str:
    champs = ("sujet", "description", "objet", "corps", "entite", "groupe", "action", "service", "titre")
    return " ".join(str(brut.get(clef, "")) for clef in champs).lower()


def volumes_reels(corpus: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    """Per real service: the count seen in each channel.

    Attribution is by the `service` field the collectors really computed - from
    a real component, a real label, or the real KIP a message cites. Matching a
    word in free text is not attribution: "core", "config" and "tools" are also
    ordinary English words, and a guessed perimeter is not a real one.
    """
    services: dict[str, dict[str, int]] = {}
    for canal, enregistrements in corpus.items():
        for brut in enregistrements:
            service = str(brut.get("service", "")).strip().lower()
            if not service:
                continue
            comptes = services.setdefault(service, {})
            comptes[canal] = comptes.get(canal, 0) + 1
    return services


def processus_reels(
    volumes: dict[str, dict[str, int]], limite: int, seuil: int = SEUIL_VOLUME
) -> list[tuple[str, dict[str, int]]]:
    """The real components with enough observed volume, biggest first."""
    retenus = [
        (service, par_canal) for service, par_canal in volumes.items() if sum(par_canal.values()) >= seuil
    ]
    retenus.sort(key=lambda item: (-sum(item[1].values()), item[0]))
    return retenus[:limite]


def procedures_reelles(racine: Path) -> list[tuple[str, str, str]]:
    """The real written procedures: (ref, real perimeter, real version date).

    The perimeter comes from the documents channel, which read it from the real
    tracker keys the KIP cites - not from a word found in the text.
    """
    chemin = racine / "donnees" / "documents" / "documents.json"
    if not chemin.exists():
        return []
    documents = lire_json(chemin)
    return [
        (str(d["id"]), str(d.get("service", "")), str(d.get("horodatage", "")))
        for d in documents
        if d.get("id")
    ]


def kip_pour(procedures: list[tuple[str, str, str]], service: str, fin: str) -> tuple[str, int]:
    """The most recent real KIP mentioning the component, and the 12-month count."""
    aujourdhui = date.today().isoformat()
    debut = f"{int(aujourdhui[:4]) - 1}-{aujourdhui[5:7]}"
    motif = re.compile(rf"\b{re.escape(service)}\b")
    correspondants = [(ref, quand) for ref, texte, quand in procedures if motif.search(texte)]
    changes = sum(1 for _, quand in correspondants if debut <= quand <= fin)
    if not correspondants:
        return "", changes
    plus_recent = max(correspondants, key=lambda item: item[1] or "0000")
    return plus_recent[0], changes


def cout_reel(motif: MotifCatalogue | None, tjm: Decimal) -> dict[str, str]:
    """The automation cost, from the versioned catalogue and the rate card."""
    if motif is None:
        return {"jours": "5", "tjm": str(tjm), "abonnement_mensuel": "0", "taux_maintenance": "0"}
    jours = ((motif.cout_jours_min + motif.cout_jours_max) / 2).quantize(Decimal("0.5"))
    return {
        "jours": str(jours),
        "tjm": str(tjm),
        "abonnement_mensuel": str(motif.abonnement_mensuel),
        "taux_maintenance": "0",
    }


def transfert_reel(motif: MotifCatalogue | None) -> list[dict[str, Any]]:
    """The transfer components, from the catalogue's published review rate."""
    if motif is None:
        return []
    return [
        {
            "nom": "revue",
            "taux": str(motif.taux_revue_defaut),
            "duree_minutes": str(motif.duree_revue_minutes),
            "forfait_heures": None,
        }
    ]


def composants_connus(racine: Path) -> frozenset[str]:
    """The real component list of the real project, downloaded once and cached."""
    from gisement.serialisation import lire_json

    cache = racine / "brut" / "composants_jira.json"
    return frozenset(lire_json(cache)) if cache.exists() else frozenset()


def nature_reelle(service: str, composants: frozenset[str]) -> str:
    """What a real perimeter key is: a component, a list, the project, a label."""
    if service in composants:
        return "composant"
    if service in {"dev", "users", "commits"}:
        return "liste"
    if service == "kafka":
        return "projet"
    if service == "sans_composant":
        return "sans_composant"
    return "etiquette"


def nom_reel(service: str, nature: str) -> tuple[str, str]:
    """A real name for a real perimeter: a component is not a mailing list."""
    if nature == "liste":
        return (
            f"Traitement des discussions de la liste de diffusion {service}",
            f"Handling the discussions of the {service} mailing list",
        )
    if nature == "projet":
        return (
            "Traitement des demandes transverses du projet",
            "Handling the project-wide requests",
        )
    if nature == "sans_composant":
        return (
            "Traitement des demandes sans composant attribue",
            "Handling the requests with no component assigned",
        )
    return (
        f"Traitement des demandes du composant {service}",
        f"Handling the requests of the {service} component",
    )


def _entree(
    index: int,
    service: str,
    par_canal: dict[str, int],
    procedures: list[tuple[str, str, str]],
    fin: str,
    faits_modele: dict[str, Any],
    catalogue: Catalogue,
    tjm: Decimal,
    composants: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """One declared process of the real perimeter."""
    modele = faits_modele.get(service, {})
    nature = nature_reelle(service, composants)
    nom, nom_en = nom_reel(service, nature)
    motifs = [str(m) for m in modele.get("motifs", []) if str(m) in catalogue.refs()]
    primaire = motifs[0] if motifs else ""
    motif = catalogue.par_ref(primaire) if primaire else None
    kip, changements = kip_pour(procedures, service, fin)
    return {
        "id": f"R-{index:02d}",
        "nom": nom,
        "nom_en": nom_en,
        "nature_perimetre": nature,
        "service": service,
        "famille_poste": str(modele.get("famille_poste", "technique")),
        "motifs": motifs,
        "canaux": [c for c in ("tickets", "courriels", "journaux", "documents") if par_canal.get(c)],
        "procedure_ref": kip,
        "changements_douze_mois": changements,
        "visibilite_dirigeant": bool(kip),
        "faits": dict(modele.get("faits") or FAITS_CONSERVATEURS),
        "origine_faits": "modele_reel" if modele.get("faits") else "conservateur",
        "raison_modele": str(modele.get("justification", "")),
        "cout": cout_reel(motif, tjm),
        "transfert": transfert_reel(motif),
        "part_volume_traitee": "1",
        "suppression_etape": bool((modele.get("faits") or {}).get("etape_supprimable_amont")),
        "volume_observe": dict(par_canal),
    }


def _document(
    retenus: list[tuple[str, dict[str, int]]],
    procedures: list[tuple[str, str, str]],
    fin: str,
    faits_modele: dict[str, Any],
    catalogue: Catalogue,
    tjm: Decimal,
    composants: frozenset[str],
    limite: int,
    seuil: int,
) -> dict[str, Any]:
    """The declaration document, in the same shape as the demo perimeter file."""
    entrees = [
        _entree(i + 1, s, v, procedures, fin, faits_modele, catalogue, tjm, composants)
        for i, (s, v) in enumerate(retenus)
    ]
    return {
        "version": "1.0",
        "corpus": "reel",
        "note": "Perimetre reel : chaque processus est un composant reel du projet, "
        "ses motifs et ses faits viennent d'un modele reel lisant les vrais documents "
        "de conception, son cout vient du catalogue versionne. Aucune verite terrain.",
        "regles": {
            "seuil_volume": seuil,
            "limite_processus": limite,
            "tjm_reference_eur": str(tjm),
            "faits_sans_modele": "conservateurs (jugement_requis=true, rien d'autre)",
        },
        "processus": [entree for entree in entrees if entree["motifs"]],
        "non_coutes": [
            {
                "id": entree["id"],
                "service": entree["service"],
                "nom": entree["nom"],
                "volume_observe": entree["volume_observe"],
                "raison": entree.get("raison_modele", "aucun motif du catalogue ne decrit ce travail"),
            }
            for entree in entrees
            if not entree["motifs"]
        ],
    }


def construire(racine: Path, limite: int | None = None) -> dict[str, Any]:
    """The declared perimeter of the real corpus, read from the real artefacts."""
    config = charger_config()
    limite = limite if limite is not None else int(config.get("limite_processus", 14))
    seuil = int(config.get("seuil_volume_processus", SEUIL_VOLUME))
    manifeste = lire_json(racine / "donnees" / "manifeste.json")
    corpus = charger_corpus(racine)
    procedures = procedures_reelles(racine)
    catalogue = charger_catalogue()
    tjm = Decimal(str(config.get("tjm_reference_eur", "650")))
    chemin_faits = racine / FAITS_MODELE
    faits_modele = {}
    if chemin_faits.exists():
        faits_modele = dict(lire_json(chemin_faits).get("processus", {}))
    composants = composants_connus(racine)
    fin = str(manifeste.get("fenetre", {}).get("fin", ""))
    retenus = processus_reels(volumes_reels(corpus), limite, seuil)
    return _document(retenus, procedures, fin, faits_modele, catalogue, tjm, composants, limite, seuil)


def ecrire(racine: Path, limite: int | None = None) -> Path:
    chemin = racine / DECLARATION
    chemin.parent.mkdir(parents=True, exist_ok=True)
    document = construire(racine, limite)
    chemin.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return chemin


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--racine", default=str(RACINE / "reel"))
    parseur.add_argument("--limite", type=int, default=None)
    args = parseur.parse_args(argv)
    chemin = ecrire(Path(args.racine), args.limite)
    document = lire_json(chemin)
    print(f"declaration ecrite : {chemin} ({len(document['processus'])} processus reels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
