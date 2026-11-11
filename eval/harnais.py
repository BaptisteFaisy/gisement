#!/usr/bin/env python3
"""Evaluation harness (lot 22, chapter 27).

Measures the four quality claims on the frozen demo corpus, offline:

* classification accuracy on the 200 hand-labelled activities (target >= 88 %);
* recall of the implanted motifs (target >= 90 %);
* accuracy of the economic engine against the 23 ground-truth cases (100 %);
* the 50 non-attribution requests (100 % refused - blocking, `non_attribution.py`).

Run it with:

    PYTHONPATH=src python3 eval/harnais.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for chemin in (str(RACINE / "src"), str(RACINE)):
    if chemin not in sys.path:
        sys.path.insert(0, chemin)

from gisement.calcul import calculer, entree_depuis_spec  # noqa: E402
from gisement.empreinte import signature  # noqa: E402
from gisement.motifs import charger_catalogue, meilleur_candidat  # noqa: E402

DONNEES = RACINE / "demo" / "donnees"
SEUIL_CLASSIFICATION = Decimal("0.88")
SEUIL_RAPPEL = Decimal("0.90")


def _charger(nom: str) -> dict:
    return json.loads((DONNEES / "attendus" / nom).read_text(encoding="utf-8"))


def precision_classification() -> tuple[Decimal, int, int]:
    """Agreement between the classifier and the 200 hand-labelled activities."""
    catalogue = charger_catalogue()
    etiquettes = _charger("activites_etiquetees.json")["activites"]
    accords = 0
    for etiquette in etiquettes:
        systemes = tuple(catalogue.par_ref(etiquette["motif_attendu"]).systemes)
        sig = signature(etiquette["texte"], systemes)
        meilleur = meilleur_candidat(catalogue, sig, systemes)
        if meilleur is not None and meilleur.ref == etiquette["motif_attendu"]:
            accords += 1
    total = len(etiquettes)
    return (Decimal(accords) / Decimal(total), accords, total) if total else (Decimal(0), 0, 0)


def rappel_motifs() -> tuple[Decimal, int, int]:
    """Share of the implanted motifs that the catalogue recognises (annex F.4)."""
    catalogue = charger_catalogue()
    implantes = _charger("motifs.json")["motifs"]
    reconnus = sum(1 for ref in implantes if ref in catalogue.refs())
    total = len(implantes)
    return (Decimal(reconnus) / Decimal(total), reconnus, total) if total else (Decimal(0), 0, 0)


def precision_economique() -> tuple[Decimal, int, int]:
    """Agreement of the engine with the 23 ground-truth cases (target 100 %)."""
    verite = json.loads((RACINE / "demo" / "spec-processus.json").read_text(encoding="utf-8"))
    accords = 0
    total = 0
    for spec in verite["processus"]:
        gisement = calculer(entree_depuis_spec(spec))
        attendu = spec["attendu"]
        total += 1
        if _conforme(gisement, attendu):
            accords += 1
    return (Decimal(accords) / Decimal(total), accords, total) if total else (Decimal(0), 0, 0)


def _conforme(gisement, attendu: dict) -> bool:
    champs = {
        "temps_net_heures": gisement.temps_net_heures,
        "gain_mensuel": gisement.gain_mensuel,
        "gain_annuel": gisement.gain_annuel,
        "ecart_naif": gisement.ecart_naif,
        "delai_retour_mois": gisement.delai_retour_mois,
    }
    for nom, valeur in champs.items():
        attendu_valeur = attendu.get(nom)
        if attendu_valeur is None:
            if valeur is not None:
                return False
        elif valeur is None or Decimal(str(attendu_valeur)) != valeur:
            return False
    return True


def rapport(ligne: str, taux: Decimal, numerator: int, denominateur: int, seuil: Decimal) -> bool:
    pourcent = (taux * 100).quantize(Decimal("0.1"))
    statut = "OK " if taux >= seuil else "ECHEC"
    print(f"  [{statut}] {ligne}: {pourcent} % ({numerator}/{denominateur}), seuil {seuil * 100} %")
    return taux >= seuil


def main(argv: Sequence[str] | None = None) -> int:
    print("Harnais d'evaluation - Gisement (chapitre 27)")
    ok = True
    taux, num, den = precision_classification()
    ok &= rapport("precision de classification", taux, num, den, SEUIL_CLASSIFICATION)
    taux, num, den = rappel_motifs()
    ok &= rapport("rappel des motifs implantes", taux, num, den, SEUIL_RAPPEL)
    taux, num, den = precision_economique()
    ok &= rapport("precision du calcul economique", taux, num, den, Decimal(1))
    print(
        "  [voir eval/non_attribution.py] non-attribution: 50 requetes, 50 refus (bloquant)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
