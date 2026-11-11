"""Detection and filtering of the sensitive categories (R4, EF-12).

Health, union opinion, political opinion, religion, sexual life, ethnic origin
and genetic data are **dropped before storage**, not redacted and kept: a
record carrying one of them never reaches a corpus. The lexicon includes the
indirect phrasings, because a filter that only catches the obvious words is a
filter that leaks.
"""

from __future__ import annotations

import re

CATEGORIES_SENSIBLES: tuple[str, ...] = (
    "sante",
    "opinion_syndicale",
    "opinion_politique",
    "religion",
    "vie_sexuelle",
    "origine_ethnie",
    "donnee_genetique",
)

#: Category -> lexicon. Indirect wordings are included on purpose.
LEXIQUES: dict[str, tuple[str, ...]] = {
    "sante": (
        "arret de travail",
        "arret maladie",
        "conge maladie",
        "hospitalisation",
        "hospitalise",
        "maladie",
        "pathologie",
        "traitement medical",
        "medicament",
        "prescription",
        "medecin",
        "invalidite",
        "handicap",
        "rqrh",
        "sante",
        "depistage",
        "vaccin",
        "grossesse",
        "maternite",
        "psychologue",
        "burn out",
        "burnout",
        "suivi medical",
    ),
    "opinion_syndicale": (
        "syndicat",
        "syndicale",
        "syndicaliste",
        "delegue syndical",
        "section syndicale",
        "reunion de section",
        "cgt",
        "cfdt",
        "fo ",
        "cfe-cgc",
        "solidaires",
        "adhesion syndicale",
        "mandat syndical",
        "greve",
        "tract syndical",
        "cotisation syndicale",
    ),
    "opinion_politique": (
        "parti politique",
        "militant",
        "engagement politique",
        "vote",
        "election",
        "elu",
        "campagne electorale",
        "opinion politique",
        "sympathisant",
        "manifestation politique",
    ),
    "religion": (
        "religion",
        "religieux",
        "religieuse",
        "pratique religieuse",
        "priere",
        "culte",
        "ramadan",
        "carême",
        "careme",
        "sabbat",
        "eglise",
        "mosquee",
        "synagogue",
        "temple",
        "conviction religieuse",
        "fete religieuse",
        "regime confessionnel",
    ),
    "vie_sexuelle": (
        "orientation sexuelle",
        "vie sexuelle",
        "homosexualite",
        "homosexuel",
        "transgenre",
        "identite de genre",
        "pacse",
        "pacs ",
        "concubin",
        "moers",
        "moeurs",
    ),
    "origine_ethnie": (
        "origine ethnique",
        "origine presumee",
        "ethnie",
        "nationalite d origine",
        "communaute d origine",
        "ascendance",
        "couleur de peau",
        "appartenance ethnique",
    ),
    "donnee_genetique": (
        "test genetique",
        "analyse genetique",
        "adn",
        "gene ",
        "genetique",
        "biopsie",
        "sequencage",
        "predisposition genetique",
    ),
}

MOTIF_OCCULTATION = "[OCCULTE:{categorie}]"


def _motifs(categorie: str) -> tuple[re.Pattern[str], ...]:
    return tuple(
        re.compile(r"\b" + re.escape(mot).strip() + r"\b", re.IGNORECASE) for mot in LEXIQUES[categorie]
    )


def detecter_categories(texte: str) -> tuple[str, ...]:
    """Every sensitive category present in a text, in the canonical order."""
    if not texte:
        return ()
    trouvees = [
        categorie
        for categorie in CATEGORIES_SENSIBLES
        if any(motif.search(texte) for motif in _motifs(categorie))
    ]
    return tuple(trouvees)


def occulter(texte: str, categorie: str) -> str:
    """Replace the sensitive spans of one category by an explicit marker."""
    resultat = texte
    for motif in _motifs(categorie):
        resultat = motif.sub(MOTIF_OCCULTATION.format(categorie=categorie), resultat)
    return resultat


def filtrer(texte: str) -> tuple[str, tuple[str, ...]]:
    """Redacted text and the categories found. Dropping stays the caller's call."""
    categories = detecter_categories(texte)
    resultat = texte
    for categorie in categories:
        resultat = occulter(resultat, categorie)
    return resultat, categories


def texte_concatene(enregistrement: dict, champs: tuple[str, ...]) -> str:
    """Concatenate the textual fields of a record for one detection pass."""
    morceaux: list[str] = []
    for champ in champs:
        valeur = enregistrement.get(champ)
        if isinstance(valeur, str):
            morceaux.append(valeur)
        elif isinstance(valeur, (list, tuple)):
            morceaux.extend(str(v) for v in valeur if isinstance(v, str))
    return "\n".join(morceaux)
