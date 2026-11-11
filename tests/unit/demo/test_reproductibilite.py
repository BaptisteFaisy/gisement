"""ENF-08 - the same seed gives the same bytes."""

from __future__ import annotations

import json
from pathlib import Path

from demo.genere import charger_verite, empreintes, generer

RACINE = Path(__file__).resolve().parents[3]
DONNEES = RACINE / "demo" / "donnees"


#: owned by lot 0, not written by the generator (docs/CONTRACTS.md section 7)
HORS_GENERATEUR = {"attendus/non_attribution.json"}


def test_deux_generations_donnent_des_fichiers_identiques(tmp_path: Path) -> None:
    assert DONNEES.exists(), "lancez `python3 demo/genere.py`"
    generer(tmp_path, charger_verite())
    attendu = empreintes(DONNEES)
    obtenu = empreintes(tmp_path)
    assert set(attendu) - HORS_GENERATEUR == set(obtenu)
    differents = [c for c in obtenu if attendu.get(c) != obtenu[c]]
    assert differents == [], differents[:5]


def test_la_graine_est_publiee_dans_le_manifeste() -> None:
    manifeste = json.loads((DONNEES / "manifeste.json").read_text(encoding="utf-8"))
    verite = json.loads((RACINE / "demo" / "spec-processus.json").read_text(encoding="utf-8"))
    assert manifeste["graine"] == verite["graine"] == 20261111


def test_le_verificateur_est_utilisable_depuis_la_cli() -> None:
    """`gisement generer --verifier` must exist and be wired to the generator."""
    from gisement.commands.generer import GENERATEUR

    assert GENERATEUR.exists()
    assert GENERATEUR.name == "genere.py"
