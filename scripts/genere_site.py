#!/usr/bin/env python3
"""Build the static, self-contained site from the live handlers (lot 18/24).

GitHub Pages has no backend, so the demo responses are pre-computed here from
the very same handlers the API runs, and written to `site/data/api.json`. The
portal's `app.js` detects the absence of `/api/health` and serves those
responses instead: one front-end, two runtimes, identical figures.

    python3 scripts/genere_site.py [--site site]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from gisement.api import handlers  # noqa: E402
from gisement.api.auth import Identite  # noqa: E402
from gisement.types.communs import Role  # noqa: E402

MSP = Identite(tenant_id="T-DEMO", role=Role.CONSULTANT_MSP, utilisateur="u-consultant_msp")
DPO = Identite(tenant_id="T-DEMO", role=Role.DPO, utilisateur="u-dpo")

FICHIERS_STATIQUES = ("index.html", "styles.css", "app.js")


def construire_carte() -> dict:
    """Run the handlers once and capture every response the portal reads."""
    etat = handlers.Etat.demo()
    carte: dict[str, dict] = {}

    def ajouter(clef, resultat):
        statut, corps = resultat
        carte[clef] = {"statut": statut, "corps": corps}

    ajouter("POST /api/campagnes/courante/conformite", handlers.declarer_conformite(etat, DPO, {}))
    ajouter("POST /api/campagnes/courante/lancer", handlers.lancer(etat, MSP))
    ajouter("POST /api/campagnes/courante/suspendre", handlers.suspendre(etat, DPO))
    # suspendre flips the state; re-launch a clean campaign for the data views
    etat = handlers.Etat.demo()
    handlers.declarer_conformite(etat, DPO, {})
    handlers.lancer(etat, MSP)
    ajouter("GET /api/campagnes/courante", handlers.campagnes_detail(etat))
    ajouter("GET /api/projets", handlers.projets(etat))
    ajouter("GET /api/deconseilles", handlers.deconseilles(etat))
    ajouter("GET /api/gisements/P-07", handlers.gisement_detail(etat, "P-07"))
    ajouter("GET /api/rapports/CMP-0031?langue=fr", handlers.rapport(etat, "fr"))
    ajouter("GET /api/rapports/CMP-0031?langue=en", handlers.rapport(etat, "en"))
    ajouter("GET /api/registre-conformite/CMP-0031?langue=fr", handlers.registre(etat, "fr"))
    ajouter("GET /api/budget", handlers.budget(etat))
    ajouter(
        "POST /api/mesure#individu",
        handlers.mesurer(
            etat,
            MSP,
            {
                "canal": "tickets",
                "groupements": ["service", "individu"],
                "taille_groupe": 1,
                "taille_resultat_apres_filtres": 1,
                "filtres": {"service": "adv"},
            },
        ),
    )
    ajouter(
        "POST /api/mesure#agrege",
        handlers.mesurer(
            etat,
            MSP,
            {
                "canal": "tickets",
                "groupements": ["service", "motif"],
                "taille_groupe": 34,
                "taille_resultat_apres_filtres": 34,
                "filtres": {"service": "adv"},
            },
        ),
    )
    return carte


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--site", default=str(RACINE / "site"))
    args = parseur.parse_args(argv)
    site = Path(args.site)

    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)
    for nom in FICHIERS_STATIQUES:
        shutil.copy2(RACINE / "portal" / nom, site / nom)
    (site / "data").mkdir()
    carte = construire_carte()
    (site / "data" / "api.json").write_text(json.dumps(carte, ensure_ascii=False, indent=2), encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    print(f"site statique genere dans {site} ({len(carte)} reponses pre-calculees)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
