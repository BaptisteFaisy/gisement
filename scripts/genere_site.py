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

from gisement.api import handlers, vues_mesure, vues_produits  # noqa: E402
from gisement.api.auth import Identite  # noqa: E402
from gisement.types.communs import Role  # noqa: E402

MSP = Identite(tenant_id="T-DEMO", role=Role.CONSULTANT_MSP, utilisateur="u-consultant_msp")
DPO = Identite(tenant_id="T-DEMO", role=Role.DPO, utilisateur="u-dpo")

FICHIERS_STATIQUES = ("index.html", "styles.css", "app.js", "vues.js")


def _etat_lance():
    """A campaign with the DPO validation recorded and the measurement run."""
    etat = handlers.Etat.demo()
    handlers.declarer_conformite(etat, DPO, {})
    handlers.lancer(etat, MSP)
    return etat


def _ajouter_mesures(carte: dict, etat) -> None:
    """The two measure calls: the individual one refused, the aggregated one allowed."""
    individuel = {
        "canal": "tickets",
        "groupements": ["service", "individu"],
        "taille_groupe": 1,
        "taille_resultat_apres_filtres": 1,
        "filtres": {"service": "adv"},
    }
    agrege = {
        "canal": "tickets",
        "groupements": ["service", "motif"],
        "taille_groupe": 34,
        "taille_resultat_apres_filtres": 34,
        "filtres": {"service": "adv"},
    }
    carte["POST /api/mesure#individu"] = _reponse(handlers.mesurer(etat, MSP, individuel))
    carte["POST /api/mesure#agrege"] = _reponse(handlers.mesurer(etat, MSP, agrege))


def _reponse(resultat) -> dict:
    statut, corps = resultat
    return {"statut": statut, "corps": corps}


def construire_carte() -> dict:
    """Run the handlers once and capture every response the portal reads."""
    carte: dict[str, dict] = {}
    etat_demo = handlers.Etat.demo()
    carte["POST /api/campagnes/courante/conformite"] = _reponse(
        handlers.declarer_conformite(etat_demo, DPO, {})
    )
    carte["POST /api/campagnes/courante/lancer"] = _reponse(handlers.lancer(etat_demo, MSP))
    carte["POST /api/campagnes/courante/suspendre"] = _reponse(handlers.suspendre(etat_demo, DPO))
    etat = _etat_lance()
    carte["GET /api/campagnes/courante"] = _reponse(handlers.campagnes_detail(etat))
    carte["GET /api/projets"] = _reponse(handlers.projets(etat))
    carte["GET /api/deconseilles"] = _reponse(handlers.deconseilles(etat))
    carte["GET /api/gisements/P-07"] = _reponse(handlers.gisement_detail(etat, "P-07"))
    carte["GET /api/rapports/CMP-0031?langue=fr"] = _reponse(handlers.rapport(etat, "fr"))
    carte["GET /api/rapports/CMP-0031?langue=en"] = _reponse(handlers.rapport(etat, "en"))
    carte["GET /api/registre-conformite/CMP-0031?langue=fr"] = _reponse(handlers.registre(etat, "fr"))
    carte["GET /api/budget"] = _reponse(handlers.budget(etat))
    _ajouter_vues(carte, etat)
    _ajouter_mesures(carte, etat)
    return carte


def _ajouter_vues(carte: dict, etat) -> None:
    """Every feature view of the portal, pre-computed from the same handlers."""

    def ajouter(clef, resultat):
        carte[clef] = _reponse(resultat)

    ajouter("GET /api/campagne", (200, {"ok": True, "donnees": vues_produits.campagne_courante()}))
    ajouter("GET /api/processus", vues_mesure.processus_table(etat.resultat))
    ajouter("GET /api/motifs", vues_mesure.motifs_mesures(etat.resultat))
    ajouter("GET /api/catalogue", vues_mesure.catalogue_complet())
    ajouter("GET /api/plan", vues_mesure.plan_projet(etat.resultat))
    ajouter("GET /api/suivi", vues_produits.suivi_longitudinal(etat.resultat))
    ajouter("GET /api/backtest", vues_produits.backtest())
    ajouter("GET /api/evaluation", vues_produits.evaluation())
    ajouter("GET /api/privacy", vues_produits.privacy(etat.resultat))
    ajouter("GET /api/cedar", vues_produits.politique_cedar_vue())
    ajouter("GET /api/connecteurs", vues_produits.connecteurs())
    ajouter("GET /api/proposition", vues_produits.proposition(etat.resultat))
    ajouter("GET /api/quick", vues_produits.quick_assets(etat.resultat))
    ajouter("GET /api/cout", vues_produits.cout_detaille())
    for mesure in etat.resultat.mesures:
        identifiant = mesure.declare.id
        ajouter(
            f"GET /api/processus/{identifiant}",
            vues_mesure.processus_fiche(etat.resultat, identifiant),
        )


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
