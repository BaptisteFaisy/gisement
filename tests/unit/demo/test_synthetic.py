"""ENF-11 - the demo dataset contains no real personal data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from demo.listes import FILIGRANE, NOMS, PRENOMS

RACINE = Path(__file__).resolve().parents[3]
DONNEES = RACINE / "demo" / "donnees"
PSEUDO = re.compile(r"\b[12]\d{2}\s?\d{2}\s?\d{2,3}\s?\d{3}\s?\d{2}\b")
HORS_DEMO = re.compile(r"@(?!demo\.example|synthetique)[\w.-]+\.(fr|com|net|org)\b")


def lire_jsonl(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8") as fichier:
        return [json.loads(ligne) for ligne in fichier if ligne.strip()]


def test_le_filigrane_est_partout() -> None:
    assert FILIGRANE == "SYNTHETIQUE - DEMONSTRATION"
    manifeste = json.loads((DONNEES / "manifeste.json").read_text(encoding="utf-8"))
    assert manifeste["watermark"] == FILIGRANE
    for record in lire_jsonl(DONNEES / "tickets" / "tickets.jsonl")[:200]:
        assert record["watermark"] == FILIGRANE
    for record in lire_jsonl(DONNEES / "courriels" / "courriels.jsonl")[:200]:
        assert record["watermark"] == FILIGRANE


def test_les_noms_viennent_des_listes_fixes() -> None:
    """A generated name is a combination of the fixed lists, never a real person."""
    autorises = {f"{p} {n}" for p in PRENOMS for n in NOMS}
    for record in lire_jsonl(DONNEES / "tickets" / "tickets.jsonl"):
        assert record["agent"] in autorises, record["agent"]


def test_toutes_les_adresses_sont_dans_le_domaine_fictif() -> None:
    for record in lire_jsonl(DONNEES / "courriels" / "courriels.jsonl"):
        assert record["expediteur"].endswith(".example")
        for destinataire in record["destinataires"]:
            assert destinataire.endswith("@demo.example"), destinataire


def test_aucun_numero_de_securite_sociale_dans_le_corpus() -> None:
    """A planted French social security number would be a real identifier."""
    echantillons = [r["description"] for r in lire_jsonl(DONNEES / "tickets" / "tickets.jsonl")]
    echantillons += [r["corps"] for r in lire_jsonl(DONNEES / "courriels" / "courriels.jsonl")]
    for texte in echantillons:
        assert not PSEUDO.search(texte), texte[:80]


def test_les_documents_sensibles_sont_fictifs_et_signales() -> None:
    sensibles = json.loads((DONNEES / "attendus" / "sensibles.json").read_text(encoding="utf-8"))
    for document in sensibles["documents"]:
        assert "demo" in document["texte"].lower() or document["categorie"], document["document_id"]
        assert len(document["texte"]) < 200


def test_le_manifeste_ne_contient_aucune_donnee_personnelle() -> None:
    manifeste = json.loads((DONNEES / "manifeste.json").read_text(encoding="utf-8"))
    assert manifeste["client"]["nom"] == "Demo Distribution SAS"
    assert manifeste["client"]["effectif"] == 120
    assert not HORS_DEMO.search(json.dumps(manifeste, ensure_ascii=False))


def test_les_etiquettes_portent_sur_des_motifs_du_catalogue() -> None:
    from gisement.motifs import charger_catalogue

    catalogue = charger_catalogue()
    etiquettes = json.loads((DONNEES / "attendus" / "activites_etiquetees.json").read_text(encoding="utf-8"))[
        "activites"
    ]
    assert len(etiquettes) == 200
    for etiquette in etiquettes:
        assert catalogue.par_ref(etiquette["motif_attendu"]).ref == etiquette["motif_attendu"]
        assert etiquette["texte"] == catalogue.par_ref(etiquette["motif_attendu"]).modele_texte


@pytest.mark.parametrize("canal", ["tickets", "courriels"])
def test_aucun_identifiant_de_personne_ne_survit_a_l_assainissement(canal: str) -> None:
    """R9 - proved end to end in the collectors' tests, checked here on the raw data."""
    from gisement.assainissement import assainir_lot, construire_motif_noms
    from gisement.types import Canal

    bruts = lire_jsonl(DONNEES / canal / f"{canal}.jsonl")[:500]
    motif = construire_motif_noms(PRENOMS, NOMS)
    propres, rapport = assainir_lot(bruts, Canal(canal), cle="cle-de-test", sel="CMP-DEMO", motif_noms=motif)
    assert propres and rapport.volume_entree == 500
    for record in propres:
        texte = json.dumps(record, ensure_ascii=False)
        for prenom in PRENOMS[:10]:
            assert f"{prenom} " not in texte
        assert "@demo.example" not in texte
