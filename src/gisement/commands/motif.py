"""`gisement motif` - the catalogue is data, and it grows (idea #5).

python3 -m gisement.cli motif propositions            # what the measure proposes
python3 -m gisement.cli motif valider PROP-01         # write it into the catalogue
python3 -m gisement.cli motif emergents avant.json apres.json
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from gisement.motif_banque import charger_volumes, emergentes, propositions, valider


def main(argv: list[str] | None = None) -> int:
    args = _parseur().parse_args(argv)
    if args.commande == "propositions":
        return _propositions(args)
    if args.commande == "valider":
        return _valider(args)
    if args.commande == "emergents":
        return _emergents(args)
    print(f"motif : sous-commande inconnue '{args.commande}'", file=sys.stderr)
    return 2


def _parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(description=__doc__)
    sous = parseur.add_subparsers(dest="commande", required=True)
    prop = sous.add_parser("propositions", help="list the motifs the measure proposes")
    prop.add_argument("--seuil", default="0.70")
    val = sous.add_parser("valider", help="write one proposal into the catalogue")
    val.add_argument("ref")
    val.add_argument("--racine", default=None)
    val.add_argument("--nom", default=None)
    emer = sous.add_parser("emergents", help="compare two campaigns' motif volumes")
    emer.add_argument("avant")
    emer.add_argument("apres")
    emer.add_argument("--seuil", default="30")
    return parseur


def _propositions(args) -> int:
    """Run the pipeline and list what the classifier could not match."""
    from gisement.pipeline import campagne_demo, executer

    resultat = executer(campagne_demo())
    liste = propositions(resultat.motifs, decimal_ou(args.seuil, Decimal("0.70")))
    if not liste:
        print("aucun motif nouveau : tout le corpus est couvert par le catalogue")
        return 0
    print(f"{len(liste)} motif(s) propose(s) par la mesure :")
    for proposition in liste:
        etat = "a valider" if proposition.a_valider else "valide automatiquement"
        print(
            f"  {proposition.ref_proposee} {proposition.nom[:50]:52s} "
            f"{proposition.occurrences:5d}/mois  confiance {proposition.confiance}  ({etat})"
        )
    print("\nPour en ajouter un au catalogue : gisement motif valider <ref>")
    return 0


def _valider(args) -> int:
    from gisement.pipeline import campagne_demo, executer

    resultat = executer(campagne_demo())
    liste = {p.ref_proposee: p for p in propositions(resultat.motifs)}
    proposition = liste.get(args.ref)
    if proposition is None:
        print(f"proposition introuvable : {args.ref}", file=sys.stderr)
        return 2
    if args.nom:
        from dataclasses import replace

        proposition = replace(proposition, nom=args.nom, nom_en=args.nom)
    try:
        ref = valider(proposition, Path(args.racine) if args.racine else None)
    except ValueError as erreur:
        print(f"refus : {erreur}", file=sys.stderr)
        return 1
    print(f"motif {ref} ajoute au catalogue (donnees, aucune modification de code)")
    return 0


def _emergents(args) -> int:
    avant = charger_volumes(args.avant)
    apres = charger_volumes(args.apres)
    liste = emergentes(avant, apres, decimal_ou(args.seuil, Decimal("30")))
    if not liste:
        print("aucun motif emergent : les volumes sont stables d'une campagne a l'autre")
        return 0
    for motif in liste:
        print(f"  {motif.ref:10s} {motif.occurrences_avant:5d} -> {motif.occurrences_apres:5d}")
        print(f"             {motif.recommandation}")
    return 0


def decimal_ou(valeur: str, defaut: Decimal) -> Decimal:
    try:
        return Decimal(valeur)
    except (ArithmeticError, ValueError):
        return defaut
