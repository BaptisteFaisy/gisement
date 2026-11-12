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

#: Verbs of the observation vocabulary, FR and EN. Matched on the whole word.
#:
#: The English aliases were added for the REAL corpus (`reel/`, a public ASF
#: project): without them every English activity falls back to the catch-all
#: `activite` and the fingerprint cannot group anything. Three attachments are
#: deliberate and contestable, and are said here rather than hidden:
#:   - `fix` / `resolve` / `handle` -> `verifier`: in a real ticket flow the
#:     gesture is "check that the case is really closed", not a new entry;
#:   - `add` / `implement` / `update` -> `saisir`: entering data in a system;
#:   - `migrate` / `upgrade` / `convert` -> `transcrire`: moving a content from
#:     one form to another, which is what re-keying is.
VERBES: dict[str, tuple[str, ...]] = {
    "saisir": (
        "saisir",
        "saisie",
        "enregistrer",
        "saisit",
        "enter",
        "entry",
        "input",
        "record",
        "key",
        "log",
        "add",
        "added",
        "create",
        "created",
        "implement",
        "introduce",
        "set",
        "update",
        "updated",
    ),
    "recopier": (
        "recopier",
        "recopie",
        "copier",
        "saisir",
        "reporter",
        "copy",
        "copied",
        "paste",
        "retype",
        "duplicate",
        "mirror",
        "port",
        "backport",
    ),
    "transcrire": (
        "transcrire",
        "transcription",
        "ressaisir",
        "ressaisie",
        "transcribe",
        "translate",
        "convert",
        "migrate",
        "migration",
        "upgrade",
        "transform",
    ),
    "verifier": (
        "verifier",
        "verification",
        "controle",
        "controler",
        "control",
        "verify",
        "verified",
        "check",
        "checked",
        "checks",
        "validate",
        "validated",
        "validation",
        "test",
        "tested",
        "tests",
        "assert",
        "confirm",
        "fix",
        "fixed",
        "fixes",
        "resolve",
        "resolved",
        "handle",
        "handled",
        "debug",
        "flaky",
    ),
    "rapprocher": (
        "rapprocher",
        "rapprochement",
        "confronter",
        "reconcile",
        "match",
        "cross-check",
        "compare",
        "align",
        "merge",
    ),
    "relancer": (
        "relancer",
        "relance",
        "relances",
        "remind",
        "reminder",
        "follow-up",
        "followup",
        "escalate",
        "nudge",
        "ping",
        "reopen",
    ),
    "classer": (
        "classer",
        "classement",
        "indexer",
        "indexation",
        "ranger",
        "archiver",
        "archivage",
        "file",
        "filing",
        "sort",
        "organize",
        "archive",
        "label",
        "tag",
        "categorize",
        "triage",
        "rename",
        "cleanup",
        "clean",
    ),
    "rechercher": (
        "rechercher",
        "recherche",
        "chercher",
        "consulter",
        "search",
        "find",
        "lookup",
        "investigate",
        "investigation",
        "trace",
        "discover",
        "detect",
    ),
    "rediger": (
        "rediger",
        "redaction",
        "preparer",
        "preparation",
        "synthetiser",
        "write",
        "writing",
        "draft",
        "document",
        "documentation",
        "describe",
        "summarize",
        "report",
        "propose",
        "proposal",
    ),
    "envoyer": (
        "envoyer",
        "transmettre",
        "diffuser",
        "transmission",
        "diffusion",
        "send",
        "sent",
        "notify",
        "notification",
        "post",
        "publish",
        "release",
        "dispatch",
        "email",
        "announce",
    ),
    "extraire": (
        "extraire",
        "extraction",
        "exporter",
        "consolider",
        "consolidation",
        "extract",
        "export",
        "parse",
        "dump",
        "collect",
        "harvest",
        "generate",
        "build",
        "compile",
    ),
    "planifier": (
        "planifier",
        "planification",
        "organiser",
        "affecter",
        "plan",
        "schedule",
        "assign",
        "prioritize",
        "milestone",
    ),
    "signer": (
        "signer",
        "signature",
        "valider",
        "validation",
        "approuver",
        "sign",
        "approve",
        "approval",
        "review",
        "reviewed",
        "vote",
    ),
    "consulter": (
        "consulter",
        "consultation",
        "lire",
        "lecture",
        "read",
        "view",
        "consult",
        "inspect",
        "watch",
    ),
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
    """Tokens of the normalised text, without noise words and without numbers.

    A reference number or an amount is an instance detail, not part of the
    gesture: keeping it out of the signature is what lets two occurrences of
    the same gesture share a fingerprint (21.2).
    """
    return [
        m
        for m in normaliser(texte).split()
        if m not in MOTS_VIDES and len(m) > 2 and any(c.isalpha() for c in m)
    ]


def verbe(texte: str) -> str:
    """The leading verb of the activity, normalised to the observation vocabulary."""
    mots = normaliser(texte).split()
    for mot in mots:
        for canonique, alias in VERBES.items():
            if mot in alias:
                return canonique
    return MOT_VIDE


#: Every alias of the vocabulary, FR and EN (used by the real-corpus tooling).
ALIAS_VERBES = frozenset(alias for alias_verbe in VERBES.values() for alias in alias_verbe)


def objets(texte: str, maximum: int = 6) -> tuple[str, ...]:
    """The most specific words of the activity, used as the object part."""
    candidats = [m for m in mots_pertinents(texte) if m not in VERBES]
    return tuple(sorted(candidats)[:maximum])


def systemes(activite_systemes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Normalised systems touched by the activity."""
    return tuple(sorted(normaliser(s) for s in activite_systemes if s))


def signature(texte: str, activite_systemes: tuple[str, ...] = (), maximum: int = 6) -> str:
    """The deterministic signature: verb | objects | systems.

    `maximum` is the number of object words kept. Six suits a templated corpus;
    a real free-text corpus needs fewer, or every activity gets its own
    fingerprint and the model budget is gone before the first call (the real
    corpus calibrates it, and publishes the calibration).
    """
    parties = [
        verbe(texte),
        "|".join(objets(texte, maximum)),
        "|".join(systemes(activite_systemes)),
    ]
    return "::".join(parties)


def empreinte(signature: str) -> str:
    """Short, stable hash of a signature."""
    return hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]


def empreinte_complete(texte: str, activite_systemes: tuple[str, ...] = ()) -> tuple[str, str]:
    """Both the signature and its hash - what the collector stores."""
    sig = signature(texte, activite_systemes)
    return sig, empreinte(sig)
