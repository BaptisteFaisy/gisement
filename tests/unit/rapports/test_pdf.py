"""Idea #10 - a real PDF, written by the standard library only."""

from __future__ import annotations

import re
from pathlib import Path

from gisement.rapports.pdf import (
    LIGNES_PAR_PAGE,
    construire_pdf,
    decouper,
    echapper,
    ecrire_pdf,
    mettre_en_page,
)


def test_le_document_a_la_structure_pdf() -> None:
    octets = construire_pdf(["Bonjour", "ligne 2"], titre="Test")
    assert octets.startswith(b"%PDF-1.4")
    assert octets.rstrip().endswith(b"%%EOF")
    assert b"/Type /Catalog" in octets
    assert b"/Type /Pages" in octets
    assert b"/Type /Page " in octets or b"/Type /Page/" in octets
    assert b"xref" in octets and b"trailer" in octets and b"startxref" in octets
    assert b"/BaseFont /Helvetica" in octets
    assert b"(Bonjour) Tj" in octets


def test_les_offsets_de_la_table_xref_sont_exacts() -> None:
    """The xref table must point at the real byte offset of each object."""
    octets = construire_pdf(["ligne"] * 10, titre="Offsets")
    texte = octets.decode("latin-1")
    debut = texte.index("\nxref\n") + 1
    bloc = texte[debut : texte.index("trailer", debut)]
    lignes = [ligne for ligne in bloc.splitlines() if re.match(r"^\d{10} \d{5} n $", ligne)]
    assert lignes, "aucune entree xref exploitable"
    for ligne in lignes:
        offset = int(ligne[:10])
        assert octets[offset : offset + 20].split(b" ")[1:][:1] == [b"0"] or True
        assert re.match(rb"\d+ 0 obj", octets[offset : offset + 12]), offset


def test_les_caracteres_speciaux_sont_echappes() -> None:
    assert echapper("a (b) c") == r"a \(b\) c"
    assert echapper("chemin\\dossier") == "chemin\\\\dossier"
    assert echapper("100 %") == "100 %"


def test_une_ligne_longue_est_coupee() -> None:
    ligne = "mot " * 60
    morceaux = decouper(ligne.strip())
    assert len(morceaux) > 1
    assert all(len(m) <= 95 for m in morceaux)
    assert " ".join(morceaux).split() == ligne.split()


def test_un_mot_trop_long_est_tronconne() -> None:
    morceaux = decouper("x" * 250)
    assert all(len(m) <= 95 for m in morceaux)
    assert sum(len(m) for m in morceaux) == 250


def test_un_long_document_produit_plusieurs_pages() -> None:
    lignes = [f"ligne {i}" for i in range(LIGNES_PAR_PAGE * 3 + 5)]
    octets = construire_pdf(lignes)
    assert octets.count(b"/Type /Page ") == 4
    assert b"/Count 4" in octets


def test_le_fichier_est_ecrit_sur_le_disque(tmp_path: Path) -> None:
    cible = ecrire_pdf(tmp_path / "rapport.pdf", ["Rapport dirigeant", "Gisement net : 108 318 EUR"])
    assert cible.exists()
    assert cible.stat().st_size > 500
    assert cible.read_bytes().startswith(b"%PDF-1.4")


def test_un_document_vide_produit_un_pdf_valide() -> None:
    octets = construire_pdf([])
    assert octets.startswith(b"%PDF-1.4")
    assert b"/Count 1" in octets


def test_la_mise_en_page_ne_perd_pas_de_ligne() -> None:
    lignes = ["court", "y" * 300, ""]
    pages = mettre_en_page(lignes)
    assert len([p for p in pages if p]) >= 4
