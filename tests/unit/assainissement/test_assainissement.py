"""Lot 9 - pseudonymisation (R3, R9) and the sensitive filter (R4, R8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gisement.assainissement import (
    CATEGORIES_SENSIBLES,
    assainir,
    assainir_lot,
    detecter_categories,
    filtrer,
    groupe_pseudonyme,
    pseudonyme,
    pseudonymiser_texte,
)
from gisement.assainissement.detecteurs import DetecteurLexical
from gisement.types import Canal

CLE = "cle-de-campagne-CMP-0031"
RACINE = Path(__file__).resolve().parents[3]
SENSIBLES = RACINE / "demo" / "donnees" / "attendus" / "sensibles.json"


def test_le_pseudonyme_est_stable_et_non_reversible():
    """R3 - same key, same pseudonym; the value never contains the identifier."""
    premier = pseudonyme("marie.dupont@demo.example", CLE, "CMP-0031")
    second = pseudonyme("marie.dupont@demo.example", CLE, "CMP-0031")
    assert premier == second
    assert premier.startswith("PSD-")
    assert "marie" not in premier.lower()
    assert "dupont" not in premier.lower()
    assert pseudonyme("marie.dupont@demo.example", "autre-cle", "CMP-0031") != premier


def test_les_identifiants_d_un_texte_sont_remplaces():
    texte = "Contacter marie.dupont@demo.example ou le 06 12 34 56 78, dossier M-2291."
    propre, occurrences = pseudonymiser_texte(texte, CLE, "CMP-0031")
    categories = {o.categorie for o in occurrences}
    assert "email" in categories
    assert "telephone" in categories
    assert "matricule" in categories
    assert "marie.dupont@demo.example" not in propre
    assert "06 12 34 56 78" not in propre
    assert "M-2291" not in propre
    assert propre.count("PSD-") == len(occurrences)


def test_une_liste_de_noms_explicite_est_interceptee():
    texte = "Marie Dupont a transmis le bon de commande."
    propre, occurrences = pseudonymiser_texte(texte, CLE, "CMP-0031", noms=("Marie Dupont",))
    assert "Marie Dupont" not in propre
    assert any(o.categorie == "personne" for o in occurrences)


def test_le_groupe_pseudonyme_ne_designe_jamais_une_personne():
    """R2 - the only individual-related label is a collective one."""
    assert groupe_pseudonyme("adv", "lyon", "jour") == "ADV-JOUR"
    assert groupe_pseudonyme("comptabilite") == "COMPTA"
    assert "-" not in groupe_pseudonyme("support")


def test_les_sept_categories_sensibles_sont_detectees():
    echantillons = {
        "sante": "Suite a mon arret de travail, je reprends lundi.",
        "opinion_syndicale": "La section syndicale se reunit jeudi.",
        "opinion_politique": "Il milite pour un parti politique local.",
        "religion": "Elle s'absente pour la priere de midi.",
        "vie_sexuelle": "Son orientation sexuelle a ete mentionnee.",
        "origine_ethnie": "Origine presumee de la candidate.",
        "donnee_genetique": "Un test genetique a ete demande.",
    }
    for categorie, texte in echantillons.items():
        assert categorie in detecter_categories(texte), categorie
    assert set(echantillons) == set(CATEGORIES_SENSIBLES)


def test_un_enregistrement_sensible_est_supprime_avant_stockage():
    """EF-12 / R8 - dropped before storage, not redacted and kept."""
    brut = {
        "id": "T-1",
        "sujet": "Demande de conge",
        "description": "Suite a mon arret de travail je demande un amenagement.",
        "agent": "Marie Dupont",
        "service": "adv",
        "site": "lyon",
    }
    resultat, occurrences, categories = assainir(brut, Canal.TICKETS, cle=CLE)
    assert resultat is None
    assert "sante" in categories
    assert occurrences == ()


def test_un_enregistrement_sain_est_pseudonymise_et_conserve():
    brut = {
        "id": "T-2",
        "sujet": "Recopier la commande fournisseur dans l'ERP",
        "description": "Commande 45892 du fournisseur DEMO-FR-12, contacter marie.dupont@demo.example",
        "agent": "Marie Dupont",
        "service": "adv",
        "site": "lyon",
    }
    resultat, occurrences, categories = assainir(brut, Canal.TICKETS, cle=CLE)
    assert categories == ()
    assert resultat is not None
    assert resultat["canal"] == "tickets"
    assert resultat["groupe_pseudonyme"] == "ADV-LYON"
    assert resultat["agent"].startswith("PSD-")
    assert "marie.dupont@demo.example" not in resultat["description"]
    assert any(o.categorie == "email" for o in occurrences)


def test_le_rapport_compte_les_exclusions_et_rest_coherent():
    """ENF-05 - the report proves nothing sensitive was stored."""
    lots = [
        {"id": "1", "description": "Saisie d'une commande", "service": "adv"},
        {"id": "2", "description": "Arret de travail prolonge", "service": "adv"},
        {"id": "3", "description": "Reunion de section syndicale", "service": "comptabilite"},
        {"id": "4", "description": "Rapprochement facture bon de livraison", "service": "comptabilite"},
    ]
    propres, rapport = assainir_lot(lots, Canal.TICKETS, cle=CLE, graine=20261111)
    assert len(propres) == 2
    assert rapport.volume_entree == 4
    assert rapport.volume_sortie == 2
    assert rapport.exclus == 2
    assert rapport.est_conforme()
    assert set(rapport.categories_sensibles) == {"sante", "opinion_syndicale"}
    assert rapport.motifs_exclusion["sante"] == 1


def test_le_filtrage_occulte_explicitement():
    texte = "Arret de travail et reunion de section syndicale."
    propre, categories = filtrer(texte)
    assert "arret de travail" not in propre.lower()
    assert "[OCCULTE:sante]" in propre
    assert set(categories) == {"sante", "opinion_syndicale"}


def test_le_detecteur_lexical_trouve_les_pii_sans_aws():
    detecteur = DetecteurLexical(cle=CLE, sel="CMP-0031", noms=("Marie Dupont",))
    occurrences = detecteur.detecter("Marie Dupont - marie.dupont@demo.example - 0612345678")
    assert {o.categorie for o in occurrences} >= {"personne", "email", "telephone"}


@pytest.mark.skipif(not SENSIBLES.exists(), reason="demo dataset not generated yet (lot 3)")
def test_les_100_documents_sensibles_du_jeu_de_demo_sont_filtres():
    """R8 (blocking): 100 documents with planted categories, 100 filtered."""
    documents = json.loads(SENSIBLES.read_text(encoding="utf-8"))["documents"]
    assert len(documents) == 100
    filtres = 0
    for document in documents:
        resultat, _, categories = assainir(
            {"id": document["document_id"], "description": document["texte"], "service": "adv"},
            Canal.DOCUMENTS,
            cle=CLE,
        )
        assert resultat is None, document["document_id"]
        assert document["categorie"] in categories
        filtres += 1
    assert filtres == 100
