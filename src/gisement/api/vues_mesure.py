"""Portal views over the measurement: processes, sheets, motifs, catalogue, plan.

Each function returns `(status, body)` like the handlers of `api/handlers.py`, so
the local server, the Lambda and the static site generator share one
implementation. Nothing here computes a figure: everything is read from the
pipeline result (21.5).
"""

from __future__ import annotations

from pathlib import Path

from gisement.motifs.catalogue import charger_catalogue
from gisement.planification import (
    Capacite,
    Dependance,
    chemin_critique,
    gantt,
    jours_necessaires,
    planifier,
)
from gisement.processus import MesureProcessus, comparer_procedure, lire_procedure
from gisement.types.communs import Vague, decimal

RACINE = Path(__file__).resolve().parents[3]
PROCEDURES = RACINE / "demo" / "donnees" / "procedures"

#: Dependencies of the demo client: a project whose input data is cleaned by
#: another one must wait for it (annex A.7 is exactly this reasoning).
DEPENDANCES_DEMO: tuple[Dependance, ...] = (
    Dependance(
        projet_id="P-03",
        apres=("P-07",),
        raison="le rapprochement facture/BL n'est fiable qu'une fois les commandes passées par l'EDI",
    ),
    Dependance(
        projet_id="P-19",
        apres=("P-03",),
        raison="le reporting de gestion consolide des données déjà rapprochées",
    ),
    Dependance(
        projet_id="P-21",
        apres=("P-17",),
        raison="l'analyse des appels suppose l'affectation des demandes déjà automatisée",
    ),
)


def _ok(donnees: object) -> tuple[int, dict]:
    return 200, {"ok": True, "donnees": donnees}


def _erreur(statut: int, message: str) -> tuple[int, dict]:
    return statut, {"ok": False, "erreur": message}


def processus_table(resultat) -> tuple[int, dict]:
    """The 23 processes with their measured volume and their place in the sequence."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    # resultat.projets carries all 23, including the advised-against ones; the
    # portfolio only carries the sequenced waves
    vagues = {p.processus_id: p for p in resultat.projets}
    lignes = []
    for mesure, gisement in zip(resultat.mesures, resultat.gisements, strict=True):
        projet = vagues.get(mesure.declare.id)
        lignes.append(
            {
                "id": mesure.declare.id,
                "nom": mesure.declare.nom,
                "nom_en": mesure.declare.nom_en,
                "service": mesure.declare.service,
                "motif": mesure.declare.motif_primaire,
                "origine": mesure.origine,
                "occurrences_medianes": str(mesure.entree.occurrences.mediane),
                "amplitude": [
                    str(mesure.entree.occurrences.minimum),
                    str(mesure.entree.occurrences.maximum),
                ],
                "duree_minutes": str(mesure.entree.duree_unitaire_minutes),
                "duree_statut": mesure.entree.duree_statut.value,
                "temps_net": str(gisement.temps_net_heures),
                "intervalle": [
                    str(gisement.temps_net_intervalle.bas),
                    str(gisement.temps_net_intervalle.haut),
                ],
                "gain_mensuel": str(gisement.gain_mensuel),
                "gain_annuel": str(gisement.gain_annuel),
                "ecart_naif": str(gisement.ecart_naif),
                "delai_retour_mois": str(gisement.delai_retour_mois),
                "type": projet.faisabilite.type.value if projet else "?",
                "vague": projet.vague.value if projet else "aucune",
                "risque": projet.risque.value if projet else "?",
            }
        )
    return _ok({"nb_processus": len(lignes), "processus": lignes})


def processus_fiche(resultat, processus_id: str) -> tuple[int, dict]:
    """One process sheet in the shape of annex D, including the procedure gap."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    mesure = next((m for m in resultat.mesures if m.declare.id == processus_id), None)
    if mesure is None:
        return _erreur(404, f"processus introuvable : {processus_id}")
    gisement = next(g for g in resultat.gisements if g.processus_id == processus_id)
    projet = next((p for p in resultat.portefeuille.projets if p.processus_id == processus_id), None)
    return _ok(
        {
            "id": processus_id,
            "nom": mesure.declare.nom,
            "service": mesure.declare.service,
            "canaux": [c.value for c in mesure.declare.canaux],
            "volume": _bloc_volume(mesure),
            "travail_reel_vs_procedure": _bloc_procedure(mesure),
            "calcul": _bloc_calcul(gisement),
            "faisabilite": _bloc_faisabilite(projet),
            "recommandation": _bloc_recommandation(projet),
            "confidentialite": (
                "Mesure aggregatee au-dessus du seuil k >= 5. Aucune attribution individuelle. "
                "Pseudonymisation appliquee a l'ingestion, avant tout modele."
            ),
        }
    )


def _bloc_volume(mesure: MesureProcessus) -> dict:
    occ = mesure.entree.occurrences
    return {
        "occurrences_medianes": str(occ.mediane),
        "amplitude_saisonnieres": f"[{occ.minimum} - {occ.maximum}]",
        "serie_mensuelle": [str(v) for v in occ.serie],
        "ecart_type": str(occ.ecart_type),
        "duree_unitaire_minutes": str(mesure.entree.duree_unitaire_minutes),
        "duree_statut": mesure.entree.duree_statut.value,
        "duree_mesuree_sur": mesure.entree.duree_nb_cas,
        "repartition": mesure.entree.repartition.value,
        "part_atypique": str(mesure.entree.part_atypique),
        "origine": mesure.origine,
    }


def _bloc_procedure(mesure: MesureProcessus) -> dict:
    """EF-25 / R12 - the gap between the written procedure and the observed work."""
    reference = mesure.declare.procedure_ref
    chemin = PROCEDURES / f"{reference}.md"
    if not chemin.exists():
        return {"procedure_ref": reference, "ecart": None}
    procedure = lire_procedure(chemin)
    divergence = decimal(mesure.declare.declare.get("part_pratique_divergente", "0"))
    ecart = comparer_procedure(procedure, mesure.declare.canaux, divergence)
    if ecart is None:
        return {"procedure_ref": reference, "ecart": None}
    return {
        "procedure_ref": reference,
        "ecart": {
            "declare": ecart.declare,
            "observe": ecart.observe,
            "majeur": ecart.majeur,
            "part_pratique_divergente": str(ecart.part_pratique_divergente),
            "preuve_canaux": [c.value for c in ecart.preuve_canaux],
        },
    }


def _bloc_calcul(gisement) -> dict:
    return {
        "temps_brut": str(gisement.temps_brut_heures),
        "coefficient_fragmentation": str(gisement.coefficient_fragmentation),
        "temps_fragmente": str(gisement.temps_fragmente_heures),
        "temps_transfere": str(gisement.temps_transfere_heures),
        "detail_transfert": [[nom, str(valeur)] for nom, valeur in gisement.detail_transfert],
        "temps_ineliminable": str(gisement.temps_ineliminable_heures),
        "temps_net": str(gisement.temps_net_heures),
        "intervalle_net": [
            str(gisement.temps_net_intervalle.bas),
            str(gisement.temps_net_intervalle.haut),
        ],
        "gain_mensuel": str(gisement.gain_mensuel),
        "gain_mensuel_intervalle": (
            [str(gisement.gain_mensuel_intervalle.bas), str(gisement.gain_mensuel_intervalle.haut)]
            if gisement.gain_mensuel_intervalle
            else None
        ),
        "gain_annuel": str(gisement.gain_annuel),
        "gain_naif_mensuel": str(gisement.gain_naif_mensuel),
        "ecart_naif": str(gisement.ecart_naif),
        "cout": {
            "developpement": str(gisement.cout.developpement),
            "outil_annuel": str(gisement.cout.outil_annuel),
            "maintenance": str(gisement.cout.maintenance_annuelle),
            "annee_1": str(gisement.cout.annee_1),
            "recurrent": str(gisement.cout.recurrent),
        },
        "delai_retour_mois": str(gisement.delai_retour_mois),
        "delai_retour_naif_mois": str(gisement.delai_retour_naif_mois),
        "gain_trois_ans": str(gisement.gain_trois_ans),
        "tirages_monte_carlo": gisement.tirages,
    }


def _bloc_faisabilite(projet) -> dict:
    if projet is None:
        return {}
    return {
        "type": projet.faisabilite.type.value,
        "motifs_decision": list(projet.faisabilite.motifs_decision),
        "api_existe": projet.faisabilite.api_existe,
        "interface_stable": projet.faisabilite.interface_stable,
        "jugement_requis": projet.faisabilite.jugement_requis,
        "risque": projet.risque.value,
        "score_priorite": str(projet.score),
        "criteres": {
            "gain": str(projet.criteres.gain),
            "faisabilite": str(projet.criteres.faisabilite),
            "rapidite": str(projet.criteres.rapidite),
            "visibilite": str(projet.criteres.visibilite),
            "securite_juridique": str(projet.criteres.securite_juridique),
        },
    }


def _bloc_recommandation(projet) -> dict:
    if projet is None:
        return {"vague": "aucune"}
    if projet.deconseille is not None:
        return {
            "vague": "aucune",
            "deconseille": projet.deconseille.motif.value,
            "seuil_atteint": projet.deconseille.seuil_atteint,
            "condition_reexamen": projet.deconseille.condition_reexamen,
        }
    return {
        "vague": projet.vague.value,
        "rang": projet.rang,
        "gain_mensuel": str(projet.gisement.gain_mensuel),
        "cout_annee_1": str(projet.gisement.cout.annee_1),
        "retour_mois": str(projet.gisement.delai_retour_mois),
    }


#: How many measured motifs the portal lists. A real corpus carries one motif
#: per fingerprint group - 2 332 on the Apache Kafka corpus - and a page that
#: lists them all is a page nobody reads. The API keeps them all.
MOTIFS_AFFICHES = 100


def motifs_mesures(resultat) -> tuple[int, dict]:
    """The groups the fingerprint produced, and what the classifier made of them."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    lignes = []
    for motif in sorted(resultat.motifs, key=lambda m: m.occurrences.mediane, reverse=True)[:MOTIFS_AFFICHES]:
        lignes.append(
            {
                "ref": motif.catalogue_ref or "(nouveau)",
                "nom": motif.nom,
                "nouveau": motif.nouveau,
                "en_revue_humaine": motif.en_revue_humaine,
                "confiance": str(motif.confiance),
                "occurrences_medianes": str(motif.occurrences.mediane),
                "services": list(motif.services),
                "canaux": [c.value for c in motif.canaux],
                "duree_minutes": str(motif.duree_unitaire_minutes),
                "duree_statut": motif.duree_statut.value,
                "repartition": motif.repartition.value,
                "part_atypique": str(motif.part_atypique),
            }
        )
    return _ok(
        {
            "nb_groupes": len(resultat.groupes),
            "nb_activites": resultat.activites,
            "facteur_reduction": (round(resultat.activites / max(1, len(resultat.groupes)), 1)),
            "nb_motifs_catalogues": sum(1 for m in resultat.motifs if m.catalogue_ref),
            "nb_nouveaux": sum(1 for m in resultat.motifs if m.nouveau),
            "nb_en_revue": len(resultat.revues),
            "motifs": lignes,
            "revue_humaine": [
                {"objet": r.objet, "raison": r.raison, "confiance": str(r.confiance)} for r in resultat.revues
            ],
        }
    )


def catalogue_complet() -> tuple[int, dict]:
    """The 40 motifs of annex B, as data (R25)."""
    catalogue = charger_catalogue()
    par_famille: dict[str, list[dict]] = {}
    for motif in catalogue.motifs:
        par_famille.setdefault(motif.famille, []).append(
            {
                "ref": motif.ref,
                "nom": motif.nom,
                "nom_en": motif.nom_en,
                "duree_typique": str(motif.duree_unitaire_typique_minutes),
                "repartition": motif.repartition_defaut.value,
                "types": [t.value for t in motif.types_envisageables],
                "cout_jours": f"{motif.cout_jours_min}-{motif.cout_jours_max}",
                "modele_texte": motif.modele_texte,
            }
        )
    return _ok(
        {
            "nb_motifs": len(catalogue),
            "familles": {k: len(v) for k, v in sorted(par_famille.items())},
            "motifs_par_famille": dict(sorted(par_famille.items())),
        }
    )


def plan_projet(resultat, consultants: int = 2, jours_par_mois: int = 15) -> tuple[int, dict]:
    """Idea #9 - the sequence turned into a dated plan under a real bench."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    capacite = Capacite(consultants=consultants, jours_par_mois=jours_par_mois)
    plan = planifier(resultat.portefeuille.projets, DEPENDANCES_DEMO, capacite)
    return _ok(
        {
            "capacite": {
                "consultants": consultants,
                "jours_par_mois": jours_par_mois,
                "jours_disponibles": str(capacite.jours_disponibles()),
            },
            "dependances": [
                {"projet": d.projet_id, "apres": list(d.apres), "raison": d.raison} for d in DEPENDANCES_DEMO
            ],
            "taches": [
                {
                    "projet": t.projet_id,
                    "debut_mois": t.debut_mois,
                    "fin_mois": t.fin_mois,
                    "jours": str(t.jours),
                    "dependances": list(t.dependances_respectees),
                }
                for t in plan.taches
            ],
            "impossibles": [{"projet": p, "raison": plan.raisons[p]} for p in plan.impossibles],
            "duree_totale_mois": plan.duree_totale_mois,
            "capacite_utilisee": str(plan.capacite_utilisee),
            "gain_cumule": str(plan.gain_cumule),
            "chemin_critique": list(chemin_critique(resultat.portefeuille.projets, DEPENDANCES_DEMO)),
            "gantt": gantt(plan),
            "jours_par_projet": {
                p.processus_id: str(jours_necessaires(p))
                for p in resultat.portefeuille.projets
                if p.vague != Vague.AUCUNE
            },
        }
    )
