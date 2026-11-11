"""D-09 / R5 - the gateway artefact is generated from the enforced registry."""

from __future__ import annotations

from gisement.politique import exporter_politique_agentcore, regles_par_outil, verifier_artefact
from gisement.politique.regles import REGLES
from gisement.types import Regle
from gisement.types.conformite import OUTIL_CORPUS, OUTIL_EXPORT, OUTIL_MESURE


def test_l_artefact_contient_toutes_les_regles(ctx) -> None:
    document = exporter_politique_agentcore(ctx)
    identifiants = {r["id"] for r in document["regles"]}
    for regle in Regle:
        assert regle.value in identifiants, regle.value
    assert verifier_artefact(document) == ()


def test_l_artefact_est_en_refus_par_defaut_et_avant_l_outil(ctx) -> None:
    document = exporter_politique_agentcore(ctx)
    assert document["defaut"] == "deny"
    assert document["evaluation"] == "avant_execution_de_l_outil"
    assert document["seuil_agregation"] == 5


def test_le_seuil_de_l_artefact_suit_le_contexte(ctx) -> None:
    from dataclasses import replace

    assert exporter_politique_agentcore(replace(ctx, seuil=10))["seuil_agregation"] == 10
    assert exporter_politique_agentcore(replace(ctx, seuil=2))["seuil_agregation"] == 5


def test_chaque_regle_porte_sa_condition_et_son_message(ctx) -> None:
    for entree in exporter_politique_agentcore(ctx)["regles"]:
        assert entree["condition"] and entree["message"] and entree["journaliser"] is True
        assert entree["action"] == "deny"
        assert entree["outils"]


def test_les_regles_sont_filtrees_par_outil(ctx) -> None:
    document = exporter_politique_agentcore(ctx)
    assert "regle_corpus_brut" in regles_par_outil(document, OUTIL_CORPUS)
    assert "regle_corpus_brut" not in regles_par_outil(document, OUTIL_MESURE)
    assert "regle_export" in regles_par_outil(document, OUTIL_EXPORT)
    assert "regle_k5" in regles_par_outil(document, OUTIL_MESURE)


def test_une_seule_source_de_verite(ctx) -> None:
    """The artefact and the engine read the same registry: they cannot drift."""
    document = exporter_politique_agentcore(ctx)
    assert len(document["regles"]) == len(REGLES)
    assert {r["id"] for r in document["regles"]} == {spec.regle.value for spec in REGLES}


def test_les_parametres_sont_auditable(ctx) -> None:
    from dataclasses import replace
    from decimal import Decimal

    document = exporter_politique_agentcore(replace(ctx, budget_restant=Decimal("7.50"), seuil=5))
    par_regle = {r["id"]: r for r in document["regles"]}
    assert par_regle["regle_k5"]["parametres"]["seuil_agregation"] == 5
    assert par_regle["regle_budget"]["parametres"]["budget_restant_usd"] == "7.50"
    assert par_regle["regle_quota_requetes"]["parametres"]["quota_requetes"] == 200
    assert "tickets" in par_regle["regle_canal_non_autorise"]["parametres"]["canaux_autorises"]
