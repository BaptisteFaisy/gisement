"""Shared plumbing of the real collectors (`reel/collecteurs/`).

One rule for the four channels: the raw download stays in `reel/brut/` (not
committed, never served by the portal), and only the **sanitised** artefacts are
written to `reel/donnees/` - pseudonymised at ingestion by the product's own
sanitiser (R3, ENF-02), with its real report published next to them.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from gisement.assainissement import assainir_lot
from gisement.serialisation import lire_json
from gisement.types.communs import Canal

RACINE = Path(__file__).resolve().parents[2]
REEL = RACINE / "reel"
BRUT = REEL / "brut"
DONNEES = REEL / "donnees"
CLE_PSEUDONYMISATION = "reel-kafka"
SEL_PSEUDONYMISATION = "corpus-reel-apache-kafka"
LONGUEUR_DESCRIPTION = 2000
LONGUEUR_CORPS = 2000


def ecrire_brut(nom: str, enregistrements: list[dict[str, Any]]) -> tuple[Path, str]:
    """The raw download, gzipped, with its checksum (provenance only)."""
    BRUT.mkdir(parents=True, exist_ok=True)
    chemin = BRUT / nom
    with gzip.open(chemin, "wt", encoding="utf-8") as fichier:
        for brut in enregistrements:
            fichier.write(json.dumps(brut, ensure_ascii=False) + "\n")
    return chemin, hashlib.sha256(chemin.read_bytes()).hexdigest()


def ecrire_jsonl(chemin: Path, enregistrements: list[dict[str, Any]]) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as fichier:
        for propre in enregistrements:
            fichier.write(json.dumps(propre, ensure_ascii=False, sort_keys=True) + "\n")
    return chemin


def ecrire_json(chemin: Path, donnees: Any) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return chemin


def assainir(
    bruts: list[dict[str, Any]],
    canal: Canal,
    identites_reelles: tuple[str, ...] = (),
    complement: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The product's own sanitiser, run on real records.

    `identites_reelles` are the identities the real structured fields carry
    (assignee, reporter, sender): they are handed to the sanitiser so that the
    same person is also removed from the free text, with the same pseudonym.
    """
    propres, rapport = assainir_lot(
        bruts,
        canal,
        cle=CLE_PSEUDONYMISATION,
        sel=SEL_PSEUDONYMISATION,
        noms=tuple(sorted(set(identites_reelles))),
    )
    detail = {
        "canal": canal.value,
        "volume_entree": rapport.volume_entree,
        "volume_sortie": rapport.volume_sortie,
        "exclus": rapport.exclus,
        "motifs_exclusion": rapport.motifs_exclusion,
        "pseudonymes_appliques": rapport.pseudonymes_appliques,
        "categories_sensibles": list(rapport.categories_sensibles),
        "identites_reelles_retirees": len(set(identites_reelles)),
        "cle": "HMAC-SHA256 tronque (gisement.assainissement.pseudonyme), irreversible",
        **(complement or {}),
    }
    ecrire_json(DONNEES / "assainissement" / f"{canal.value}.json", detail)
    return propres, detail


def horodatage(valeur: Any) -> str:
    """A real timestamp -> the frozen schema's local ISO form (no offset)."""
    texte = str(valeur or "").strip()
    if not texte:
        return ""
    for format_ in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(texte, format_).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return texte[:19]


def tronquer(texte: Any, limite: int = LONGUEUR_DESCRIPTION) -> str:
    """A real description is unbounded; the corpus keeps its first characters."""
    propre = " ".join(str(texte or "").split())
    return propre if len(propre) <= limite else propre[: limite - 1] + "…"


def provenance(canal: str, source: str, url: str, brut: int, publie: int, sha256: str) -> None:
    """Append the real provenance of one channel to `reel/brut/provenance.json`."""
    chemin = BRUT / "provenance.json"
    existant = lire_json(chemin) if chemin.exists() else {}
    existant[canal] = {
        "systeme": source,
        "url": url,
        "telecharge_le": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "enregistrements_bruts": brut,
        "enregistrements_publies": publie,
        "brut_gz_sha256": sha256,
    }
    ecrire_json(chemin, existant)
