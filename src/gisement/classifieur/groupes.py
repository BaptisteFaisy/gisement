"""First pass of the classifier: group the activities without a model (21.2).

On the demo corpus, 19 200 activities collapse into a few dozen groups. The
model is then called once per group, which is what keeps a mapping under 20 $
(annex G.1: a factor of about 80).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import Decimal

from gisement.empreinte import empreinte
from gisement.types.communs import Canal, Repartition, StatutDuree, arrondi, decimal
from gisement.types.mesure import Activite, GroupeEmpreinte

#: Share of the occurrences held by the busiest hours, per spread class.
SEUIL_REGROUPEE = Decimal("0.70")
SEUIL_SEMI_REGROUPEE = Decimal("0.85")
HEURES_OUVREES = tuple(range(7, 20))


def grouper(activites: Sequence[Activite], mois: Sequence[str] = ()) -> tuple[GroupeEmpreinte, ...]:
    """Group activities by fingerprint **and service**, then measure each group.

    The service is part of the key: the same gesture done by two departments is
    two measurements, and the aggregation into processes (lot 11) is keyed on
    motif + service. The ground truth guarantees that two processes of one
    service never share a primary motif.
    """
    par_cle: dict[tuple[str, str], list[Activite]] = defaultdict(list)
    for activite in activites:
        par_cle[(activite.signature, activite.service)].append(activite)
    return tuple(
        _construire(signature, membres, mois) for (signature, _service), membres in sorted(par_cle.items())
    )


def _construire(signature: str, membres: list[Activite], mois: Sequence[str]) -> GroupeEmpreinte:
    canaux = Counter(a.canal for a in membres)
    services = tuple(sorted({a.service for a in membres if a.service}))
    return GroupeEmpreinte(
        empreinte=empreinte(signature),
        canal=canaux.most_common(1)[0][0],
        signature=signature,
        activites=tuple(a.id for a in membres),
        occurrences=len(membres),
        occurrences_mensuelles=comptes_mensuels(membres, mois),
        exemple_texte=membres[0].texte[:200],
        systemes=tuple(sorted({s for a in membres for s in a.systemes})),
        services=services,
        canaux=tuple(canal for canal, _ in canaux.most_common()),
        taille_groupe_individus=len({a.groupe_pseudonyme for a in membres if a.groupe_pseudonyme}),
        repartition_horaire=inferer_repartition(membres),
        duree_mesuree_minutes=duree_moyenne(membres),
        duree_ecart_minutes=ecart_duree(membres),
        duree_nb_cas=nb_durees_mesurees(membres),
        duree_statut=statut_duree(membres),
        part_atypique=part_atypique(membres),
        nb_atypiques=sum(1 for a in membres if a.atypique),
    )


def comptes_mensuels(membres: Sequence[Activite], mois: Sequence[str]) -> tuple[int, ...]:
    """Occurrences per month of the window; unknown months are dropped."""
    if not mois:
        return ()
    index = {cle: position for position, cle in enumerate(mois)}
    comptes = [0] * len(mois)
    for activite in membres:
        cle = activite.horodatage.strftime("%Y-%m")
        if cle in index:
            comptes[index[cle]] += 1
    return tuple(comptes)


def inferer_repartition(membres: Sequence[Activite]) -> Repartition:
    """13.1 correction 1, inferred from the hour distribution (9.3).

    INTERRUPTIVE is not detectable from timestamps - it is a property of the
    gesture, not of the clock - so it is left to the motif's default.
    """
    heures = Counter(a.horodatage.hour for a in membres)
    total = sum(heures.values())
    if total == 0:
        return Repartition.DIFFUSE
    parts = [Decimal(n) / Decimal(total) for _, n in heures.most_common()]
    if sum(parts[:4]) >= SEUIL_REGROUPEE:
        return Repartition.REGROUPEE
    if sum(parts[:8]) >= SEUIL_SEMI_REGROUPEE:
        return Repartition.SEMI_REGROUPEE
    return Repartition.DIFFUSE


def _durees(membres: Sequence[Activite]) -> list[Decimal]:
    return [a.duree_mesuree_minutes for a in membres if a.duree_mesuree_minutes is not None]


def duree_moyenne(membres: Sequence[Activite]) -> Decimal | None:
    durees = _durees(membres)
    if not durees:
        return None
    return arrondi(sum(durees, Decimal(0)) / Decimal(len(durees)), 2)


def ecart_duree(membres: Sequence[Activite]) -> Decimal:
    durees = _durees(membres)
    if len(durees) < 2:
        return Decimal(0)
    moyenne = sum(durees, Decimal(0)) / Decimal(len(durees))
    variance = sum((d - moyenne) ** 2 for d in durees) / Decimal(len(durees) - 1)
    return arrondi(variance.sqrt(), 3)


def nb_durees_mesurees(membres: Sequence[Activite]) -> int:
    return len(_durees(membres))


def statut_duree(membres: Sequence[Activite]) -> StatutDuree:
    """Measured only if a majority of the group carries a measured duration."""
    if not membres:
        return StatutDuree.INFERREE
    mesures = sum(
        1 for a in membres if a.duree_statut == StatutDuree.MESUREE and a.duree_mesuree_minutes is not None
    )
    return StatutDuree.MESUREE if mesures * 2 >= len(membres) else StatutDuree.INFERREE


def part_atypique(membres: Sequence[Activite]) -> Decimal:
    """13.1 correction 3: the share of cases outside the dominant pattern."""
    if not membres:
        return Decimal(0)
    return arrondi(decimal(sum(1 for a in membres if a.atypique)) / decimal(len(membres)), 4)


def canaux_du_groupe(membres: Sequence[Activite]) -> tuple[Canal, ...]:
    return tuple(canal for canal, _ in Counter(a.canal for a in membres).most_common())
