"""The sanitisation report: what came in, what was dropped, what was applied.

EF-16 and ENF-05 need a trace: a corpus that cannot say how many records it
dropped, and why, is a corpus nobody can audit. The report is published in the
compliance register (chapter 24.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gisement.types.communs import Canal


@dataclass(frozen=True)
class RapportAssainissement:
    """One pass of sanitisation on one channel."""

    canal: Canal
    volume_entree: int = 0
    volume_sortie: int = 0
    pseudonymes_appliques: int = 0
    categories_sensibles: tuple[str, ...] = ()
    exclus: int = 0
    motifs_exclusion: dict[str, int] = field(default_factory=dict)
    graine: int = 0

    @property
    def taux_exclusion(self) -> float:
        if self.volume_entree == 0:
            return 0.0
        return self.exclus / self.volume_entree

    def est_conforme(self) -> bool:
        """ENF-05: nothing sensitive was stored, and the counts add up."""
        return self.volume_sortie + self.exclus == self.volume_entree


def fusionner(rapports: tuple[RapportAssainissement, ...]) -> dict[Canal, RapportAssainissement]:
    """One report per channel (a collector may run in several passes)."""
    cumul: dict[Canal, RapportAssainissement] = {}
    for rapport in rapports:
        precedent = cumul.get(rapport.canal)
        if precedent is None:
            cumul[rapport.canal] = rapport
            continue
        motifs = dict(precedent.motifs_exclusion)
        for categorie, nombre in rapport.motifs_exclusion.items():
            motifs[categorie] = motifs.get(categorie, 0) + nombre
        categories = tuple(sorted(set(precedent.categories_sensibles) | set(rapport.categories_sensibles)))
        cumul[rapport.canal] = RapportAssainissement(
            canal=rapport.canal,
            volume_entree=precedent.volume_entree + rapport.volume_entree,
            volume_sortie=precedent.volume_sortie + rapport.volume_sortie,
            pseudonymes_appliques=precedent.pseudonymes_appliques + rapport.pseudonymes_appliques,
            categories_sensibles=categories,
            exclus=precedent.exclus + rapport.exclus,
            motifs_exclusion=motifs,
            graine=rapport.graine or precedent.graine,
        )
    return cumul


def lignes_registre(rapports: dict[Canal, RapportAssainissement]) -> tuple[str, ...]:
    """Human readable lines for the compliance register (EF-62)."""
    lignes: list[str] = []
    for canal in sorted(rapports, key=lambda c: c.value):
        rapport = rapports[canal]
        lignes.append(
            f"{canal.value}: {rapport.volume_entree} entrees, {rapport.volume_sortie} conservees, "
            f"{rapport.exclus} exclues, {rapport.pseudonymes_appliques} pseudonymes appliques"
        )
        if rapport.categories_sensibles:
            lignes.append(f"  categories filtrees: {', '.join(rapport.categories_sensibles)}")
    return tuple(lignes)
