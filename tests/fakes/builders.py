"""Builders shared by the tests: turn the ground truth into contract objects.

`demo/spec-processus.json` is the frozen truth of the 23 demo processes (lot 0).
These helpers keep every test that reads it short, and keep the mapping in one
place instead of five.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from gisement.types.communs import (
    Canal,
    MotifDeconseil,
    Repartition,
    StatutDuree,
    TypeAutomatisation,
)
from gisement.types.economie import (
    DecompositionCout,
    Deconseille,
    FaitsFaisabilite,
    Gisement,
    Intervalle,
)
from gisement.types.mesure import Processus, StatutValidation

RACINE = Path(__file__).resolve().parents[2]
VERITE = (RACINE / "demo" / "spec-processus.json").resolve()


def charger_verite() -> dict:
    """The whole ground truth document."""
    return json.loads(VERITE.read_text(encoding="utf-8"))


def processus_verite() -> list[dict]:
    """The 23 processes, in id order."""
    return charger_verite()["processus"]


def identifiants_verite() -> list[str]:
    return [p["id"] for p in processus_verite()]


def decimal(valeur: object) -> Decimal:
    if valeur is None:
        return Decimal(0)
    return Decimal(str(valeur))


def processus_depuis_spec(spec: dict) -> Processus:
    return Processus(
        id=spec["id"],
        campagne_id="CMP-DEMO",
        nom=spec["nom"],
        service=spec["service"],
        motif_ids=tuple(spec["motifs"]),
        validation=StatutValidation.VALIDEE,
        canaux=tuple(Canal(c) for c in spec["canaux"]),
        famille_poste=spec["famille_poste"],
        changements_douze_mois=spec["changements_douze_mois"],
        visibilite_dirigeant=spec["visibilite_dirigeant"],
        saisonnier=spec.get("piege") == "pic_saisonnier",
    )


def faits_depuis_spec(spec: dict) -> FaitsFaisabilite:
    return FaitsFaisabilite(**spec["faits"])


def cout_depuis_attendu(spec: dict) -> DecompositionCout:
    attendu = spec["attendu"]["cout"]
    return DecompositionCout(
        developpement=decimal(attendu["developpement"]),
        outil_annuel=decimal(attendu["outil_annuel"]),
        maintenance_annuelle=decimal(attendu["maintenance_annuelle"]),
        annee_1=decimal(attendu["annee_1"]),
        recurrent=decimal(attendu["recurrent"]),
    )


def gisement_depuis_attendu(spec: dict) -> Gisement:
    """A `Gisement` carrying the expected figures, without recomputing them."""
    attendu = spec["attendu"]
    net = decimal(attendu["temps_net_heures"])
    return Gisement(
        processus_id=spec["id"],
        temps_brut_heures=decimal(attendu["temps_brut_heures"]),
        coefficient_fragmentation=decimal(attendu["coefficient_fragmentation"]),
        temps_fragmente_heures=decimal(attendu["temps_fragmente_heures"]),
        temps_transfere_heures=decimal(attendu["temps_transfere_heures"]),
        detail_transfert=tuple((c["nom"], decimal(c.get("forfait_heures") or 0)) for c in spec["transfert"]),
        temps_ineliminable_heures=decimal(attendu["temps_ineliminable_heures"]),
        temps_net_heures=net,
        temps_net_intervalle=Intervalle(bas=net, haut=net),
        cout=cout_depuis_attendu(spec),
        taux_horaire=decimal("42"),
        gain_mensuel=decimal(attendu["gain_mensuel"]),
        gain_annuel=decimal(attendu["gain_annuel"]),
        gain_naif_mensuel=decimal(attendu["gain_naif_mensuel"]),
        ecart_naif=decimal(attendu["ecart_naif"]) if attendu["ecart_naif"] else None,
        delai_retour_mois=decimal(attendu["delai_retour_mois"]) if attendu["delai_retour_mois"] else None,
        gain_trois_ans=decimal(attendu["gain_trois_ans"]),
    )


def deconseilles_depuis_spec(spec: dict) -> tuple[Deconseille, ...]:
    """The advised-against reasons the ground truth expects."""
    return tuple(
        Deconseille(
            processus_id=spec["id"],
            motif=MotifDeconseil(item["motif"]),
            seuil_atteint=item["seuil"],
            condition_reexamen=item["condition"],
        )
        for item in spec["deconseil_attendu"]
    )


def type_attendu(spec: dict) -> TypeAutomatisation:
    return TypeAutomatisation(spec["type_final_attendu"])


def repartition_depuis_spec(spec: dict) -> Repartition:
    return Repartition(spec["repartition"])


def statut_duree_depuis_spec(spec: dict) -> StatutDuree:
    return StatutDuree(spec["duree_statut"])
