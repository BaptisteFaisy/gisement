"""The campaign stage handler invoked by Step Functions (one state per stage).

The orchestration is declarative: the state machine calls the same Lambda with
a different `stage`, so adding a stage is a state, not a function. The pipeline
itself is the offline one (`gisement.pipeline.executer`) - the same code runs in
CI, in the local demo and in Lambda, which is the point of keeping the handlers
framework-agnostic.

The measured campaign is cached per campaign id inside the warm container: a
mapping takes seconds of compute but re-running the five collectors at every
stage would multiply the cost for nothing (26.4).
"""

from __future__ import annotations

import os
from typing import Any

from gisement.couverture import ligne_publication
from gisement.observabilite import CompteurCout
from gisement.pipeline import ResultatCampagne, campagne_demo, executer
from gisement.types.communs import Vague

ETAPES = ("collect", "classify", "aggregate", "price", "sequence", "report")
CACHE: dict[str, ResultatCampagne] = {}


def resultat_pour(campagne_id: str) -> ResultatCampagne:
    """Run (or reuse) the measurement of one campaign."""
    if campagne_id not in CACHE:
        campagne = campagne_demo()
        if campagne_id and campagne_id != campagne.id:
            from dataclasses import replace

            campagne = replace(campagne, id=campagne_id)
        CACHE[campagne_id] = executer(campagne)
    return CACHE[campagne_id]


def handler(evenement: dict[str, Any], contexte: object = None) -> dict[str, Any]:
    """Lambda entry point: dispatch on the stage asked by Step Functions."""
    del contexte
    etape = str(evenement.get("stage", ""))
    campagne_id = str(evenement.get("campagne") or evenement.get("campagne_id") or "CMP-0031")
    if etape not in ETAPES:
        return {"ok": False, "erreur": f"etape inconnue : {etape}", "etapes": list(ETAPES)}
    resultat = resultat_pour(campagne_id)
    return {"ok": True, "etape": etape, "campagne": campagne_id, **_resume(etape, resultat)}


def _resume(etape: str, resultat: ResultatCampagne) -> dict[str, Any]:
    """The slice of the campaign this stage is responsible for."""
    portefeuille = resultat.portefeuille
    if etape == "collect":
        return {"activites": resultat.activites, "cout_mesure_usd": str(_cout().tarifer().total_usd)}
    if etape == "classify":
        return {
            "groupes": len(resultat.groupes),
            "motifs": len(resultat.motifs),
            "nouveaux_motifs": sum(1 for m in resultat.motifs if m.nouveau),
            "en_revue_humaine": len(resultat.revues),
        }
    if etape == "aggregate":
        return {
            "processus": len(resultat.mesures),
            "invisibles": [m.declare.id for m in resultat.mesures if m.est_invisible],
        }
    if etape == "price":
        return {
            "gisement_net_annuel": str(portefeuille.gain_net_annuel.bas),
            "couverture": ligne_publication(resultat.couverture, os.environ.get("GISMENT_LANGUE", "fr")),
        }
    if etape == "sequence":
        return {
            "vague1_existe": portefeuille.vague1_existe,
            "vagues": {
                vague.value: [p.processus_id for p in portefeuille.projets if p.vague == vague]
                for vague in (Vague.AMORCAGE, Vague.STRUCTUREL, Vague.TRANSFORMATION)
            },
            "deconseilles": [d.processus_id for d in portefeuille.deconseilles],
        }
    return {"rapports": ["rapport-dirigeant", "cas-business", "registre-conformite"], "langues": ["fr", "en"]}


def _cout() -> CompteurCout:
    """The measured cost of the campaign: frozen corpus volumes (annex G.3)."""
    compteur = CompteurCout()
    compteur.charger_tarifs()
    compteur.ajouter_transcribe(360)
    compteur.ajouter_pages(200)
    return compteur
