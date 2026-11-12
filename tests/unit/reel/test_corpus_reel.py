"""The REAL corpus: the same figures the site and the API publish.

The artefacts of `reel/donnees/` are committed, so these tests read the real
numbers without a network and without a credit. If the site, the API and these
tests ever disagreed, the site could show a figure the API would not produce -
which is exactly what the product forbids (the same handlers, the same code).
"""

from __future__ import annotations

import json
from pathlib import Path

from reel.corpus import executer_reel, modele_reel
from reel.declaration import construire as construire_declaration
from reel.manifeste import RACINE

from gisement.motifs.catalogue import charger_catalogue

REEL = Path(RACINE) / "reel"
DONNEES = REEL / "donnees"


def _lire(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def test_le_manifeste_reel_decrit_les_fichiers_reels() -> None:
    manifeste = _lire(DONNEES / "manifeste.json")
    tickets = (DONNEES / "tickets" / "tickets.jsonl").read_text(encoding="utf-8").splitlines()
    courriels = (DONNEES / "courriels" / "courriels.jsonl").read_text(encoding="utf-8").splitlines()
    assert manifeste["activites_par_canal"]["tickets"] == len([t for t in tickets if t.strip()])
    assert manifeste["activites_par_canal"]["courriels"] == len([c for c in courriels if c.strip()])
    assert manifeste["fenetre"]["debut"] <= manifeste["fenetre"]["fin"]
    assert manifeste["couverture"]["volume_travail_estime_heures"]
    assert "regle" in manifeste["couverture"]


def test_le_manifeste_reel_publie_les_sources_et_les_licences() -> None:
    manifeste = _lire(DONNEES / "manifeste.json")
    sources = {source["canal"] for source in manifeste["sources"]}
    assert {"tickets", "courriels", "documents"} <= sources
    for source in manifeste["sources"]:
        assert source["url"].startswith("https://")
        assert source["licence"]
    absents = {a["canal"] for a in manifeste["absents"]}
    assert "appels" in absents, "un canal absent se declare, il ne se simule pas"


def test_la_declaration_reel_n_a_pas_de_verite_terrain() -> None:
    document = construire_declaration(REEL)
    catalogue = charger_catalogue()
    assert document["processus"], "le perimetre reel declare des processus"
    for processus in document["processus"]:
        assert processus["motifs"], "un processus declare porte au moins un motif"
        for motif in processus["motifs"]:
            assert motif in catalogue.refs()
        for interdit in ("type_attendu", "piege", "type_arbre_attendu", "vague_attendue"):
            assert interdit not in processus, "une verite terrain ne se declare pas"


def test_le_perimetre_reel_vient_des_faits_d_un_modele_reel() -> None:
    faits = _lire(REEL / "modele" / "faits.json")
    assert faits["modele"], "les faits du perimetre disent quel modele les a produits"
    assert faits["processus"], "chaque service declare porte ses faits"
    document = construire_declaration(REEL)
    for processus in document["processus"]:
        entree = faits["processus"][processus["service"]]
        assert processus["motifs"] == entree["motifs"]
        assert processus["origine_faits"] == "modele_reel"


def test_la_mesure_reelle_reproduit_les_chiffres_publies() -> None:
    resultat = executer_reel(REEL, modele=modele_reel(REEL))
    assert resultat.activites > 3000, "le corpus reel a bien ete mesure"
    assert len(resultat.mesures) == 12
    mesures = sum(1 for mesure in resultat.mesures if mesure.est_mesuree)
    assert mesures >= 6, "des processus reels sont mesures, pas seulement declares"
    assert resultat.revues, "ce qui n'est pas reconnu va en revue humaine"


def test_le_rejeu_du_modele_reel_n_invente_rien() -> None:
    reponses = _lire(REEL / "modele" / "reponses.json")
    for cle, reponse in reponses.items():
        if cle == "_meta":
            continue
        assert reponse["motif_ref"]
        assert 0 < float(reponse["confiance"]) <= 1
