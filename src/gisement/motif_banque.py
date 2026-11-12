"""The catalogue is alive (idea #5): proposals, validation, emerging motifs.

A closed catalogue is a tool that only recognises what its author imagined. Two
mechanisms keep it open:

* **Validation loop** - a group that matches nothing becomes a proposed motif
  (EF-21); a human validates it, and it is written into `catalogue/motifs/` as
  data. No code change, no release (R25).
* **Emergence** - comparing two campaigns shows a motif that appeared, or whose
  volume grew: that is a new deposit, and it is what makes the quarterly
  follow-up worth paying for.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from gisement.types.communs import arrondi, decimal
from gisement.types.mesure import Motif

RACINE_CATALOGUE = Path(__file__).resolve().parents[2] / "catalogue"

#: Fields a proposed motif carries when the classifier could not infer them.
DEFAUTS_PROPOSITION: dict[str, object] = {
    "famille": "a_classer",
    "description": "Motif propose par la mesure, a valider par un consultant.",
    "duree_unitaire_typique_minutes": "6",
    "duree_statut_defaut": "inferree",
    "repartition_defaut": "semi_regroupee",
    "taux_revue_defaut": "0.20",
    "duree_revue_minutes": "1.5",
    "part_atypique_defaut": "0.15",
    "types_envisageables": ["B"],
    "cout_jours_min": "3",
    "cout_jours_max": "12",
    "abonnement_mensuel": "0",
}

#: A motif whose volume grows by more than this share is worth a project.
SEUIL_EMERGENCE = Decimal("30")


@dataclass(frozen=True)
class Proposition:
    """A motif the measurement proposes to add to the catalogue."""

    ref_proposee: str
    nom: str
    nom_en: str
    famille: str
    modele_texte: str
    occurrences: int
    confiance: Decimal
    canaux: tuple[str, ...]
    systemes: tuple[str, ...]
    duree_typique: str
    a_valider: bool

    def en_donnees(self) -> dict:
        """The catalogue entry, in the loader's own shape."""
        return {
            "ref": self.ref_proposee,
            "famille": self.famille,
            "nom": self.nom,
            "nom_en": self.nom_en,
            "description": str(DEFAUTS_PROPOSITION["description"]),
            "canaux": list(self.canaux),
            "indices": {"verbes": [], "objets": [], "systemes": list(self.systemes)},
            "modele_texte": self.modele_texte,
            **{
                cle: valeur
                for cle, valeur in DEFAUTS_PROPOSITION.items()
                if cle not in ("famille", "description")
            },
            "duree_unitaire_typique_minutes": self.duree_typique,
        }


@dataclass(frozen=True)
class MotifEmergent:
    """A motif whose volume moved between two campaigns."""

    ref: str
    nom: str
    occurrences_avant: int
    occurrences_apres: int
    variation: Decimal
    recommandation: str


def propositions(
    motifs: Sequence[Motif], seuil_confiance: Decimal = Decimal("0.70")
) -> tuple[Proposition, ...]:
    """Every uncatalogued motif becomes a proposal, richest first."""
    nouveaux = sorted((m for m in motifs if m.nouveau), key=lambda m: (-m.occurrences.mediane, m.id))
    return tuple(_proposition(motif, rang, seuil_confiance) for rang, motif in enumerate(nouveaux, start=1))


def _proposition(motif: Motif, rang: int, seuil: Decimal) -> Proposition:
    nom = motif.nom or "Motif a nommer"
    duree = motif.duree_unitaire_minutes or decimal(DEFAUTS_PROPOSITION["duree_unitaire_typique_minutes"])
    return Proposition(
        ref_proposee=f"PROP-{rang:02d}",
        nom=nom,
        nom_en=nom,
        famille=str(DEFAUTS_PROPOSITION["famille"]),
        modele_texte=nom,
        occurrences=int(motif.occurrences.mediane),
        confiance=motif.confiance,
        canaux=tuple(c.value for c in motif.canaux),
        systemes=_systemes_de_la_proposition(motif.proposition_catalogue),
        duree_typique=str(arrondi(duree, 1)),
        a_valider=motif.confiance < seuil,
    )


def _systemes_de_la_proposition(brut: str) -> tuple[str, ...]:
    """The systems the classifier put in its proposal, if it is parsable JSON."""
    if not brut:
        return ()
    try:
        donnees = json.loads(brut)
    except json.JSONDecodeError:
        return ()
    return tuple(donnees.get("indices", {}).get("systemes", ()))


def emergentes(
    avant: Mapping[str, int],
    apres: Mapping[str, int],
    seuil_variation: Decimal = SEUIL_EMERGENCE,
    noms: Mapping[str, str] | None = None,
) -> tuple[MotifEmergent, ...]:
    """What appeared, and what grew, between two campaigns."""
    noms = noms or {}
    resultats: list[MotifEmergent] = []
    for ref in sorted(set(avant) | set(apres)):
        precedent = int(avant.get(ref, 0))
        courant = int(apres.get(ref, 0))
        if precedent == 0 and courant > 0:
            resultats.append(
                MotifEmergent(
                    ref=ref,
                    nom=noms.get(ref, ref),
                    occurrences_avant=0,
                    occurrences_apres=courant,
                    variation=Decimal(0),
                    recommandation=(
                        f"nouveau motif apparu : {courant} occurrences par mois sur la campagne ; "
                        "un projet se prepare, a inscrire au prochain portefeuille"
                    ),
                )
            )
            continue
        if precedent <= 0:
            continue
        variation = arrondi(decimal(courant - precedent) / decimal(precedent) * 100, 1)
        if abs(variation) >= seuil_variation:
            sens = "hausse" if variation > 0 else "baisse"
            resultats.append(
                MotifEmergent(
                    ref=ref,
                    nom=noms.get(ref, ref),
                    occurrences_avant=precedent,
                    occurrences_apres=courant,
                    variation=variation,
                    recommandation=(
                        f"volume en {sens} de {abs(variation)} % ({precedent} -> {courant} "
                        "occurrences par mois) : le chiffre d'affaires du projet change, "
                        "la sequence doit etre rejouee"
                    ),
                )
            )
    return tuple(resultats)


def valider(proposition: Proposition, racine: str | Path | None = None) -> str:
    """Write a validated proposal into the catalogue, as data (R25)."""
    cible = Path(racine) if racine else RACINE_CATALOGUE
    dossier = cible / "motifs"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{proposition.famille}.json"
    existants = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else []
    if any(m.get("ref") == proposition.ref_proposee for m in existants):
        raise ValueError(f"la reference {proposition.ref_proposee} existe deja dans le catalogue")
    existants.append(proposition.en_donnees())
    chemin.write_text(json.dumps(existants, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return proposition.ref_proposee


def fusionner(propositions: Sequence[Proposition], racine: str | Path | None = None) -> int:
    """Validate a batch of proposals; returns how many motifs were added."""
    return sum(1 for proposition in propositions if valider(proposition, racine))


def charger_volumes(chemin: str | Path) -> dict[str, int]:
    """Read a `{motif: occurrences}` file, as written by the demo generator."""
    brut = json.loads(Path(chemin).read_text(encoding="utf-8"))
    return {str(cle): int(valeur) for cle, valeur in brut.get("motifs", brut).items()}
