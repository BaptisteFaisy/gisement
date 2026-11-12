"""Command line entry point of Gisement.

Thin dispatcher on purpose: each command lives in its own module under
`gisement/commands/`, owned by one lot, so two lots never edit the same file.

    python3 -m gisement.cli smoke
    python3 -m gisement.cli demo
    python3 -m gisement.cli eval
"""

from __future__ import annotations

import importlib
import sys

COMMANDES: tuple[str, ...] = (
    "smoke",
    "demo",
    "generer",
    "mesurer",
    "portefeuille",
    "rapport",
    "proposition",
    "suivi",
    "eval",
    "motif",
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
    "proposition": "produce the MSP commercial proposal, as text or PDF",
    "suivi": "record a quarter of realised against predicted (lot 17)",
    "eval": "run the evaluation harness: classification, k>=5, economics (lot 22)",
    "motif": "the living catalogue: proposals, validation, emerging motifs",
    "assets": "write the Amazon Quick asset bundle (lot 19)",
    "serve": "serve the portal API locally (lot 18)",
}


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


def aide() -> str:
    lignes = ["usage: gisement <commande> [options]", "", "commandes:"]
    lignes += [f"  {nom:14s} {DESCRIPTIONS.get(nom, nom)}" for nom in COMMANDES]
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> int:
    """Dispatch on the first argument; the rest goes to the command as-is."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(aide())
        return 0
    commande, reste = args[0], args[1:]
    if commande not in COMMANDES:
        print(f"gisement: commande inconnue '{commande}'", file=sys.stderr)
        print(aide(), file=sys.stderr)
        return 2
    return executer(commande, reste)


if __name__ == "__main__":
    sys.exit(main())
