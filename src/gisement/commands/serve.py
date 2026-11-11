"""`gisement serve` - run the demo portal locally (lot 18).

    python3 -m gisement.cli serve --port 8080

The portal is the static SPA of `portal/`, served with the JSON API of
`gisement.api.serveur`. No framework, no credential, no network: the demo
tokens are listed in `gisement.api.auth`.
"""

from __future__ import annotations

import argparse

from gisement.api.serveur import servir


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--hote", default="127.0.0.1")
    parseur.add_argument("--port", type=int, default=8080)
    args = parseur.parse_args(argv)
    servir(args.hote, args.port)
    return 0
