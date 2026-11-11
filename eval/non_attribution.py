#!/usr/bin/env python3
"""R7 (blocking) - the 50 non-attribution requests must all be refused.

Run it with:

    PYTHONPATH=src python3 eval/non_attribution.py

Exit code 0 means 50 refusals out of 50, with every expected rule named. One
single miss forbids the submission (spec 27).
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE / "src") not in sys.path:
    sys.path.insert(0, str(RACINE / "src"))

from gisement.politique import cas_depuis_dict, charger_non_attribution, evaluer  # noqa: E402


def verifier(cas: list[dict]) -> tuple[int, list[str]]:
    """Return the number of refusals and the list of problems."""
    refuses = 0
    problemes: list[str] = []
    for brut in cas:
        identifiant, nom, requete, attendues, contexte = cas_depuis_dict(brut)
        decision = evaluer(requete, contexte)
        obtenu = {r.value for r in decision.regles_violees}
        if decision.autorisee:
            problemes.append(f"{identifiant} {nom} : AUTORISEE (refus attendu)")
            continue
        manquantes = set(attendues) - obtenu
        if manquantes:
            problemes.append(f"{identifiant} {nom} : regles absentes {sorted(manquantes)}")
        refuses += 1
    return refuses, problemes


def rapport(cas: list[dict], refuses: int, problemes: list[str]) -> None:
    combinaisons = sum(1 for c in cas if c["nom"] == "combinaison de filtres")
    print(f"{len(cas)} requetes, {refuses} refusees, {combinaisons} par combinaison de filtres")
    for ligne in problemes:
        print(f"  ECHEC {ligne}")
    if not problemes:
        print("R7 OK - aucune mesure individuelle n'est accessible, y compris par filtres combines")


def main(argv: list[str] | None = None) -> int:
    chemin = argv[0] if argv else None
    cas = charger_non_attribution(chemin)
    refuses, problemes = verifier(cas)
    rapport(cas, refuses, problemes)
    return 1 if problemes or refuses != len(cas) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
