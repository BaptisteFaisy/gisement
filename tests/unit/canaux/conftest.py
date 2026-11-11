"""Shared fixtures of the collector tests: the frozen demo corpus."""

from __future__ import annotations

from pathlib import Path

import pytest
from demo.listes import NOMS, PRENOMS

from gisement.assainissement import construire_motif_noms
from gisement.canaux.base import ParametresCollecte

RACINE = Path(__file__).resolve().parents[3]
DONNEES = RACINE / "demo" / "donnees"


@pytest.fixture(scope="session")
def corpus() -> Path:
    assert DONNEES.exists(), "lancez `python3 demo/genere.py` (lot 3)"
    return DONNEES


@pytest.fixture
def parametres() -> ParametresCollecte:
    """The collection parameters of the demo campaign."""
    return ParametresCollecte(
        campagne_id="CMP-0031",
        cle="cle-de-campagne-CMP-0031",
        sel="CMP-0031",
        graine=20261111,
        motif_noms=construire_motif_noms(PRENOMS, NOMS),
    )
