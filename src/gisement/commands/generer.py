"""`gisement generer` - regenerate the synthetic client (lot 3).

    python3 -m gisement.cli generer --sortie demo/donnees
    python3 -m gisement.cli generer --verifier

Thin wrapper over `demo/genere.py`: the generator is a build tool of the demo
dataset, the CLI only exposes it so that `make demo` and the runbook have one
entry point (decision D-19).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
GENERATEUR = RACINE / "demo" / "genere.py"


def main(argv: list[str] | None = None) -> int:
    """Run the generator with the same interpreter, from the repository root."""
    if not GENERATEUR.exists():
        print(f"gisement: generateur introuvable {GENERATEUR}", file=sys.stderr)
        return 2
    commande = [sys.executable, str(GENERATEUR), *(argv or [])]
    # fixed interpreter and fixed script path: nothing comes from the user
    resultat = subprocess.run(commande, cwd=RACINE, check=False)
    return resultat.returncode
