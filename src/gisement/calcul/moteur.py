"""The economic engine (EF-30 to EF-35, annex A).

Pure Python, pure `Decimal`, no model anywhere in this module: a model
classifies facts, this code does the arithmetic. The reference case of annex A
is the acceptance test (R2): 18.4 net hours, 772.80 EUR per month, a 13.7 month
payback, and a naive/real factor of 2.61.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from gisement.calcul.corrections import (
    coefficient_fragmentation,
    decomposer_cout,
    delai_retour,
    ecart_au_naif,
    gain_trois_ans,
    occurrences_effectives,
    temps_brut,
    temps_fragmente,
    temps_ineliminable,
    temps_net,
    temps_transfere,
)
from gisement.calcul.monte_carlo import simuler
from gisement.types.communs import Repartition, StatutDuree, arrondi, decimal, euros, heures
from gisement.types.economie import (
    ComposanteTransfert,
    CoutAutomatisation,
    EntreeGisement,
    FaitsFaisabilite,
    Gisement,
)
from gisement.types.mesure import OccurrencesMensuelles

TAUX_HORAIRE_DEMO = Decimal("42")
GRAINE_DEMO = 20261111


def calculer(entree: EntreeGisement) -> Gisement:
    """One process in, one measured deposit out - with its interval."""
    brut = temps_brut(entree)
    coefficient = coefficient_fragmentation(entree.repartition)
    fragmente = temps_fragmente(entree, brut)
    transfere, detail = temps_transfere(entree, occurrences_effectives(entree))
    ineliminable = temps_ineliminable(entree, brut)
    net = temps_net(fragmente, transfere, ineliminable)
    cout = decomposer_cout(entree.cout)
    taux = entree.taux_horaire
    gain_mensuel = euros(net * taux) if taux is not None else None
    gain_annuel = euros(gain_mensuel * 12) if gain_mensuel is not None else None
    gain_naif = euros(brut * taux) if taux is not None else None
    intervalle_heures, intervalle_gain = simuler(entree, entree.tirages)
    trois_ans = gain_trois_ans(gain_annuel, cout.annee_1, cout.recurrent) if gain_annuel is not None else None
    return Gisement(
        processus_id=entree.processus_id,
        temps_brut_heures=heures(brut),
        coefficient_fragmentation=coefficient,
        temps_fragmente_heures=heures(fragmente),
        temps_transfere_heures=heures(transfere),
        detail_transfert=detail,
        temps_ineliminable_heures=heures(ineliminable),
        temps_net_heures=heures(net),
        temps_net_intervalle=intervalle_heures,
        cout=cout,
        taux_horaire=taux,
        gain_mensuel=gain_mensuel,
        gain_mensuel_intervalle=intervalle_gain,
        gain_annuel=gain_annuel,
        gain_naif_mensuel=gain_naif,
        ecart_naif=ecart_au_naif(gain_naif, gain_mensuel),
        delai_retour_mois=delai_retour(cout.annee_1, gain_mensuel),
        delai_retour_naif_mois=delai_retour(cout.annee_1, gain_naif),
        gain_trois_ans=trois_ans,
        tirages=entree.tirages,
        graine=entree.graine,
    )


def calculer_portefeuille(entrees: Sequence[EntreeGisement]) -> tuple[Gisement, ...]:
    """Every process of a campaign, in the order it was given."""
    return tuple(calculer(entree) for entree in entrees)


def gisement_total(gisements: Sequence[Gisement]) -> Decimal:
    """KPI-2 - the net annual deposit of the portfolio."""
    return arrondi(
        sum((g.gain_annuel or Decimal(0) for g in gisements), Decimal(0)),
        2,
    )


def composante_depuis_spec(brut: dict) -> ComposanteTransfert:
    return ComposanteTransfert(
        nom=brut["nom"],
        taux=decimal(brut["taux"]) if brut.get("taux") is not None else None,
        duree_minutes=decimal(brut["duree_minutes"]) if brut.get("duree_minutes") is not None else None,
        forfait_heures=(decimal(brut["forfait_heures"]) if brut.get("forfait_heures") is not None else None),
    )


def entree_depuis_spec(
    spec: dict, taux_horaire: Decimal | None = TAUX_HORAIRE_DEMO, graine: int = GRAINE_DEMO
) -> EntreeGisement:
    """Build an engine input from one process of `demo/spec-processus.json`."""
    brut = spec["occurrences"]
    cout = spec["cout"]
    return EntreeGisement(
        processus_id=spec["id"],
        part_volume_traitee=decimal(spec["part_volume_traitee"]),
        suppression_etape=bool(spec["suppression_etape"]),
        occurrences=OccurrencesMensuelles(
            serie=tuple(decimal(v) for v in brut["serie"]),
            mediane=decimal(brut["mediane"]),
            minimum=decimal(brut["minimum"]),
            maximum=decimal(brut["maximum"]),
            ecart_type=decimal(brut["ecart_type"]),
            nb_mois=int(brut["nb_mois"]),
        ),
        duree_unitaire_minutes=decimal(spec["duree_unitaire_minutes"]),
        duree_statut=StatutDuree(spec["duree_statut"]),
        duree_ecart_minutes=decimal(spec["duree_ecart_minutes"]),
        duree_nb_cas=int(spec["duree_nb_cas"]),
        repartition=Repartition(spec["repartition"]),
        part_atypique=decimal(spec["part_atypique"]),
        part_atypique_nb_cas=int(spec["part_atypique_nb_cas"]),
        transfert=tuple(composante_depuis_spec(c) for c in spec["transfert"]),
        taux_horaire=taux_horaire,
        cout=CoutAutomatisation(
            jours=decimal(cout["jours"]),
            tjm=decimal(cout["tjm"]),
            abonnement_mensuel=decimal(cout["abonnement_mensuel"]),
            taux_maintenance=decimal(cout["taux_maintenance"]),
        ),
        faits=FaitsFaisabilite(**spec["faits"]),
        graine=graine,
    )


def entrees_depuis_verite(chemin: str | Path | None = None) -> list[EntreeGisement]:
    """The 23 processes of the demo client, ready for the engine."""
    cible = Path(chemin) if chemin else Path(__file__).resolve().parents[3] / "demo" / "spec-processus.json"
    document = json.loads(cible.read_text(encoding="utf-8"))
    return [entree_depuis_spec(spec) for spec in document["processus"]]
