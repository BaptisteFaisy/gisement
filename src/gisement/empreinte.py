"""Deterministic fingerprint of an activity (chapter 21.2, first pass).

The fingerprint groups the activities that look alike *without calling a
model*. On the demo corpus it turns about 7 000 items into about 60 groups,
which is what holds the budget: the model is called once per group, not once
per activity (annex G.1 - a factor of about 80).

The signature is built from three observable facts:
    - the verb of the activity,
    - the objects it touches,
    - the systems it crosses.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

MOT_VIDE = "activite"

#: Verbs of the observation vocabulary, FR and EN. Matched on the word start.
VERBES: dict[str, tuple[str, ...]] = {
    "saisir": ("saisir", "saisie", "enregistrer", "saisit"),
    "recopier": ("recopier", "recopie", "copier", "saisir", "reporter"),
    "transcrire": ("transcrire", "transcription", "ressaisir", "ressaisie"),
    "verifier": ("verifier", "verification", "controle", "controler", "control"),
    "rapprocher": ("rapprocher", "rapprochement", "confronter"),
    "relancer": ("relancer", "relance", "relances"),
    "classer": ("classer", "classement", "indexer", "indexation", "ranger", "archiver", "archivage"),
    "rechercher": ("rechercher", "recherche", "chercher", "consulter"),
    "rediger": ("rediger", "redaction", "preparer", "preparation", "synthetiser"),
    "envoyer": ("envoyer", "transmettre", "diffuser", "transmission", "diffusion"),
    "extraire": ("extraire", "extraction", "exporter", "consolider", "consolidation"),
    "planifier": ("planifier", "planification", "organiser", "affecter"),
    "signer": ("signer", "signature", "valider", "validation", "approuver"),
    "consulter": ("consulter", "consultation", "lire", "lecture"),
}

#: Words that carry no signal for the fingerprint.
MOTS_VIDES = frozenset(
    [
        "de",
        "du",
        "des",
        "la",
        "le",
        "les",
        "un",
        "une",
        "et",
        "ou",
        "de",
        "la",
        "des",
        "a",
        "au",
        "aux",
        "en",
        "pour",
        "par",
        "sur",
        "avec",
        "sans",
        "dans",
        "ce",
        "cet",
        "cette",
        "ces",
        "que",
        "qui",
        "quoi",
        "dont",
        "ne",
        "pas",
        "plus",
        "tres",
        "est",
        "sont",
        "etre",
        "avoir",
        "fait",
        "faire",
        "the",
        "of",
        "to",
        "for",
        "from",
        "with",
        "and",
        "or",
        "in",
        "on",
        "at",
        "by",
        "is",
        "are",
        "be",
        "been",
        "this",
        "that",
        "these",
        "those",
        "it",
    ]
)

SEPARATEURS = re.compile(r"[^a-z0-9]+")


def normaliser(texte: str) -> str:
    """Lower case, without accent, without punctuation, spaces collapsed."""
    decompose = unicodedata.normalize("NFKD", texte.lower())
    sans_accent = "".join(c for c in decompose if not unicodedata.combining(c))
    return " ".join(SEPARATEURS.sub(" ", sans_accent).split())


def mots_pertinents(texte: str) -> list[str]:
    """Tokens of the normalised text, without the noise words."""
    return [m for m in normaliser(texte).split() if m not in MOTS_VIDES and len(m) > 2]


def verbe(texte: str) -> str:
    """The leading verb of the activity, normalised to the observation vocabulary."""
    mots = normaliser(texte).split()
    for mot in mots:
        for canonique, alias in VERBES.items():
            if mot in alias:
                return canonique
    return MOT_VIDE


def objets(texte: str, maximum: int = 6) -> tuple[str, ...]:
    """The most specific words of the activity, used as the object part."""
    candidats = [m for m in mots_pertinents(texte) if m not in VERBES]
    return tuple(sorted(candidats)[:maximum])


def systemes(activite_systemes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Normalised systems touched by the activity."""
    return tuple(sorted(normaliser(s) for s in activite_systemes if s))


def signature(texte: str, activite_systemes: tuple[str, ...] = ()) -> str:
    """The deterministic signature: verb | objects | systems."""
    parties = [verbe(texte), "|".join(objets(texte)), "|".join(systemes(activite_systemes))]
    return "::".join(parties)


def empreinte(signature: str) -> str:
    """Short, stable hash of a signature."""
    return hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]


def empreinte_complete(texte: str, activite_systemes: tuple[str, ...] = ()) -> tuple[str, str]:
    """Both the signature and its hash - what the collector stores."""
    sig = signature(texte, activite_systemes)
    return sig, empreinte(sig)
