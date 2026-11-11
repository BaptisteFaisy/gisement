"""Command line entry point of Gisement.

Thin dispatcher on purpose: each command lives in its own module under
`gisement/commands/`, owned by one lot, so two lots never edit the same file.

    python3 -m gisement.cli smoke
    python3 -m gisement.cli demo
    python3 -m gisement.cli eval
"""

from __future__ import annotations

import argparse
import importlib
import sys

COMMANDES: tuple[str, ...] = (
    "smoke",
    "demo",
    "generer",
    "mesurer",
    "portefeuille",
    "rapport",
    "suivi",
    "eval",
    "assets",
    "serve",
)

DESCRIPTIONS: dict[str, str] = {
    "smoke": "run the whole pipeline on the frozen demo corpus and print the portfolio",
    "demo": "regenerate the synthetic dataset, then run smoke",
    "generer": "generate the synthetic demo dataset (lot 3)",
    "mesurer": "run a campaign: ingest, classify, aggregate, compute (lots 4-15)",
    "portefeuille": "print the sequenced portfolio of a campaign (lot 14)",
    "rapport": "produce the executive report and the business cases (lot 16)",
    "suivi": "record a quarter of realised against predicted (lot 17)",
    "eval": "run the evaluation harness: classification, k>=5, economics (lot 22)",
    "assets": "write the Amazon Quick asset bundle (lot 19)",
    "serve": "serve the portal API locally (lot 18)",
}


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(prog="gisement", description=__doc__)
    sous = parseur.add_subparsers(dest="commande", required=True)
    for nom in COMMANDES:
        item = sous.add_parser(nom, help=DESCRIPTIONS.get(nom, nom), add_help=True)
        item.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parseur


def executer(nom: str, arguments: list[str]) -> int:
    """Import the command module and run it. A missing lot is said clearly."""
    try:
        module = importlib.import_module(f"gisement.commands.{nom}")
    except ModuleNotFoundError:
        print(f"gisement: la commande '{nom}' n'est pas encore livree", file=sys.stderr)
        return 2
    if not hasattr(module, "main"):
        print(f"gisement: '{nom}' n'expose pas main(argv)", file=sys.stderr)
        return 2
    return int(module.main(arguments) or 0)


def main(argv: list[str] | None = None) -> int:
    args = construire_parseur().parse_args(argv)
    return executer(args.commande, list(args.arguments))


if __name__ == "__main__":
    sys.exit(main())
