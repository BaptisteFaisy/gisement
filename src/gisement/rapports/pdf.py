"""A minimal PDF 1.4 writer, standard library only (idea #10).

The deliverable a sponsor actually reads is two printed pages, not a web page.
Adding a PDF dependency to a project whose whole pitch is "runs offline in a
5-minute CI" would be a bad trade, so the writer is here: header, objects, an
xref table with byte-exact offsets, trailer. Helvetica, one page of 54 lines,
text wrapped on word boundaries.

It is deliberately small: no images, no tables, no compression. A report is
text, and text is all that is needed to hand a CFO the sequence and the first
project.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path

MARGE_GAUCHE = 50
MARGE_HAUTE = 790
INTERLIGNE = 13
LIGNES_PAR_PAGE = 54
LARGEUR_CARACTERES = 95
HAUTEUR_PAGE = 842
LARGEUR_PAGE = 595

EN_TETE = b"%PDF-1.4\n"
# a binary comment, as the spec recommends: it tells tools the file is binary
COMMENTAIRE_BINAIRE = b"%\xe2\xe3\xcf\xd3\n"


def echapper(texte: str) -> str:
    """Escape a literal string, and drop what Latin-1 cannot encode."""
    return (
        texte.replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def decouper(ligne: str, largeur: int = LARGEUR_CARACTERES) -> list[str]:
    """Wrap one line on word boundaries; a too-long word is cut."""
    if len(ligne) <= largeur:
        return [ligne]
    morceaux: list[str] = []
    reste = ligne
    while len(reste) > largeur:
        coupe = reste.rfind(" ", 0, largeur)
        if coupe <= 0:
            coupe = largeur
        morceaux.append(reste[:coupe].rstrip())
        reste = reste[coupe:].lstrip()
    if reste:
        morceaux.append(reste)
    return morceaux


def mettre_en_page(lignes: Sequence[str], largeur: int = LARGEUR_CARACTERES) -> list[str]:
    """Wrap every line so that a page holds a known number of them."""
    page: list[str] = []
    for ligne in lignes:
        page.extend(decouper(ligne.rstrip(), largeur))
    return page


def contenu_page(lignes: Sequence[str]) -> bytes:
    """The content stream of one page: one text-showing operation per line."""
    morceaux = ["BT", "/F1 10 Tf", f"{INTERLIGNE} TL", f"1 0 0 1 {MARGE_GAUCHE} {MARGE_HAUTE} Tm"]
    for ligne in lignes:
        morceaux.append(f"({echapper(ligne)}) Tj T*")
    morceaux.append("ET")
    return ("\n".join(morceaux) + "\n").encode("latin-1", "replace")


def _objet(numero: int, corps: bytes) -> bytes:
    return f"{numero} 0 obj\n".encode("latin-1") + corps + b"\nendobj\n"


def ecrire_pdf(chemin: str | Path, lignes: Sequence[str], titre: str = "Gisement") -> Path:
    """Write the PDF and return its path."""
    cible = Path(chemin)
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_bytes(construire_pdf(lignes, titre))
    return cible


def construire_pdf(lignes: Sequence[str], titre: str = "Gisement") -> bytes:
    """A complete, valid PDF document."""
    pages = _paginer(mettre_en_page(lignes))
    tampon = io.BytesIO()
    tampon.write(EN_TETE)
    tampon.write(COMMENTAIRE_BINAIRE)
    offsets: dict[int, int] = {}
    nb_pages = len(pages)
    premiere_page = 5
    _ecrire_objets_fixes(tampon, offsets, nb_pages, premiere_page, titre)
    for index, page in enumerate(pages):
        numero_page = premiere_page + 2 * index
        numero_contenu = numero_page + 1
        _ecrire_page(tampon, offsets, numero_page, numero_contenu, page)
    _ecrire_xref(tampon, offsets, titre, nb_pages)
    return tampon.getvalue()


def _paginer(lignes: Sequence[str]) -> list[list[str]]:
    if not lignes:
        return [[]]
    return [list(lignes[i : i + LIGNES_PAR_PAGE]) for i in range(0, len(lignes), LIGNES_PAR_PAGE)]


def _ecrire_objets_fixes(
    tampon: io.BytesIO, offsets: dict[int, int], nb_pages: int, premiere_page: int, titre: str
) -> None:
    enfants = " ".join(f"{premiere_page + 2 * i} 0 R" for i in range(nb_pages))
    fixes = {
        1: "<< /Type /Catalog /Pages 2 0 R >>".encode("latin-1"),
        2: f"<< /Type /Pages /Kids [{enfants}] /Count {nb_pages} >>".encode("latin-1"),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    }
    for numero in sorted(fixes):
        offsets[numero] = tampon.tell()
        tampon.write(_objet(numero, fixes[numero]))
    del titre  # the title is carried by the Info dictionary, written with the xref


def _ecrire_page(
    tampon: io.BytesIO,
    offsets: dict[int, int],
    numero: int,
    numero_contenu: int,
    lignes: Sequence[str],
) -> None:
    contenu = contenu_page(lignes)
    offsets[numero] = tampon.tell()
    tampon.write(
        _objet(
            numero,
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGEUR_PAGE} {HAUTEUR_PAGE}] "
                "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {numero_contenu} 0 R >>"
            ).encode("latin-1"),
        )
    )
    offsets[numero_contenu] = tampon.tell()
    tampon.write(
        _objet(
            numero_contenu,
            f"<< /Length {len(contenu)} >>\nstream\n".encode("latin-1") + contenu + b"endstream",
        )
    )


def _ecrire_xref(tampon: io.BytesIO, offsets: dict[int, int], titre: str, nb_pages: int) -> None:
    numero_info = max(offsets) + 1
    offsets[numero_info] = tampon.tell()
    tampon.write(
        _objet(
            numero_info,
            f"<< /Title ({echapper(titre)}) /Producer (Gisement) /Creator (Gisement) >>".encode("latin-1"),
        )
    )
    debut_xref = tampon.tell()
    total = numero_info + 1
    entrees = [f"xref\n0 {total}\n", "0000000000 65535 f \n"]
    for numero in range(1, total):
        entrees.append(f"{offsets.get(numero, 0):010d} 00000 n \n")
    tampon.write("".join(entrees).encode("latin-1"))
    tampon.write(
        f"trailer\n<< /Size {total} /Root 1 0 R /Info {numero_info} 0 R >>\n"
        f"startxref\n{debut_xref}\n%%EOF\n".encode("latin-1")
    )
    del nb_pages
