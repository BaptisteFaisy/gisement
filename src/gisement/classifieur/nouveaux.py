"""EF-21 - a homogeneous group that matches nothing becomes a proposed motif.

The catalogue is not closed: a client's work contains gestures nobody wrote
down. Gisement proposes them instead of forcing them into the nearest motif,
which is how a mapping stays honest about what it did not recognise.
"""

from __future__ import annotations

from decimal import Decimal

from gisement.calcul.occurrences import statistiques
from gisement.types.communs import SEUIL_CONFIANCE_CLASSIFICATION, Canal, Repartition, StatutDuree, decimal
from gisement.types.mesure import GroupeEmpreinte, Motif


def proposer_nouveau_motif(groupe: GroupeEmpreinte, campagne_id: str) -> Motif:
    """Build an uncatalogued motif from a group, and the proposal to add it."""
    identifiant = f"M-NOUVEAU-{groupe.empreinte[:8]}"
    return Motif(
        id=identifiant,
        campagne_id=campagne_id,
        nom=_nom_propose(groupe),
        catalogue_ref="",
        confiance=Decimal(0),
        occurrences=statistiques([decimal(c) for c in groupe.occurrences_mensuelles]),
        duree_unitaire_minutes=groupe.duree_mesuree_minutes or Decimal(0),
        duree_statut=(
            StatutDuree.MESUREE if groupe.duree_mesuree_minutes is not None else StatutDuree.INFERREE
        ),
        duree_ecart_minutes=groupe.duree_ecart_minutes,
        duree_nb_cas=groupe.duree_nb_cas,
        repartition=groupe.repartition_horaire or Repartition.DIFFUSE,
        part_atypique=groupe.part_atypique,
        part_atypique_nb_cas=groupe.occurrences,
        canaux=tuple(Canal(c) for c in groupe.canaux),
        services=groupe.services,
        empreintes=(groupe.empreinte,),
        nouveau=True,
        en_revue_humaine=True,
        proposition_catalogue=proposition(groupe),
    )


def _nom_propose(groupe: GroupeEmpreinte) -> str:
    verbe, _, reste = groupe.signature.partition("::")
    objets = reste.split("::")[0].replace("|", " ")
    return f"{verbe.title()} {objets}".strip()


def proposition(groupe: GroupeEmpreinte) -> str:
    """The catalogue entry a human should review, in the loader's own shape."""
    return (
        '{"ref": "NOUVEAU-01", "famille": "a classer", '
        f'"nom": "{_nom_propose(groupe)}", '
        f'"canaux": {[c.value for c in groupe.canaux]}, '
        f'"indices": {{"verbes": [], "objets": [], "systemes": {list(groupe.systemes)}}}, '
        f'"duree_unitaire_typique_minutes": "{groupe.duree_mesuree_minutes or 0}", '
        f'"occurrences_observees": {groupe.occurrences}}}'
    )


def sont_nouveaux(motifs: tuple[Motif, ...] | list[Motif]) -> tuple[Motif, ...]:
    return tuple(m for m in motifs if m.nouveau)


def seuil_confiance() -> Decimal:
    return SEUIL_CONFIANCE_CLASSIFICATION
