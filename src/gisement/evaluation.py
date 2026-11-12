"""The quality measures of the product (chapter 27, idea #6).

The evaluation harness lives in the product, not in a script: the portal
publishes the numbers, and the CI checks them with the same code.

Four measures:
* classification accuracy on the labelled activities (target >= 88 %);
* recall of the implanted motifs (target >= 90 %);
* accuracy of the economic engine against the ground truth (target 100 %);
* the distribution of the overstatement factor across sectors.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from gisement.calcul import calculer, entree_depuis_spec
from gisement.empreinte import signature
from gisement.motifs import charger_catalogue, meilleur_candidat
from gisement.types.communs import decimal

RACINE = Path(__file__).resolve().parents[2]
DEMO = RACINE / "demo" / "spec-processus.json"
RETOURS = RACINE / "demo" / "retours"
DONNEES = RACINE / "demo" / "donnees"
ETIQUETTES = DONNEES / "attendus" / "activites_etiquetees.json"
MOTIFS_IMPLANTES = DONNEES / "attendus" / "motifs.json"
SECTEURS = ("sante", "logistique", "industrie_services")

SEUIL_CLASSIFICATION = Decimal("0.88")
SEUIL_RAPPEL = Decimal("0.90")
SEUIL_FACTEUR = Decimal("1.5")

CHAMPS_A_VERIFIER = (
    "temps_net_heures",
    "gain_mensuel",
    "gain_annuel",
    "gain_naif_mensuel",
    "ecart_naif",
    "delai_retour_mois",
    "gain_trois_ans",
)


def _charger(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def cas_de_reference() -> list[tuple[str, dict]]:
    """Every reference case: the demo client plus the three other sectors."""
    cas: list[tuple[str, dict]] = []
    for spec in _charger(DEMO)["processus"]:
        cas.append(("distribution_demo", spec))
    for secteur in SECTEURS:
        chemin = RETOURS / f"{secteur}.json"
        if not chemin.exists():
            continue
        for spec in _charger(chemin)["cas"]:
            cas.append((secteur, spec))
    return cas


def precision_classification() -> tuple[Decimal, int, int]:
    """Agreement between the classifier and the hand-labelled activities."""
    if not ETIQUETTES.exists():
        return Decimal(0), 0, 0
    catalogue = charger_catalogue()
    etiquettes = _charger(ETIQUETTES)["activites"]
    accords = 0
    for etiquette in etiquettes:
        motif = catalogue.par_ref(etiquette["motif_attendu"])
        sig = signature(etiquette["texte"], motif.systemes)
        meilleur = meilleur_candidat(catalogue, sig, motif.systemes)
        if meilleur is not None and meilleur.ref == etiquette["motif_attendu"]:
            accords += 1
    total = len(etiquettes)
    return (Decimal(accords) / Decimal(total), accords, total) if total else (Decimal(0), 0, 0)


def rappel_motifs() -> tuple[Decimal, int, int]:
    """Share of the implanted motifs the catalogue recognises."""
    if not MOTIFS_IMPLANTES.exists():
        return Decimal(0), 0, 0
    catalogue = charger_catalogue()
    implantees = _charger(MOTIFS_IMPLANTES)["motifs"]
    reconnus = sum(1 for ref in implantees if ref in catalogue.refs())
    total = len(implantees)
    return (Decimal(reconnus) / Decimal(total), reconnus, total) if total else (Decimal(0), 0, 0)


def precision_economique() -> tuple[Decimal, int, int]:
    """Agreement of the engine with the ground truth: total, the engine is exact."""
    accords = 0
    total = 0
    for _, spec in cas_de_reference():
        attendu = spec.get("attendu")
        if not attendu:
            continue
        total += 1
        if _conforme(calculer(entree_depuis_spec(spec)), attendu):
            accords += 1
    return (Decimal(accords) / Decimal(total), accords, total) if total else (Decimal(0), 0, 0)


def _conforme(gisement, attendu: dict) -> bool:
    for champ in CHAMPS_A_VERIFIER:
        obtenu = getattr(gisement, champ)
        voulu = attendu.get(champ)
        if voulu is None:
            if obtenu is not None:
                return False
        elif obtenu is None or decimal(voulu) != obtenu:
            return False
    return True


def mediane(valeurs: Sequence[Decimal]) -> Decimal:
    if not valeurs:
        return Decimal(0)
    tries = sorted(valeurs)
    milieu = len(tries) // 2
    if len(tries) % 2:
        return tries[milieu]
    return (tries[milieu - 1] + tries[milieu]) / 2


def facteurs_par_secteur() -> dict[str, list[Decimal]]:
    """The naive/net factor per sector, measured by the engine."""
    par_secteur: dict[str, list[Decimal]] = {}
    for secteur, spec in cas_de_reference():
        gisement = calculer(entree_depuis_spec(spec))
        if gisement.ecart_naif is None:
            continue
        par_secteur.setdefault(secteur, []).append(gisement.ecart_naif)
    return par_secteur


def resume_backtest() -> dict:
    """The back-test, as the portal publishes it."""
    par_secteur = facteurs_par_secteur()
    lignes = []
    for secteur in sorted(par_secteur):
        valeurs = par_secteur[secteur]
        lignes.append(
            {
                "secteur": secteur,
                "cas": len(valeurs),
                "min": str(min(valeurs)),
                "median": str(mediane(valeurs)),
                "max": str(max(valeurs)),
            }
        )
    toutes = [v for valeurs in par_secteur.values() for v in valeurs]
    return {
        "secteurs": lignes,
        "cas_total": len(toutes),
        "facteur_median_global": str(mediane(toutes)),
        "facteur_min_global": str(min(toutes)) if toutes else "0",
        "facteur_max_global": str(max(toutes)) if toutes else "0",
        "seuil_de_rupture": str(SEUIL_FACTEUR),
        "tient": mediane(toutes) >= SEUIL_FACTEUR,
    }


def resume_evaluation() -> dict:
    """The four measures of chapter 27, as the portal publishes them."""
    classification, accords_c, total_c = precision_classification()
    rappel, reconnus, total_r = rappel_motifs()
    economique, accords_e, total_e = precision_economique()
    return {
        "classification": {
            "taux": str(classification),
            "accords": accords_c,
            "total": total_c,
            "seuil": str(SEUIL_CLASSIFICATION),
            "tient": classification >= SEUIL_CLASSIFICATION,
        },
        "rappel_motifs": {
            "taux": str(rappel),
            "reconnus": reconnus,
            "total": total_r,
            "seuil": str(SEUIL_RAPPEL),
            "tient": rappel >= SEUIL_RAPPEL,
        },
        "calcul_economique": {
            "taux": str(economique),
            "accords": accords_e,
            "total": total_e,
            "tient": economique == Decimal(1),
        },
        "backtest": resume_backtest(),
    }
