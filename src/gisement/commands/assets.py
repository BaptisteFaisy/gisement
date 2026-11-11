"""`gisement assets` - the Amazon Quick asset bundle (lot 19).

Quick renders the portfolio, the waves, the trends and the anonymised
cross-client comparison. This command writes the analytical tables (the data
Quick ingests) and the dashboard spec (the visuals), as JSON, into `infra/quick/`.

The tables are published from the measured campaign, so the dashboard and the
report can never disagree: they read the same figures.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from gisement.pipeline import campagne_demo, executer
from gisement.serialisation import ecrire_json
from gisement.types.communs import Vague


def table_portefeuille(resultat) -> list[dict]:
    """One row per project: the portfolio Quick renders."""
    lignes = []
    for projet in resultat.projets:
        lignes.append(
            {
                "processus_id": projet.processus_id,
                "type": projet.faisabilite.type.value,
                "vague": projet.vague.value,
                "rang": projet.rang,
                "risque": projet.risque.value,
                "score": str(projet.score),
                "gain_mensuel": str(projet.gisement.gain_mensuel or 0),
                "gain_annuel": str(projet.gisement.gain_annuel or 0),
                "delai_retour_mois": str(projet.gisement.delai_retour_mois or 0),
                "cout_annee_1": str(projet.gisement.cout.annee_1),
                "deconseille": projet.deconseille.motif.value if projet.deconseille else "",
            }
        )
    return lignes


def table_vagues(resultat) -> list[dict]:
    """One row per wave: the sequence, as the executive sees it."""
    lignes = []
    for vague in (Vague.AMORCAGE, Vague.STRUCTUREL, Vague.TRANSFORMATION):
        projets = [p for p in resultat.portefeuille.projets if p.vague == vague]
        if not projets:
            continue
        cout = sum((p.gisement.cout.annee_1 for p in projets), Decimal(0))
        gain = sum((p.gisement.gain_annuel or Decimal(0) for p in projets), Decimal(0))
        lignes.append(
            {
                "vague": vague.value,
                "nb_projets": len(projets),
                "cout_total": str(cout),
                "gain_annuel_total": str(gain),
                "processus": [p.processus_id for p in projets],
            }
        )
    return lignes


def table_tendances(resultat) -> list[dict]:
    """The monthly series per process: what shows the seasonality (P-16)."""
    lignes = []
    for mesure in resultat.mesures:
        serie = mesure.entree.occurrences.serie
        lignes.append(
            {
                "processus_id": mesure.declare.id,
                "service": mesure.declare.service,
                "occurrences_par_mois": [str(v) for v in serie],
                "mediane": str(mesure.entree.occurrences.mediane),
                "amplitude": [
                    str(mesure.entree.occurrences.minimum),
                    str(mesure.entree.occurrences.maximum),
                ],
            }
        )
    return lignes


VISUELS: tuple[dict, ...] = (
    {
        "id": "kpi-gisement",
        "type": "kpi",
        "dataset": "portefeuille",
        "mesure": "gain_annuel",
        "agregation": "sum",
        "titre": "Gisement net annuel (EUR)",
    },
    {
        "id": "kpi-cout",
        "type": "kpi",
        "dataset": "portefeuille",
        "mesure": "cout_annee_1",
        "agregation": "sum",
        "titre": "Cout total annee 1 (EUR)",
    },
    {
        "id": "vagues",
        "type": "bar",
        "dataset": "vagues",
        "dimension": "vague",
        "mesure": "gain_annuel_total",
        "titre": "Gain annuel par vague",
    },
    {
        "id": "sequence",
        "type": "table",
        "dataset": "portefeuille",
        "colonnes": ["vague", "rang", "processus_id", "type", "gain_mensuel", "delai_retour_mois", "risque"],
        "titre": "La sequence : quoi faire en premier",
    },
    {
        "id": "deconseilles",
        "type": "table",
        "dataset": "portefeuille",
        "filtre": "deconseille != ''",
        "colonnes": ["processus_id", "deconseille"],
        "titre": "A ne pas automatiser",
    },
    {
        "id": "saisonnalite",
        "type": "line",
        "dataset": "tendances",
        "dimension": "occurrences_par_mois",
        "serie": "processus_id",
        "titre": "Saisonnalite : la mediane, pas la moyenne",
    },
)


def spec_tableau_de_bord() -> dict:
    """The Quick dashboard spec: the visuals, bound to the tables above."""
    return {
        "nom": "Gisement - portefeuille",
        "datasets": ["portefeuille", "vagues", "tendances"],
        "visuels": list(VISUELS),
    }


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--out", default="infra/quick")
    args = parseur.parse_args(argv)
    sortie = Path(args.out)

    resultat = executer(campagne_demo())
    ecrire_json(sortie / "portefeuille.json", table_portefeuille(resultat))
    ecrire_json(sortie / "vagues.json", table_vagues(resultat))
    ecrire_json(sortie / "tendances.json", table_tendances(resultat))
    ecrire_json(sortie / "tableau_de_bord.json", spec_tableau_de_bord())
    print(f"assets Quick ecrits dans {sortie}")
    return 0
