"""Run the whole product on the REAL corpus.

    python3 -m reel.corpus --invites     # dump the real prompts a model must answer
    python3 -m reel.corpus               # measure, with the recorded real answers
    python3 -m reel.corpus --resultats   # also write reel/resultats/resultat.json

Three honest rules drive this module:

1. **No invented answer.** The classifier's prompts are dumped as they really
   are, answered once by a real model, and the answers are committed in
   `reel/modele/reponses.json`. CI replays them (`ModeleRejoue`): same answers,
   no network, no credit spent - and a prompt with no recorded answer goes to
   human review instead of being silently labelled.
2. **No ground truth.** A real client has no `spec-processus.json`: the declared
   perimeter is built by `reel/declaration.py` from real components, real KIPs
   and a real model reading them. What is not known stays unknown, and the
   report says so.
3. **No hidden estimate.** The durations this corpus cannot measure come from
   the versioned catalogue and are published as `inferree`.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.modeles.base import Modele, ReponseModele
from gisement.modeles.rejoue import ModeleRejoue
from gisement.pipeline import ResultatCampagne, campagne_depuis_manifeste, executer
from gisement.serialisation import lire_json
from gisement.types.campagne import Campagne

RACINE = Path(__file__).resolve().parents[1]
REEL = RACINE / "reel"
DONNEES = REEL / "donnees"
DECLARATION = DONNEES / "declaration.json"
REPONSES = REEL / "modele" / "reponses.json"
INVITES = REEL / "modele" / "invites.json"
RESULTATS = REEL / "resultats"
MODELE_REEL = "claude-sonnet-4-5 (reponses enregistrees)"


class ModeleEnregistreur:
    """Records the real prompts and answers nothing.

    Used once, to capture exactly what the classifier asks - so a real model can
    answer those prompts and the answers be replayed offline forever after.
    """

    nom = "enregistreur"

    def __init__(self) -> None:
        self.invites: list[dict[str, Any]] = []

    def classer(self, invite: str, schema: dict[str, Any]) -> ReponseModele:
        self.invites.append({"invite": invite, "schema": schema})
        return ReponseModele(donnees={}, confiance=Decimal(0), modele=self.nom)

    def rediger(self, invite: str) -> str:
        self.invites.append({"invite": invite, "redaction": True})
        return ""


def campagne_reelle(racine: Path = REEL) -> Campagne:
    """The real campaign, built from the real manifest (window, channels, tenant)."""
    manifeste = lire_json(racine / "donnees" / "manifeste.json")
    campagne = manifeste.get("campagne", {})
    client = manifeste.get("client", {})
    return campagne_depuis_manifeste(
        racine / "donnees",
        campagne_id=str(campagne.get("id", "CMP-REEL-0001")),
        tenant_id=str(client.get("id", "T-REEL")),
    )


def modele_reel(racine: Path = REEL) -> Modele:
    """The recorded answers of a real model, or a loud absence of them."""
    if not (racine / "modele" / "reponses.json").exists():
        raise SystemExit(
            "aucune reponse de modele enregistree : lancer `python3 -m reel.corpus --invites`, "
            "faire repondre un modele reel, puis rejouer."
        )
    return ModeleRejoue(racine / "modele" / "reponses.json", modele_reel=MODELE_REEL)


#: How many object words a fingerprint keeps on the real corpus. Calibrated on
#: the real corpus itself: six (the demo's value) produces one fingerprint per
#: real activity, and the model budget is gone before the first call.
OBJETS_MAX_REEL = 2


def executer_reel(
    racine: Path = REEL, modele: Modele | None = None, taux_horaire: Decimal | None = None
) -> ResultatCampagne:
    """The whole pipeline, on the real corpus, with the real recorded answers."""
    if taux_horaire is None:
        manifeste = lire_json(racine / "donnees" / "manifeste.json")
        publie = manifeste.get("taux_horaire")
        taux_horaire = Decimal(str(publie)) if publie else None
    return executer(
        campagne_reelle(racine),
        taux_horaire=taux_horaire,
        racine=racine / "donnees",
        declaration=racine / "donnees" / "declaration.json",
        modele=modele,
        cle="cle-campagne-reelle",
        objets_max=OBJETS_MAX_REEL,
    )


def enregistrer_invites(racine: Path = REEL) -> Path:
    """Dump the real prompts of the real corpus, for a real model to answer."""
    enregistreur = ModeleEnregistreur()
    executer_reel(racine, modele=enregistreur)
    chemin = racine / "modele" / "invites.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(enregistreur.invites, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


def groupes_reels(racine: Path = REEL) -> list[dict[str, Any]]:
    """The real fingerprint groups of the real corpus, without any model.

    The grouping is deterministic: it is what the product sees before any model
    is called - the real gestures, the real volumes, the real systems.
    """
    resultat = executer_reel(racine, modele=ModeleEnregistreur())
    return [
        {
            "empreinte": groupe.empreinte,
            "signature": groupe.signature,
            "exemple": groupe.exemple_texte[:300],
            "occurrences": groupe.occurrences,
            "occurrences_mensuelles": [str(o) for o in groupe.occurrences_mensuelles],
            "systemes": list(groupe.systemes),
            "canaux": [c.value for c in groupe.canaux],
            "services": list(groupe.services),
            "duree_mesuree_minutes": str(groupe.duree_mesuree_minutes or ""),
            "part_atypique": str(groupe.part_atypique),
        }
        for groupe in resultat.groupes
    ]


def exporter(resultat: ResultatCampagne, racine: Path = REEL) -> Path:
    """The real figures, serialised: what the portal and the API will publish."""
    from gisement.serialisation import vers_json

    sortie = racine / "resultats" / "resultat.json"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(
        json.dumps(vers_json(resultat), ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    return sortie


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--racine", default=str(REEL))
    parseur.add_argument("--invites", action="store_true", help="dump the real model prompts")
    parseur.add_argument("--groupes", action="store_true", help="dump the real fingerprint groups")
    parseur.add_argument("--resultats", action="store_true", help="also write resultat.json")
    args = parseur.parse_args(argv)
    racine = Path(args.racine)
    if args.groupes:
        groupes = groupes_reels(racine)
        chemin = racine / "modele" / "groupes.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(groupes, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(groupes)} groupes reels ecrits : {chemin}")
        return 0
    if args.invites:
        chemin = enregistrer_invites(racine)
        print(f"{len(lire_json(chemin))} invites reels ecrits : {chemin}")
        return 0
    resultat = executer_reel(racine, modele_reel(racine))
    print(
        json.dumps(
            {
                "campagne": resultat.campagne.id,
                "activites_reelles": resultat.activites,
                "groupes": len(resultat.groupes),
                "motifs": len(resultat.motifs),
                "processus_mesures": sum(1 for m in resultat.mesures if m.est_mesuree),
                "processus_invisibles": sum(1 for m in resultat.mesures if m.est_invisible),
                "projets": len(resultat.projets),
                "deconseilles": len(resultat.deconseilles),
                "revue_humaine": len(resultat.revues),
                "couverture": str(resultat.couverture.globale),
                "appels_modele": resultat.modeles_appels,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.resultats:
        print(f"resultats : {exporter(resultat, racine)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
