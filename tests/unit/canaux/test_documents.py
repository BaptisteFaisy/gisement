"""Lot 6 - the documents collector: frozen extractions, sensitive filter (R8)."""

from __future__ import annotations

from pathlib import Path

from gisement.canaux import documents
from gisement.canaux.documents.data_automation import ExtractionFigee
from gisement.types import Canal, StatutDuree


def test_les_documents_sont_joins_a_leur_extraction(corpus: Path) -> None:
    source = documents.source_fichiers(corpus)
    assert documents.mesurer_volume(source) == 200
    assert source.pages_extraites == 0


def test_les_cent_documents_sensibles_sont_supprimes_avant_stockage(corpus: Path, parametres) -> None:
    """R8 (blocking) - a document carrying a sensitive category never reaches a corpus."""
    activites, rapport = documents.collecter(documents.source_fichiers(corpus), parametres)
    assert rapport["volume_entree"] == 200
    assert rapport["volume_sortie"] == 100
    assert rapport["exclus"] == 100
    assert set(rapport["categories_sensibles"]) == {
        "sante",
        "opinion_syndicale",
        "opinion_politique",
        "religion",
        "vie_sexuelle",
        "origine_ethnie",
        "donnee_genetique",
    }
    assert all(a.canal == Canal.DOCUMENTS for a in activites)
    assert all(a.duree_statut == StatutDuree.INFERREE for a in activites)


def test_le_nombre_de_pages_est_compte_pour_le_cout(corpus: Path, parametres) -> None:
    """Annex G.3 - 200 pages of Data Automation is what the mapping is priced on."""
    _, rapport = documents.collecter(documents.source_fichiers(corpus), parametres)
    assert rapport["pages_extraites"] == 200


def test_l_extraction_figee_est_lue_sur_le_dossier(tmp_path: Path) -> None:
    (tmp_path / "documents" / "extractions").mkdir(parents=True)
    (tmp_path / "documents" / "extractions" / "D-1.json").write_text(
        '{"document_id": "D-1", "confiance": 0.9, "champs": {"texte_libre": "Bonjour"},'
        ' "tableaux": [], "categories_sensibles_detectees": []}',
        encoding="utf-8",
    )
    extracteur = ExtractionFigee(tmp_path)
    assert extracteur.extraire({"id": "D-1"})["confiance"] == 0.9
    assert extracteur.pages({"id": "D-1", "pages": 3}) == 3
    assert extracteur.extraire({"id": "D-9"})["champs"] == {}


def test_l_adaptateur_reel_ne_normalise_que_ses_answers() -> None:
    from gisement.canaux.documents.data_automation import DataAutomation

    normalise = DataAutomation.normaliser(
        "D-1",
        {
            "confidence": 0.88,
            "fields": {"numero": "42"},
            "tables": [{"nom": "lignes"}],
        },
    )
    assert normalise["document_id"] == "D-1"
    assert normalise["champs"]["numero"] == "42"
