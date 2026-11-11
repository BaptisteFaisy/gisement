"""Second pass of the classifier: the model labels one **group** (21.2).

The deterministic score picks the candidates, the model chooses among them and
produces a confidence and a citation. When the model has nothing to add - which
is the case offline, and the case in every test - the deterministic score
decides, and a group below the confidence threshold goes to human review.

One call per group, never one per activity: that is the whole budget story
(annex G.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from gisement.calcul.occurrences import statistiques
from gisement.classifieur.nouveaux import proposer_nouveau_motif
from gisement.modeles.base import Modele, ReponseModele
from gisement.motifs.catalogue import CandidatMotif, Catalogue
from gisement.motifs.recherche import candidats as scorer_candidats
from gisement.types.communs import (
    SEUIL_CONFIANCE_CLASSIFICATION,
    Canal,
    Repartition,
    StatutDuree,
    decimal,
)
from gisement.types.mesure import GroupeEmpreinte, Motif

#: Structured output asked of the model (EF-20).
SCHEMA_ETIQUETAGE = {
    "type": "object",
    "properties": {
        "motif_ref": {"type": "string"},
        "confiance": {"type": "number"},
        "citations": {"type": "array"},
        "faits": {
            "type": "object",
            "properties": {
                "etape_supprimable_amont": {"type": "boolean"},
                "api_ou_flux_natif": {"type": "boolean"},
                "travail_deterministe": {"type": "boolean"},
                "interface_stable": {"type": "boolean"},
                "jugement_requis": {"type": "boolean"},
            },
        },
    },
    "required": ["motif_ref", "confiance"],
}

#: Below this deterministic score there is no candidate worth labelling.
SEUIL_NOUVEAU_MOTIF = Decimal("0.30")
NB_CANDIDATS_PROPOSES = 5


def invite_etiquetage(groupe: GroupeEmpreinte, candidats: Sequence[CandidatMotif]) -> str:
    """The prompt of one group: facts only, no figure to compute (EF-35)."""
    lignes = [
        "Etiquette ce groupe d'activites repetitives avec un motif du catalogue.",
        f"Geste observe : {groupe.signature}",
        f"Exemple : {groupe.exemple_texte}",
        f"Systemes touches : {', '.join(groupe.systemes) or 'aucun'}",
        f"Canaux : {', '.join(c.value for c in groupe.canaux)}",
        f"Occurrences du groupe : {groupe.occurrences}",
        "Motifs candidats :",
    ]
    lignes += [f"- {c.ref} {c.nom} (score {c.score})" for c in candidats]
    lignes.append("Reponds avec motif_ref, confiance et les faits observables.")
    return "\n".join(lignes)


def etiqueter(
    groupes: Sequence[GroupeEmpreinte],
    catalogue: Catalogue,
    modele: Modele,
    campagne_id: str,
) -> tuple[Motif, ...]:
    """Label every group. One model call per group."""
    return tuple(etiquette_groupe(g, catalogue, modele, campagne_id) for g in groupes)


def etiquette_groupe(
    groupe: GroupeEmpreinte, catalogue: Catalogue, modele: Modele, campagne_id: str
) -> Motif:
    candidats = scorer_candidats(catalogue, groupe.signature, groupe.systemes, NB_CANDIDATS_PROPOSES)
    if not candidats or candidats[0].score < SEUIL_NOUVEAU_MOTIF:
        return proposer_nouveau_motif(groupe, campagne_id)
    reponse = modele.classer(invite_etiquetage(groupe, candidats), SCHEMA_ETIQUETAGE)
    ref, confiance = _decider(reponse, candidats, catalogue)
    motif_catalogue = catalogue.par_ref(ref)
    return _construire_motif(groupe, motif_catalogue, ref, confiance, campagne_id, reponse)


def _decider(
    reponse: ReponseModele, candidats: Sequence[CandidatMotif], catalogue: Catalogue
) -> tuple[str, Decimal]:
    """The model chooses among the candidates; the score decides if it abstains."""
    propose = str(reponse.donnees.get("motif_ref", ""))
    if propose and propose in catalogue.refs():
        return propose, max(reponse.confiance, candidats[0].score)
    return candidats[0].ref, candidats[0].score


def _construire_motif(
    groupe: GroupeEmpreinte,
    motif_catalogue,
    ref: str,
    confiance: Decimal,
    campagne_id: str,
    reponse: ReponseModele,
) -> Motif:
    duree, statut = _duree(groupe, motif_catalogue)
    repartition = _repartition(groupe, motif_catalogue)
    return Motif(
        id=f"M-{ref}-{groupe.empreinte[:6]}",
        campagne_id=campagne_id,
        nom=motif_catalogue.nom,
        catalogue_ref=ref,
        confiance=confiance,
        occurrences=statistiques([decimal(c) for c in groupe.occurrences_mensuelles]),
        duree_unitaire_minutes=duree,
        duree_statut=statut,
        duree_ecart_minutes=groupe.duree_ecart_minutes,
        duree_nb_cas=groupe.duree_nb_cas,
        repartition=repartition,
        part_atypique=groupe.part_atypique,
        part_atypique_nb_cas=groupe.occurrences,
        canaux=tuple(Canal(c) for c in groupe.canaux),
        services=groupe.services,
        empreintes=(groupe.empreinte,),
        nouveau=False,
        en_revue_humaine=confiance < SEUIL_CONFIANCE_CLASSIFICATION,
        proposition_catalogue=str(reponse.donnees.get("commentaire", "")),
    )


def _duree(groupe: GroupeEmpreinte, motif_catalogue) -> tuple[Decimal, StatutDuree]:
    """Measured when the group carries timestamps, typical otherwise (9.3)."""
    if groupe.duree_mesuree_minutes is not None and groupe.duree_statut == StatutDuree.MESUREE:
        return groupe.duree_mesuree_minutes, StatutDuree.MESUREE
    return (
        motif_catalogue.duree_unitaire_typique_minutes,
        motif_catalogue.duree_statut_defaut,
    )


#: Below this many occurrences an hourly spread cannot be read from the data:
#: a sample of 24 says nothing about how the work spreads over a day.
SEUIL_INFERENCE_REPARTITION = 100


def _repartition(groupe: GroupeEmpreinte, motif_catalogue) -> Repartition:
    """When the clock can be trusted, and when it cannot (13.1, 9.3).

    Three cases fall back on the motif's typical spread: INTERRUPTIVE, which is
    a property of the gesture and not of the clock; a group read mainly from
    recorded calls, where the recording start says nothing about when the work
    happens; and a group too small for an hourly distribution to mean anything.
    """
    if motif_catalogue.repartition_defaut == Repartition.INTERRUPTIVE:
        return Repartition.INTERRUPTIVE
    if groupe.canal == Canal.APPELS:
        return motif_catalogue.repartition_defaut
    if groupe.occurrences < SEUIL_INFERENCE_REPARTITION:
        return motif_catalogue.repartition_defaut
    return groupe.repartition_horaire
