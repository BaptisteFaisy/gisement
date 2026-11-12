"""Idea #10 - the commercial proposal: the document that gets signed."""

from __future__ import annotations

from pathlib import Path

import pytest

from gisement.commands.proposition import construire, main
from gisement.pipeline import campagne_demo, executer


@pytest.fixture(scope="module")
def resultat():
    return executer(campagne_demo())


def test_la_proposition_porte_les_chiffres_mesures(resultat) -> None:
    texte = "\n".join(construire(resultat, "Demo Distribution SAS"))
    assert "Demo Distribution SAS" in texte
    assert "62 %" in texte  # the coverage is published
    assert "108318.12 EUR" in texte  # the net annual deposit
    assert "Vague 1" in texte and "Vague 3" in texte
    assert "P-07" in texte and "1102.50 EUR/mois" in texte


def test_la_proposition_dit_ce_qu_il_ne_faut_pas_automatiser(resultat) -> None:
    texte = "\n".join(construire(resultat, "Demo Distribution SAS"))
    assert "ne PAS automatiser" in texte
    assert "obligation legale" in texte or "volume" in texte
    assert "reexamen" in texte.lower()
    assert "Dire non est ce qui rend le oui credible" in texte


def test_la_proposition_publie_le_cout_reel_de_la_cartographie(resultat) -> None:
    """KPI-8 - the cost is measured, and it is shown to the client."""
    texte = "\n".join(construire(resultat, "Demo Distribution SAS"))
    assert "Cout reel de la cartographie" in texte
    assert "USD" in texte


def test_l_offre_et_l_engagement_sont_explicites(resultat) -> None:
    texte = "\n".join(construire(resultat, "Demo Distribution SAS"))
    assert "Notre offre" in texte
    assert "Premier projet propose : P-07" in texte
    assert "40 %" in texte  # the commitment on prediction accuracy


def test_le_pdf_est_ecrit(tmp_path: Path) -> None:
    cible = tmp_path / "proposition.pdf"
    assert main(["--pdf", str(cible), "--client", "Client Test"]) == 0
    octets = cible.read_bytes()
    assert octets.startswith(b"%PDF-1.4")
    assert octets.rstrip().endswith(b"%%EOF")
    assert len(octets) > 2000
    assert b"Client Test" in octets


def test_le_texte_est_ecrit(tmp_path: Path) -> None:
    cible = tmp_path / "proposition.md"
    assert main(["--sortie", str(cible)]) == 0
    assert "Vague 1" in cible.read_text(encoding="utf-8")
