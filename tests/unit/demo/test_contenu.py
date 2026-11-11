"""Lot 3 - the generated corpus is what the spec promises (annex F)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
DONNEES = RACINE / "demo" / "donnees"
MANIFESTE = DONNEES / "manifeste.json"


def charger(nom: str):
    return json.loads((DONNEES / nom).read_text(encoding="utf-8"))


def lire_jsonl(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8") as fichier:
        return [json.loads(ligne) for ligne in fichier if ligne.strip()]


@pytest.fixture(scope="module")
def manifeste() -> dict:
    assert MANIFESTE.exists(), "lancez `python3 demo/genere.py` (lot 3)"
    return json.loads(MANIFESTE.read_text(encoding="utf-8"))


def test_les_volumes_nominaux_de_l_annexe_f(manifeste: dict) -> None:
    volumes = manifeste["volumes"]
    assert volumes["tickets"] == 4800
    assert volumes["courriels"] == 2000
    assert volumes["journaux"] == 12400
    assert volumes["documents"] == 200
    assert volumes["pages_extraites"] == 200, "annexe G.3 : 200 pages de Data Automation"
    assert volumes["minutes_transcrites"] == pytest.approx(360.0, abs=1.0), "annexe G.3 : 6 h"


def test_les_fichiers_bruts_ont_le_volume_annonce(manifeste: dict) -> None:
    assert len(lire_jsonl(DONNEES / "tickets" / "tickets.jsonl")) == manifeste["volumes"]["tickets"]
    assert len(lire_jsonl(DONNEES / "courriels" / "courriels.jsonl")) == manifeste["volumes"]["courriels"]
    with (DONNEES / "journaux" / "journaux.csv").open(encoding="utf-8") as fichier:
        assert sum(1 for _ in csv.DictReader(fichier)) == manifeste["volumes"]["journaux"]
    assert len(charger("documents/documents.json")) == manifeste["volumes"]["documents"]


def test_les_schemas_des_cinq_canaux() -> None:
    ticket = lire_jsonl(DONNEES / "tickets" / "tickets.jsonl")[0]
    assert {
        "id",
        "horodatage",
        "service",
        "site",
        "agent",
        "sujet",
        "description",
        "systeme",
        "duree_traitement_minutes",
        "statut",
        "allers_retours",
        "groupe",
    } <= set(ticket)
    courriel = lire_jsonl(DONNEES / "courriels" / "courriels.jsonl")[0]
    assert {"id", "horodatage", "expediteur", "destinataires", "objet", "corps", "service", "stratum"} <= set(
        courriel
    )
    document = charger("documents/documents.json")[0]
    assert {"id", "type", "titre", "chemin", "pages", "service", "horodatage"} <= set(document)
    appel = charger("appels/appels.json")[0]
    assert {"id", "duree_minutes", "horodatage", "service", "consentement", "type", "transcription"} <= set(
        appel
    )
    with (DONNEES / "journaux" / "journaux.csv").open(encoding="utf-8") as fichier:
        ligne = next(csv.DictReader(fichier))
    assert {"horodatage", "service", "action", "entite", "systeme", "groupe", "duree_secondes"} <= set(ligne)


def test_chaque_document_a_son_extraction_figee() -> None:
    """26.4 - no Bedrock Data Automation call during development."""
    documents = charger("documents/documents.json")
    for document in documents:
        extraction = DONNEES / "documents" / "extractions" / f"{document['id']}.json"
        assert extraction.exists(), document["id"]
        brut = json.loads(extraction.read_text(encoding="utf-8"))
        assert brut["document_id"] == document["id"]
        assert "champs" in brut and "tableaux" in brut


def test_chaque_appel_a_sa_transcription_figee_et_consentie() -> None:
    """10.4 - only recordings that already exist and were consented to."""
    appels = charger("appels/appels.json")
    assert appels
    for appel in appels:
        assert appel["consentement"] is True
        chemin = DONNEES / appel["transcription"]
        assert chemin.exists(), appel["id"]
        brut = json.loads(chemin.read_text(encoding="utf-8"))
        assert brut["appel_id"] == appel["id"]
        assert brut["piis_occultees"] >= 0
        for segment in brut["segments"]:
            assert segment["locuteur"].startswith("LOC-"), "jamais un nom de personne"


def test_les_100_documents_sensibles_sont_plantes() -> None:
    """R8 - a hundred documents with planted sensitive categories."""
    sensibles = charger("attendus/sensibles.json")
    assert sensibles["nb_documents"] == 100
    categories = {d["categorie"] for d in sensibles["documents"]}
    assert len(categories) == 7
    identifiants = {d["document_id"] for d in sensibles["documents"]}
    assert len(identifiants) == 100


def test_les_volumes_par_processus_reproduisent_la_verite_terrain() -> None:
    """The generator serves the ground truth, it does not invent volumes."""
    verite = {
        p["id"]: [round(float(x)) for x in p["occurrences"]["serie"]]
        for p in json.loads((RACINE / "demo" / "spec-processus.json").read_text(encoding="utf-8"))[
            "processus"
        ]
    }
    genere = charger("attendus/processus.json")
    assert genere["nb_processus"] == 23
    for processus in genere["processus"]:
        attendu = verite[processus["id"]]
        obtenu = [processus["occurrences_generees"].get(f"mois_{i + 1:02d}", 0) for i in range(6)]
        assert obtenu == attendu, processus["id"]


def test_les_trois_pieges_sont_dans_les_donnees() -> None:
    """Annex F.3: seasonal peak, divergent procedure, high judgement."""
    genere = {p["id"]: p for p in charger("attendus/processus.json")["processus"]}
    pic = genere["P-16"]["occurrences_generees"]
    mois = [pic[f"mois_{i + 1:02d}"] for i in range(6)]
    assert max(mois) >= 300 and sorted(mois)[2] <= 45, mois
    assert genere["P-07"]["ecart_procedure"] is True
    assert float(genere["P-02"]["part_atypique"]) > 0.5


def test_p07_passe_principalement_par_courriel() -> None:
    """Annex D: the divergent procedure is visible in the data.

    The 78 % of annex D is the share of supplier orders that arrive by email -
    a business fact published by the procedure gap. The mailbox is only read as
    a stratified *sample* (6.3), so the share observed in the sample is lower,
    and that is exactly why the coverage is published next to it.
    """
    verite = json.loads((RACINE / "demo" / "spec-processus.json").read_text(encoding="utf-8"))
    processus = next(p for p in verite["processus"] if p["id"] == "P-07")
    assert processus["part_pratique_divergente"] == "0.78"
    courriels = lire_jsonl(DONNEES / "courriels" / "courriels.jsonl")
    geste = "Recopier la commande fournisseur du courriel dans l'ERP"
    par_courriel = sum(1 for c in courriels if c["objet"] == geste)
    assert par_courriel > 1000
    total = sum(round(float(x)) for x in processus["occurrences"]["serie"])
    assert par_courriel / total > 0.55


def test_huit_procedures_ecrites_dont_une_divergente() -> None:
    fichiers = sorted((DONNEES / "procedures").glob("PROC-*.md"))
    assert len(fichiers) == 8
    proc04 = (DONNEES / "procedures" / "PROC-04.md").read_text(encoding="utf-8")
    assert "portail EDI" in proc04
    assert "Écart relevé par la mesure : **oui**" in proc04
    assert "78 %" in proc04


def test_le_manifeste_publie_le_denominateur_de_couverture() -> None:
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    couverture = manifeste["couverture"]
    assert float(couverture["volume_travail_estime_heures"]) > 0
    assert couverture["non_couvert"], "la liste de ce qui n'est pas couvert est obligatoire (10.3)"
    assert manifeste["graine"] == 20261111
    assert manifeste["mois"] == ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
