"""Validation of the catalogue (lot 2). The catalogue is data, so it is checked.

A motif that cannot be loaded, a family with the wrong count, a price that is
not a number: all of it is reported as a list of messages, so a partner adding
motifs for their own clients sees exactly what is wrong (Design criterion,
spec 29.1).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from gisement.motifs.catalogue import COMPTES_PAR_FAMILLE, TYPES_VALIDES, Catalogue
from gisement.types.communs import Canal, Repartition, StatutDuree


def valider_catalogue(catalogue: Catalogue) -> tuple[str, ...]:
    """Every consistency rule of annex B. Empty tuple means valid."""
    erreurs: list[str] = []
    erreurs.extend(_comptes(catalogue))
    for motif in catalogue.motifs:
        erreurs.extend(_valider_motif(motif))
    return tuple(erreurs)


def _comptes(catalogue: Catalogue) -> list[str]:
    erreurs: list[str] = []
    if len(catalogue) != sum(COMPTES_PAR_FAMILLE.values()):
        erreurs.append(
            f"le catalogue contient {len(catalogue)} motifs, "
            f"{sum(COMPTES_PAR_FAMILLE.values())} attendus (annexe B)"
        )
    for famille, attendu in COMPTES_PAR_FAMILLE.items():
        obtenu = len(catalogue.famille(famille))
        if obtenu != attendu:
            erreurs.append(f"famille '{famille}' : {obtenu} motifs, {attendu} attendus")
    return erreurs


def _valider_motif(motif) -> list[str]:
    erreurs: list[str] = []
    for champ in ("ref", "famille", "nom", "nom_en"):
        if not getattr(motif, champ):
            erreurs.append(f"{motif.ref or '?'} : champ '{champ}' vide")
    if motif.famille not in COMPTES_PAR_FAMILLE:
        erreurs.append(f"{motif.ref} : famille inconnue '{motif.famille}'")
    if not motif.types_envisageables:
        erreurs.append(f"{motif.ref} : aucun type d'automatisation envisageable")
    for type_ in motif.types_envisageables:
        if type_.value not in TYPES_VALIDES:
            erreurs.append(f"{motif.ref} : type invalide '{type_}'")
    if not motif.canaux:
        erreurs.append(f"{motif.ref} : aucun canal d'observation")
    for canal in motif.canaux:
        if canal not in Canal:
            erreurs.append(f"{motif.ref} : canal invalide '{canal}'")
    if motif.repartition_defaut not in Repartition:
        erreurs.append(f"{motif.ref} : repartition invalide '{motif.repartition_defaut}'")
    if motif.duree_statut_defaut not in StatutDuree:
        erreurs.append(f"{motif.ref} : statut de duree invalide '{motif.duree_statut_defaut}'")
    if not motif.objets or not motif.verbes:
        erreurs.append(f"{motif.ref} : indices de reconnaissance incomplets")
    if not motif.modele_texte:
        erreurs.append(f"{motif.ref} : modele_texte absent (le generateur de demo en a besoin)")
    return erreurs


def refs_en_double(catalogue: Catalogue) -> tuple[str, ...]:
    vus: set[str] = set()
    doublons: list[str] = []
    for motif in catalogue.motifs:
        if motif.ref in vus:
            doublons.append(motif.ref)
        vus.add(motif.ref)
    return tuple(doublons)


def nombres_valides(brut: dict) -> tuple[str, ...]:
    """Check the numeric fields of a raw motif before loading it."""
    champs = (
        "duree_unitaire_typique_minutes",
        "taux_revue_defaut",
        "duree_revue_minutes",
        "part_atypique_defaut",
        "cout_jours_min",
        "cout_jours_max",
        "abonnement_mensuel",
    )
    erreurs: list[str] = []
    for champ in champs:
        try:
            Decimal(str(brut.get(champ, "0")))
        except (InvalidOperation, ValueError, TypeError):
            erreurs.append(f"{brut.get('ref', '?')} : '{champ}' n'est pas un nombre")
    return tuple(erreurs)
