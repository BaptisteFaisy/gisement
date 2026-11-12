"""Idea #6 - the overstatement factor is a distribution, not a single anecdote."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from eval.backtest import SECTEURS, charger_cas, facteurs, mediane, verifier_attendus

RACINE = Path(__file__).resolve().parents[2]
RETOURS = RACINE / "demo" / "retours"


def test_les_trois_secteurs_sont_presents() -> None:
    for secteur in SECTEURS:
        chemin = RETOURS / f"{secteur}.json"
        assert chemin.exists(), secteur
        document = json.loads(chemin.read_text(encoding="utf-8"))
        assert document["secteur"] == secteur
        assert document["nb_cas"] == len(document["cas"]) >= 5
        assert "synthetiques" in document["source"]


def test_chaque_cas_a_le_format_d_une_entree_du_moteur() -> None:
    requis = {
        "id",
        "occurrences",
        "duree_unitaire_minutes",
        "repartition",
        "part_atypique",
        "transfert",
        "cout",
        "faits",
        "attendu",
    }
    for secteur, spec in charger_cas():
        assert requis <= set(spec), f"{secteur}/{spec.get('id')}"


def test_chaque_cas_reproduit_son_attendu_au_centime() -> None:
    assert verifier_attendus(charger_cas()) == []


def test_au_moins_un_cas_par_secteur_est_une_action_de_type_a() -> None:
    """14.2 - removing the step is tested in every sector, not only in the demo."""
    for secteur in SECTEURS:
        document = json.loads((RETOURS / f"{secteur}.json").read_text(encoding="utf-8"))
        assert any(c["suppression_etape"] for c in document["cas"]), secteur


def test_au_moins_un_cas_par_secteur_est_deconseille() -> None:
    """16.1 - every sector has a process that must not be automated."""
    for secteur in SECTEURS:
        document = json.loads((RETOURS / f"{secteur}.json").read_text(encoding="utf-8"))
        deconseilles = [
            c
            for c in document["cas"]
            if Decimal(c["attendu"]["gain_annuel"]) < Decimal(3000)
            or (
                c["attendu"]["delai_retour_mois"] and Decimal(c["attendu"]["delai_retour_mois"]) > Decimal(36)
            )
        ]
        assert deconseilles, secteur


def test_le_facteur_median_global_depasse_un_et_demi() -> None:
    """The thesis of the project, measured on 37 cases instead of one."""
    par_secteur = facteurs(charger_cas())
    toutes = [v for valeurs in par_secteur.values() for v in valeurs]
    assert len(toutes) >= 40
    assert len(par_secteur) == 4
    assert mediane(toutes) > Decimal("1.5")
    assert max(toutes) > Decimal(4)


def test_le_harnais_est_executable_et_rend_zero() -> None:
    resultat = subprocess.run(
        [sys.executable, str(RACINE / "eval" / "backtest.py")],
        capture_output=True,
        text=True,
        check=False,
        cwd=RACINE,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "La these tient" in resultat.stdout
