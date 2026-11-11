"""Lot 19 - the Amazon Quick asset bundle is published from the measured campaign."""

from __future__ import annotations

import pytest

from gisement.commands.assets import (
    spec_tableau_de_bord,
    table_portefeuille,
    table_tendances,
    table_vagues,
)
from gisement.pipeline import campagne_demo, executer


@pytest.fixture(scope="module")
def resultat():
    return executer(campagne_demo())


def test_le_portefeuille_comporte_les_23_processus(resultat) -> None:
    """All 23 processes, including the 6 advised-against (category E)."""
    table = table_portefeuille(resultat)
    assert len(table) == 23
    assert all({"processus_id", "type", "gain_mensuel"} <= set(ligne) for ligne in table)
    deconseilles = [ligne for ligne in table if ligne["deconseille"]]
    assert len(deconseilles) == 6


def test_les_vagues_sont_publiees(resultat) -> None:
    vagues = table_vagues(resultat)
    noms = [v["vague"] for v in vagues]
    assert "vague_1" in noms
    vague1 = next(v for v in vagues if v["vague"] == "vague_1")
    assert vague1["nb_projets"] >= 1
    assert "P-07" in vague1["processus"]


def test_les_tendances_portent_la_saisonnalite(resultat) -> None:
    tendances = table_tendances(resultat)
    p16 = next(t for t in tendances if t["processus_id"] == "P-16")
    assert max(int(x) for x in p16["occurrences_par_mois"]) > 200
    assert int(p16["mediane"]) < 60


def test_la_spec_du_tableau_de_bord_est_coherente() -> None:
    spec = spec_tableau_de_bord()
    assert spec["nom"]
    assert {d["dataset"] for d in spec["visuels"]} <= set(spec["datasets"])
    assert any(v["id"] == "sequence" for v in spec["visuels"])
    assert any(v["id"] == "deconseilles" for v in spec["visuels"])
