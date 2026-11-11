"""The motif catalogue, as data (annex B, lot 2).

Forty automation motifs in eight families. Adding one is a data change: drop a
JSON object in `catalogue/motifs/<famille>.json`, the loader picks it up and the
classifier can match it (R25). No code, no release.

A motif carries what the economic engine needs as a default (typical unit
duration, spread, review rate, atypical share) and what the classifier needs to
recognise it (fingerprint indices). `modele_texte` is the canonical sentence of
the gesture: the demo generator writes activities with it, so classification is
measured against a stable reference.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from gisement.types.communs import Canal, Repartition, StatutDuree, TypeAutomatisation, decimal

RACINE_CATALOGUE = Path(__file__).resolve().parents[3] / "catalogue"

#: annex B - eight families, forty motifs.
COMPTES_PAR_FAMILLE: dict[str, int] = {
    "ressaisie": 7,
    "rapprochement": 6,
    "verification": 6,
    "relance": 5,
    "classement": 4,
    "reporting": 5,
    "coordination": 4,
    "recherche": 3,
}

TYPES_VALIDES = frozenset(t.value for t in TypeAutomatisation)
CANAUX_VALIDES = frozenset(c.value for c in Canal)


def nombre(brut: dict, champ: str) -> Decimal:
    """A numeric field, or zero when the data is broken.

    The loader never crashes on a malformed catalogue: `nombres_valides` and
    `valider_catalogue` report the problem, which is what a partner adding
    motifs for their own clients needs.
    """
    try:
        return decimal(brut.get(champ, "0"))
    except (ArithmeticError, ValueError, TypeError):
        return Decimal(0)


def enumeration[T](classe: type[T], valeur: object, defaut: T) -> T:
    """An enumeration value, or the default when the data is not a known one."""
    try:
        return classe(valeur)
    except ValueError:
        return defaut


@dataclass(frozen=True)
class MotifCatalogue:
    """One motif of the catalogue."""

    ref: str
    famille: str
    nom: str
    nom_en: str
    description: str
    canaux: tuple[Canal, ...]
    verbes: tuple[str, ...]
    objets: tuple[str, ...]
    systemes: tuple[str, ...]
    modele_texte: str
    duree_unitaire_typique_minutes: Decimal
    duree_statut_defaut: StatutDuree
    repartition_defaut: Repartition
    taux_revue_defaut: Decimal
    duree_revue_minutes: Decimal
    part_atypique_defaut: Decimal
    types_envisageables: tuple[TypeAutomatisation, ...]
    cout_jours_min: Decimal
    cout_jours_max: Decimal
    abonnement_mensuel: Decimal


@dataclass(frozen=True)
class CandidatMotif:
    """A catalogue motif and how well it matches a fingerprint."""

    ref: str
    nom: str
    score: Decimal


def motif_depuis_dict(brut: dict) -> MotifCatalogue:
    """Build one motif from its JSON form, tolerating broken values."""
    indices = brut.get("indices", {}) or {}
    return MotifCatalogue(
        ref=str(brut.get("ref", "")),
        famille=str(brut.get("famille", "")),
        nom=str(brut.get("nom", "")),
        nom_en=str(brut.get("nom_en", brut.get("nom", ""))),
        description=str(brut.get("description", "")),
        canaux=tuple(Canal(c) for c in brut.get("canaux", ()) if c in CANAUX_VALIDES),
        verbes=tuple(indices.get("verbes", ())),
        objets=tuple(indices.get("objets", ())),
        systemes=tuple(indices.get("systemes", ())),
        modele_texte=str(brut.get("modele_texte", "")),
        duree_unitaire_typique_minutes=nombre(brut, "duree_unitaire_typique_minutes"),
        duree_statut_defaut=enumeration(StatutDuree, brut.get("duree_statut_defaut"), StatutDuree.INFERREE),
        repartition_defaut=enumeration(Repartition, brut.get("repartition_defaut"), Repartition.DIFFUSE),
        taux_revue_defaut=nombre(brut, "taux_revue_defaut"),
        duree_revue_minutes=nombre(brut, "duree_revue_minutes"),
        part_atypique_defaut=nombre(brut, "part_atypique_defaut"),
        types_envisageables=tuple(
            TypeAutomatisation(t) for t in brut.get("types_envisageables", ()) if t in TYPES_VALIDES
        ),
        cout_jours_min=nombre(brut, "cout_jours_min"),
        cout_jours_max=nombre(brut, "cout_jours_max"),
        abonnement_mensuel=nombre(brut, "abonnement_mensuel"),
    )


def charger_catalogue(racine: str | Path | None = None) -> Catalogue:
    """Load every motif file of a catalogue root (default: `catalogue/`)."""
    racine_motifs = Path(racine) if racine else RACINE_CATALOGUE
    if racine_motifs.name != "motifs":
        racine_motifs = racine_motifs / "motifs"
    motifs: list[MotifCatalogue] = []
    for chemin in sorted(racine_motifs.glob("*.json")):
        for brut in json.loads(chemin.read_text(encoding="utf-8")):
            motifs.append(motif_depuis_dict(brut))
    motifs.sort(key=lambda m: m.ref)
    return Catalogue(motifs=tuple(motifs))


@dataclass(frozen=True)
class Catalogue:
    """The loaded catalogue."""

    motifs: tuple[MotifCatalogue, ...] = ()

    def __len__(self) -> int:
        return len(self.motifs)

    def refs(self) -> tuple[str, ...]:
        return tuple(m.ref for m in self.motifs)

    def par_ref(self, ref: str) -> MotifCatalogue:
        for motif in self.motifs:
            if motif.ref == ref:
                return motif
        raise KeyError(f"motif inconnu du catalogue : {ref}")

    def famille(self, nom: str) -> tuple[MotifCatalogue, ...]:
        return tuple(m for m in self.motifs if m.famille == nom)

    def candidats(self, signature: str, systemes: tuple[str, ...] = ()) -> tuple[CandidatMotif, ...]:
        from gisement.motifs.recherche import candidats

        return candidats(self, signature, systemes)
