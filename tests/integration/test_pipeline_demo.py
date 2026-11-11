"""R10, R14, R16, R17 - the whole pipeline on the demo client, offline."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.pipeline import campagne_demo, executer
from gisement.types.communs import TypeAutomatisation, Vague


@pytest.fixture(scope="module")
def resultat():
    return executer(campagne_demo())


def test_les_23_processus_sont_detectes(resultat) -> None:
    """R10 - 23 processes: 22 measured, one declared (quarterly, invisible to logs)."""
    assert len(resultat.mesures) == 23
    mesurees = [m for m in resultat.mesures if m.est_mesuree]
    declarees = [m for m in resultat.mesures if m.est_invisible]
    assert len(mesurees) == 22
    assert [m.declare.id for m in declarees] == ["P-22"]


def test_les_volumes_mesures_suivent_la_verite_terrain(resultat) -> None:
    """R10 - the measured medians track the ground truth within tolerance."""
    import json
    from pathlib import Path
    from statistics import median

    verite = {
        p["id"]: p
        for p in json.loads(
            (Path(__file__).resolve().parents[2] / "demo" / "spec-processus.json").read_text(encoding="utf-8")
        )["processus"]
    }
    for mesure in resultat.mesures:
        attendu = [round(float(x)) for x in verite[mesure.declare.id]["occurrences"]["serie"]]
        obtenu = float(mesure.entree.occurrences.mediane)
        if mesure.est_invisible:
            assert mesure.entree.duree_statut.value == "inferree"
            continue
        assert obtenu == pytest.approx(median(attendu), rel=0.06), mesure.declare.id


def test_la_couverture_publiee_est_bien_62_pour_cent(resultat) -> None:
    """R14 - the coverage is published, never implicit."""
    assert resultat.couverture.globale == pytest.approx(Decimal("0.62"), abs=Decimal("0.03"))
    assert resultat.couverture.non_couvert


def test_les_six_processus_deconseilles(resultat) -> None:
    """R16 / KPI-9 - between 15 % and 30 % of the portfolio, with a reason."""
    deconseilles = {d.processus_id: d for d in resultat.portefeuille.deconseilles}
    assert len(deconseilles) == 6
    assert "P-18" in deconseilles and deconseilles["P-18"].motif.value == "obligation_legale"
    assert "P-06" in deconseilles and deconseilles["P-06"].motif.value == "instabilite"
    assert "P-20" in deconseilles and deconseilles["P-20"].motif.value == "dependance_externe"
    part = resultat.portefeuille.part_deconseilles
    assert Decimal("0.15") <= part <= Decimal("0.30")
    assert all(d.condition_reexamen for d in deconseilles.values())


def test_la_vague_1_est_faible_rapide_et_visible(resultat) -> None:
    """R17 / EF-43 - wave 1 leads, and it does not carry the biggest gain."""
    assert resultat.portefeuille.vague1_existe
    vague1 = [p for p in resultat.portefeuille.projets if p.vague == Vague.AMORCAGE]
    assert vague1
    ids = {p.processus_id for p in vague1}
    assert ids == {"P-07", "P-14"}
    assert all(p.gisement.delai_retour_mois < Decimal(6) for p in vague1)
    plus_gros = max((p.gisement.gain_annuel or Decimal(0) for p in resultat.projets), default=Decimal(0))
    assert all((p.gisement.gain_annuel or Decimal(0)) < plus_gros for p in vague1)


def test_le_cas_de_reference_de_l_annexe_A_sort_du_moteur(resultat) -> None:
    """R2 - the engine, fed by the corpus, keeps the annex A numbers for the full P-07."""
    from dataclasses import replace
    from decimal import Decimal

    mesure = next(m for m in resultat.mesures if m.declare.id == "P-07")
    complet = replace(mesure.entree, part_volume_traitee=Decimal(1), suppression_etape=False)
    from gisement.types import CoutAutomatisation

    complet = replace(
        complet,
        cout=CoutAutomatisation(
            jours=Decimal(12),
            tjm=Decimal(650),
            abonnement_mensuel=Decimal(180),
            taux_maintenance=Decimal("0.08"),
        ),
    )
    from gisement.calcul import calculer

    g = calculer(complet)
    # the corpus duration is 8.23 min rather than the ground truth's 9: the
    # factor stays above two, which is the point the report makes (KPI-4)
    assert g.ecart_naif is not None and g.ecart_naif > Decimal("2.4")
    assert g.gain_mensuel is not None and g.gain_mensuel < Decimal("900")
    assert g.delai_retour_mois is not None and g.delai_retour_mois > Decimal("10")


def test_les_projets_sont_types_et_les_E_portent_leur_conseil(resultat) -> None:
    """A E project always carries its advice; a non-E project never does."""
    assert all(p.faisabilite.type in TypeAutomatisation for p in resultat.projets)
    for projet in resultat.projets:
        est_e = projet.faisabilite.type == TypeAutomatisation.E
        assert (projet.deconseille is not None) == est_e, projet.processus_id
