"""Shared plumbing of the five collectors (lot 0 - integration).

Five collectors, one behaviour: read a source, sanitise every record, build
activities carrying a deterministic fingerprint, and never let a person
identifier through. The channel-specific packages stay thin: they only say
which fields of their records hold the text, the timestamp and the duration.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from gisement.assainissement import assainir_lot
from gisement.empreinte import signature
from gisement.types.communs import Canal, StatutDuree, decimal
from gisement.types.mesure import Activite


@dataclass(frozen=True)
class ParametresCollecte:
    """What a collector needs besides its source."""

    campagne_id: str
    cle: str
    sel: str = ""
    graine: int = 0
    corpus_id: str = ""
    noms: tuple[str, ...] = ()
    """Explicit list of person names to catch (published by the demo manifest)."""

    motif_noms: object | None = None
    """Precompiled "Firstname Lastname" pattern, built from the manifest lists."""


@runtime_checkable
class Source(Protocol):
    """A channel source. `SourceFichiers*` for the demo, AWS adapters in prod."""

    canal: Canal

    def lire(self) -> Iterator[dict[str, Any]]:
        """Raw records, in a stable order."""
        ...

    def volume(self) -> int:
        """Number of raw records, before any filtering."""
        ...


class SourceJsonl:
    """One JSON object per line."""

    def __init__(self, chemin: str | Path, canal: Canal) -> None:
        self.chemin = Path(chemin)
        self.canal = canal

    def lire(self) -> Iterator[dict[str, Any]]:
        if not self.chemin.exists():
            return iter(())
        with self.chemin.open(encoding="utf-8") as fichier:
            for ligne in fichier:
                ligne = ligne.strip()
                if ligne:
                    yield json.loads(ligne)

    def volume(self) -> int:
        return sum(1 for _ in self.lire())


class SourceJson:
    """A JSON array, or an object whose `cle` entry is the array."""

    def __init__(self, chemin: str | Path, canal: Canal, cle: str | None = None) -> None:
        self.chemin = Path(chemin)
        self.canal = canal
        self.cle = cle

    def lire(self) -> Iterator[dict[str, Any]]:
        if not self.chemin.exists():
            return iter(())
        brut = json.loads(self.chemin.read_text(encoding="utf-8"))
        if isinstance(brut, dict) and self.cle:
            brut = brut.get(self.cle, [])
        return iter(x for x in brut if isinstance(x, dict))

    def volume(self) -> int:
        return sum(1 for _ in self.lire())


class SourceCsv:
    """A CSV file with a header line."""

    def __init__(self, chemin: str | Path, canal: Canal) -> None:
        self.chemin = Path(chemin)
        self.canal = canal

    def lire(self) -> Iterator[dict[str, Any]]:
        if not self.chemin.exists():
            return iter(())
        with self.chemin.open(encoding="utf-8", newline="") as fichier:
            for ligne in csv.DictReader(fichier):
                yield dict(ligne)

    def volume(self) -> int:
        return sum(1 for _ in self.lire())


def horodatage(valeur: Any) -> datetime:
    """Parse an ISO timestamp, tolerating a missing value."""
    if isinstance(valeur, datetime):
        return valeur
    if not valeur:
        return datetime.fromordinal(1)
    try:
        return datetime.fromisoformat(str(valeur))
    except ValueError:
        return datetime.fromordinal(1)


def duree_minutes(valeur: Any) -> Decimal | None:
    """A duration in minutes, or None when the record carries none."""
    if valeur in (None, ""):
        return None
    try:
        return decimal(valeur)
    except (ArithmeticError, ValueError):
        return None


def systemes_de(enregistrement: dict[str, Any]) -> tuple[str, ...]:
    """Systems touched by a record, whatever the channel calls them."""
    candidats = (
        enregistrement.get("systeme"),
        enregistrement.get("systemes"),
        enregistrement.get("application"),
    )
    resultat: list[str] = []
    for candidat in candidats:
        if isinstance(candidat, str) and candidat:
            resultat.extend(p.strip() for p in candidat.split(",") if p.strip())
        elif isinstance(candidat, (list, tuple)):
            resultat.extend(str(c) for c in candidat if c)
    return tuple(dict.fromkeys(resultat))


def construire_activites(
    source: Source,
    parametres: ParametresCollecte,
    *,
    champs_signature: tuple[str, ...],
    champs_texte: tuple[str, ...] = (),
    champ_duree: str | None = None,
    statut_duree: StatutDuree = StatutDuree.INFERREE,
    facteur_duree: Decimal = Decimal(1),
) -> tuple[tuple[Activite, ...], dict[str, Any]]:
    """Sanitise a source and turn it into activities.

    `champs_signature` are the canonical fields the fingerprint is built on:
    the gesture, without its instance details. `champs_texte` is the free text
    kept on the activity for display - it is pseudonymised, but it never feeds
    the signature, or two occurrences of the same gesture would not group.

    Returns the activities and the sanitisation report as a dict, so the
    collector can publish both (EF-11, EF-16).
    """
    bruts = list(source.lire())
    propres, rapport = assainir_lot(
        bruts,
        source.canal,
        cle=parametres.cle,
        sel=parametres.sel,
        graine=parametres.graine,
        noms=parametres.noms,
        motif_noms=parametres.motif_noms,
    )
    activites = tuple(
        _activite(
            index,
            record,
            source.canal,
            parametres,
            champs_signature,
            champs_texte or champs_signature,
            champ_duree,
            statut_duree,
            facteur_duree,
        )
        for index, record in enumerate(propres)
    )
    return activites, rapport_dict(source.canal, rapport)


def rapport_dict(canal: Canal, rapport: object) -> dict[str, Any]:
    """The sanitisation report as a publishable dict (EF-16, ENF-05)."""
    return {
        "canal": canal.value,
        "volume_entree": rapport.volume_entree,
        "volume_sortie": rapport.volume_sortie,
        "exclus": rapport.exclus,
        "categories_sensibles": list(rapport.categories_sensibles),
        "pseudonymes_appliques": rapport.pseudonymes_appliques,
    }


def _activite(
    index: int,
    record: dict[str, Any],
    canal: Canal,
    parametres: ParametresCollecte,
    champs_signature: tuple[str, ...],
    champs_texte: tuple[str, ...],
    champ_duree: str | None,
    statut_duree: StatutDuree,
    facteur_duree: Decimal,
) -> Activite:
    geste = " ".join(str(record[c]) for c in champs_signature if record.get(c))
    texte = " ".join(str(record[c]) for c in champs_texte if record.get(c))
    identifiant = str(record.get("id", f"{canal.value}-{index:06d}"))
    duree = duree_minutes(record.get(champ_duree)) if champ_duree else None
    if duree is not None:
        duree = duree * facteur_duree
    return Activite(
        id=f"{canal.value}:{identifiant}",
        corpus_id=parametres.corpus_id or f"corpus-{parametres.campagne_id}-{canal.value}",
        canal=canal,
        signature=signature(geste, systemes_de(record)),
        horodatage=horodatage(record.get("horodatage")),
        texte=texte,
        duree_mesuree_minutes=duree,
        duree_statut=statut_duree if duree is not None else StatutDuree.INFERREE,
        groupe_pseudonyme=str(record.get("groupe_pseudonyme", "")),
        service=str(record.get("service", "")),
        systemes=systemes_de(record),
        atypique=bool(record.get("atypique", False)),
    )


def heures_mesurees(activites: tuple[Activite, ...] | list[Activite]) -> Decimal:
    """Total measured hours of a set of activities (coverage numerator)."""
    total = Decimal(0)
    for activite in activites:
        if activite.duree_mesuree_minutes is not None:
            total += activite.duree_mesuree_minutes
    return total / 60
