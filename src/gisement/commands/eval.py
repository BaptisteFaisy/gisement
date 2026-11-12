"""`gisement eval` - run the evaluation harness (lot 22, chapter 27).

Classification accuracy, motif recall, economic accuracy and the blocking
non-attribution check, in one command.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    del argv
    environnement = dict(__import__("os").environ, PYTHONPATH=str(RACINE / "src"))
    codes = []
    for script in ("eval/harnais.py", "eval/non_attribution.py", "eval/backtest.py"):
        resultat = subprocess.run(
            [sys.executable, str(RACINE / script)], cwd=RACINE, env=environnement, check=False
        )
        codes.append(resultat.returncode)
    return max(codes)
