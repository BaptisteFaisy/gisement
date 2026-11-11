"""Deterministic matching of a fingerprint against the catalogue (21.2).

No model here: the score is a lexical overlap between the fingerprint and the
motif indices, weighted verb > objects > systems. The model is called later,
once per **group** of identical fingerprints, to label it against the catalogue
- that is what holds the budget (annex G.1).
"""

from __future__ import annotations

from decimal import Decimal

from gisement.empreinte import normaliser
from gisement.motifs.catalogue import CandidatMotif, Catalogue, MotifCatalogue

POIDS_VERBE = Decimal("0.50")
POIDS_OBJETS = Decimal("0.35")
POIDS_SYSTEMES = Decimal("0.15")

SEPARATEUR_SIGNATURE = "::"


def decouper_signature(signature: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """`verbe::objet1|objet2::sys1|sys2` -> its three parts."""
    parties = signature.split(SEPARATEUR_SIGNATURE)
    while len(parties) < 3:
        parties.append("")
    verbe = normaliser(parties[0])
    objets = tuple(o for o in (normaliser(p) for p in parties[1].split("|")) if o)
    systemes = tuple(s for s in (normaliser(p) for p in parties[2].split("|")) if s)
    return verbe, objets, systemes


def recouvrement(attendus: tuple[str, ...], observes: tuple[str, ...]) -> Decimal:
    """Share of the expected tokens found among the observed ones."""
    if not attendus:
        return Decimal(0)
    ensemble = set(observes)
    touches = sum(1 for a in attendus if a in ensemble)
    return Decimal(touches) / Decimal(len(attendus))


def recouvrement_prefixe(attendus: tuple[str, ...], observes: tuple[str, ...]) -> Decimal:
    """Partial credit: a token that merely starts with an expected one half counts."""
    if not attendus:
        return Decimal(0)
    score = Decimal(0)
    for attendu in attendus:
        if attendu in observes:
            score += 1
        elif any(o.startswith(attendu) or attendu.startswith(o) for o in observes if o):
            score += Decimal("0.5")
    return score / Decimal(len(attendus))


def score_motif(motif: MotifCatalogue, signature: str, systemes: tuple[str, ...]) -> Decimal:
    """The matching score of one motif, in [0, 1]."""
    verbe, objets, systemes_sig = decouper_signature(signature)
    systemes_tous = tuple(dict.fromkeys((*systemes_sig, *systemes)))
    part_verbe = Decimal(1) if verbe and verbe in motif.verbes else Decimal(0)
    part_objets = recouvrement_prefixe(motif.objets, objets)
    part_systemes = recouvrement(motif.systemes, systemes_tous)
    total = POIDS_VERBE * part_verbe + POIDS_OBJETS * part_objets + POIDS_SYSTEMES * part_systemes
    return total.quantize(Decimal("0.0001"))


def candidats(
    catalogue: Catalogue, signature: str, systemes: tuple[str, ...] = (), limite: int | None = None
) -> tuple[CandidatMotif, ...]:
    """Every motif scored against a signature, best first.

    Ties are broken by `ref`, so the order is deterministic and reproducible.
    """
    scores = [
        CandidatMotif(ref=m.ref, nom=m.nom, score=score_motif(m, signature, systemes))
        for m in catalogue.motifs
    ]
    scores.sort(key=lambda c: (-c.score, c.ref))
    return tuple(scores[:limite]) if limite else tuple(scores)


def meilleur_candidat(
    catalogue: Catalogue, signature: str, systemes: tuple[str, ...] = ()
) -> CandidatMotif | None:
    liste = candidats(catalogue, signature, systemes, limite=1)
    return liste[0] if liste else None
