"""Route handlers (lot 18). Pure functions over an `Etat`, framework-agnostic.

The local demo server (`api/serveur.py`) and the Lambda/API-Gateway deployment
call the same handlers, so the offline demo and the deployed URL behave
identically. Every measure route passes through `politique.evaluer` first
(R5); the tenant comes from the token, never from a parameter (EF-71).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from gisement.api.auth import (
    Identite,
    est_dpo_ou_suspension,
    peut_lancer,
    peut_valider_conformite,
)
from gisement.couverture import ligne_publication, par_canal_publication
from gisement.observabilite import CompteurCout, ecart_a_l_estimation
from gisement.pipeline import (
    DONNEES,
    TAUX_DEFAUT,
    VERITE,
    ResultatCampagne,
    campagne_demo,
    executer,
)
from gisement.politique import (
    CompteurRequetes,
    JournalAcces,
    contexte,
    contexte_avec_quota,
    evaluer,
)
from gisement.rapports import cas_business, rapport_dirigeant, registre_conformite
from gisement.types.campagne import Campagne, Conformite
from gisement.types.communs import (
    SEUIL_AGGREGATION_DEFAUT,
    Canal,
    Langue,
    Role,
    StatutCampagne,
    StatutValidation,
)
from gisement.types.conformite import OUTIL_MESURE, RequeteMesure
from gisement.types.mesure import Processus

#: 11.3 - the service manager validates the measured volumes of his perimeter,
#: the DPO verifies the non-attribution and signs them.
ROLES_VALIDATION = (Role.RESPONSABLE_SERVICE, Role.DPO)


@dataclass
class Etat:
    """The state of one campaign - the synthetic demo one, or the real one.

    The same handlers serve both: only the corpus (its root, its declared
    perimeter, its recorded model answers) changes, never the code that reads
    them. That is what makes the site, the API and the tests unable to diverge.
    """

    campagne: Campagne
    corpus: str = "demo"
    """Which corpus the state measures: "demo" or "reel"."""
    statut_campagne: StatutCampagne = StatutCampagne.BROUILLON
    conformite: Conformite | None = None
    resultat: ResultatCampagne | None = None
    journal: JournalAcces = field(default_factory=JournalAcces)
    compteur: CompteurRequetes = field(default_factory=CompteurRequetes)
    cout: CompteurCout = field(default_factory=CompteurCout)
    racine: Path = DONNEES
    declaration: Path = VERITE
    modele: object | None = None
    objets_max: int = 6
    taux_horaire: Decimal | None = TAUX_DEFAUT
    """The rate the campaign publishes its gains with (None = hours only)."""

    @classmethod
    def demo(cls) -> Etat:
        campagne = campagne_demo()
        return cls(campagne=campagne)

    @classmethod
    def reel(cls) -> Etat:
        """The state of the REAL corpus (Apache Kafka), when it is present."""
        from reel.corpus import campagne_reelle, modele_reel

        racine = Path(__file__).resolve().parents[3] / "reel"
        manifeste = json.loads((racine / "donnees" / "manifeste.json").read_text(encoding="utf-8"))
        taux = manifeste.get("taux_horaire")
        return cls(
            campagne=campagne_reelle(racine),
            corpus="reel",
            taux_horaire=Decimal(str(taux)) if taux else None,
            racine=racine / "donnees",
            declaration=racine / "donnees" / "declaration.json",
            modele=modele_reel(racine),
            objets_max=2,
        )


def _ok(donnees: object) -> tuple[int, dict]:
    return 200, {"ok": True, "donnees": donnees}


def _erreur(statut: int, message: str, **extra) -> tuple[int, dict]:
    return statut, {"ok": False, "erreur": message, **extra}


def health(etat: Etat) -> tuple[int, dict]:
    return _ok(
        {
            "statut": "en_ligne",
            "campagne": etat.campagne.id,
            "corpus": etat.corpus,
            "statut_campagne": etat.statut_campagne.value,
            "conformite_validee": bool(etat.conformite and etat.conformite.est_valide()),
            "mesure_lancee": etat.resultat is not None,
        }
    )


def declarer_conformite(etat: Etat, identite: Identite, corps: dict) -> tuple[int, dict]:
    """EF-02 - record the DPO / staff-representative validation."""
    if not peut_valider_conformite(identite):
        return _erreur(403, "seul le DPO ou un representant du personnel peut valider")
    # The threshold can be raised by the DPO, never lowered: k >= 5 is a floor.
    seuil = max(int(corps.get("seuil", SEUIL_AGGREGATION_DEFAUT)), SEUIL_AGGREGATION_DEFAUT)
    etat.conformite = Conformite(
        campagne_id=etat.campagne.id,
        finalite=corps.get("finalite", "mesure des processus de travail"),
        canaux_autorises=tuple(Canal(c) for c in corps.get("canaux", [c.value for c in Canal])),
        seuil_agregation=seuil,
        validation_dpo=True,
        validation_cse=bool(corps.get("cse", True)),
        valide_le=datetime.now(UTC),
        valide_par=identite.utilisateur,
        retention_jours=int(corps.get("retention_jours", 180)),
    )
    etat.statut_campagne = StatutCampagne.PRETE
    return _ok({"conformite": "validee", "seuil": etat.conformite.seuil_agregation})


def lancer(etat: Etat, identite: Identite) -> tuple[int, dict]:
    """EF-04 / R1 - no ingestion without a recorded validation."""
    if not peut_lancer(identite):
        return _erreur(403, "role non autorise a lancer une mesure")
    if etat.conformite is None or not etat.conformite.est_valide():
        return _erreur(
            409,
            "aucune validation DPO/representants enregistree : ingestion refusee (EF-04)",
            bouton_grise=True,
        )
    if etat.resultat is None:
        etat.resultat = executer(
            etat.campagne,
            taux_horaire=etat.taux_horaire,
            racine=etat.racine,
            declaration=etat.declaration,
            modele=etat.modele,
            objets_max=etat.objets_max,
        )
        _alimenter_cout(etat)
    etat.statut_campagne = StatutCampagne.TERMINEE
    return _ok({"campagne": etat.campagne.id, "statut": "terminee"})


def _alimenter_cout(etat: Etat) -> None:
    """Feed the cost counters from the frozen corpus volumes (annex G.3)."""
    etat.cout.charger_tarifs()
    etat.cout.ajouter_transcribe(360)
    etat.cout.ajouter_pages(200)
    if etat.resultat is not None:
        for _ in range(etat.resultat.modeles_appels):
            etat.cout.ajouter_appel(4000, 200)


def suspendre(etat: Etat, identite: Identite) -> tuple[int, dict]:
    """ENF-12 / 11.4 - immediate suspension, state kept, logged."""
    if not est_dpo_ou_suspension(identite):
        return _erreur(403, "seul le DPO ou un representant du personnel peut suspendre")
    if etat.conformite is None:
        return _erreur(409, "aucune campagne a suspendre : conformite non enregistree")
    from dataclasses import replace as _replace

    etat.conformite = _replace(
        etat.conformite,
        suspension=True,
        suspendu_le=datetime.now(UTC),
        suspendu_par=identite.utilisateur,
    )
    etat.statut_campagne = StatutCampagne.SUSPENDUE
    return _ok({"suspendue": True, "etat_conserve": True, "reprise_possible": True})


def campagnes_detail(etat: Etat) -> tuple[int, dict]:
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    resultat = etat.resultat
    return _ok(
        {
            "campagne": etat.campagne.id,
            "activites": resultat.activites,
            "groupes": len(resultat.groupes),
            "motifs": len(resultat.motifs),
            "revue_humaine": len(resultat.revues),
            "couverture": ligne_publication(resultat.couverture),
            "couverture_par_canal": list(par_canal_publication(resultat.couverture)),
            "gisement_net_annuel": str(resultat.portefeuille.gain_net_annuel.bas),
            "cout_mesure_usd": str(etat.cout.tarifer().total_usd),
        }
    )


def projets(etat: Etat) -> tuple[int, dict]:
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    portefeuille = etat.resultat.portefeuille
    return _ok(
        {
            "vague1_existe": portefeuille.vague1_existe,
            "recommandation_elargissement": portefeuille.recommandation_elargissement,
            "part_deconseilles": str(portefeuille.part_deconseilles),
            "projets": [
                {
                    "processus_id": p.processus_id,
                    "type": p.faisabilite.type.value,
                    "vague": p.vague.value,
                    "rang": p.rang,
                    "gain_mensuel": str(p.gisement.gain_mensuel),
                    "delai_retour_mois": str(p.gisement.delai_retour_mois),
                    "risque": p.risque.value,
                    "score": str(p.score),
                }
                for p in portefeuille.projets
            ],
        }
    )


def deconseilles(etat: Etat) -> tuple[int, dict]:
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    return _ok(
        [
            {
                "processus_id": d.processus_id,
                "motif": d.motif.value,
                "seuil_atteint": d.seuil_atteint,
                "condition_reexamen": d.condition_reexamen,
            }
            for d in etat.resultat.portefeuille.deconseilles
        ]
    )


def gisement_detail(etat: Etat, processus_id: str) -> tuple[int, dict]:
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    for gisement in etat.resultat.gisements:
        if gisement.processus_id == processus_id:
            return _ok(
                {
                    "processus_id": processus_id,
                    "temps_brut": str(gisement.temps_brut_heures),
                    "temps_net": str(gisement.temps_net_heures),
                    "intervalle": [
                        str(gisement.temps_net_intervalle.bas),
                        str(gisement.temps_net_intervalle.haut),
                    ],
                    "gain_mensuel": str(gisement.gain_mensuel),
                    "gain_naif_mensuel": str(gisement.gain_naif_mensuel),
                    "ecart_naif": None if gisement.ecart_naif is None else str(gisement.ecart_naif),
                    "delai_retour_mois": (
                        None if gisement.delai_retour_mois is None else str(gisement.delai_retour_mois)
                    ),
                    "delai_retour_naif_mois": (
                        None
                        if gisement.delai_retour_naif_mois is None
                        else str(gisement.delai_retour_naif_mois)
                    ),
                }
            )
    return _erreur(404, f"gisement introuvable : {processus_id}")


def mesurer(etat: Etat, identite: Identite, corps: dict) -> tuple[int, dict]:
    """The k >= 5 demo endpoint: every measure passes through the gateway (R5)."""
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    etat.compteur.incrementer(identite.utilisateur, etat.campagne.id)
    requete = RequeteMesure(
        outil=OUTIL_MESURE,
        tenant_id=identite.tenant_id,
        utilisateur=identite.utilisateur,
        role=identite.role,
        campagne_id=etat.campagne.id,
        canal=Canal(corps["canal"]) if corps.get("canal") else None,
        filtres=dict(corps.get("filtres", {})),
        groupements=tuple(corps.get("groupements", ())),
        sortie=tuple(corps.get("sortie", ())),
        citations=bool(corps.get("citations", False)),
        taille_groupe=corps.get("taille_groupe"),
        taille_resultat_apres_filtres=corps.get("taille_resultat_apres_filtres"),
        requetes_precedentes=etat.compteur.nb(identite.utilisateur, etat.campagne.id),
    )
    ctx = contexte_avec_quota(
        contexte(etat.campagne, corpus_assainis=frozenset({f"CORP-{etat.corpus.upper()}"})),
        etat.compteur,
        identite.utilisateur,
    )
    if etat.conformite is not None:
        ctx = _avec_conformite(ctx, etat)
    decision = evaluer(requete, ctx)
    etat.journal.enregistrer(requete, decision, ctx)
    if decision.refusee:
        return _erreur(
            403,
            decision.motif,
            regles_violees=[r.value for r in decision.regles_violees],
            seuil_agregation=decision.seuil_agregation,
        )
    return _ok(
        {
            "mesure": "agregee",
            "seuil_applique": decision.seuil_agregation,
            "empreinte_requete": decision.empreinte_requete,
        }
    )


def _avec_conformite(ctx, etat: Etat):
    from dataclasses import replace

    return replace(
        ctx,
        conforme=etat.conformite.est_valide(),
        suspendue=etat.conformite.suspension,
        seuil=etat.conformite.seuil_agregation,
    )


def rapport(etat: Etat, langue: str = "fr") -> tuple[int, dict]:
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    from gisement.commands.rapport import _reference_annexe_a

    reference = _reference_annexe_a(etat.resultat)
    texte = rapport_dirigeant(
        etat.resultat.portefeuille,
        etat.resultat.couverture,
        reference,
        etat.campagne,
        Langue(langue),
    )
    return _ok({"langue": langue, "rapport": texte})


def registre(etat: Etat, langue: str = "fr") -> tuple[int, dict]:
    if etat.conformite is None:
        return _erreur(409, "aucune conformite enregistree")
    texte = registre_conformite(etat.campagne, etat.conformite, Langue(langue))
    return _ok({"registre": texte})


def cas_business_route(etat: Etat, processus_id: str, langue: str = "fr") -> tuple[int, dict]:
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    for projet in etat.resultat.portefeuille.projets:
        if projet.processus_id == processus_id:
            processus = _processus(etat, processus_id)
            return _ok({"cas": cas_business(projet, processus, Langue(langue))})
    return _erreur(404, f"projet introuvable : {processus_id}")


def _processus(etat: Etat, processus_id: str) -> Processus | None:
    if etat.resultat is None:
        return None
    for mesure in etat.resultat.mesures:
        if mesure.processus.id == processus_id:
            return mesure.processus
    return None


def budget(etat: Etat) -> tuple[int, dict]:
    """ENF-10 / KPI-8 / R24 - the measured cost, never estimated after the fact."""
    cout = etat.cout.tarifer()
    return _ok(
        {
            "cout_mesure_usd": str(cout.total_usd),
            "transcribe_usd": str(cout.transcribe_usd),
            "data_automation_usd": str(cout.data_automation_usd),
            "inference_usd": str(cout.inference_usd),
            "ecart_a_l_estimation": str(ecart_a_l_estimation(cout)),
            "budget_restant_usd": str(cout.budget_restant()),
        }
    )


def valider_processus(etat: Etat, processus_id: str, decision: str, identite: Identite) -> tuple[int, dict]:
    """EF-24 / 11.3 - the service manager confirms, contests or completes.

    The measured objects are frozen: the validation replaces the process, the
    measure that carries it and the result that holds them, rather than
    mutating them.
    """
    if etat.resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    if identite.role not in ROLES_VALIDATION:
        return _erreur(403, "seul le responsable de service ou le DPO peut valider un volume")
    try:
        statut = StatutValidation(decision)
    except ValueError:
        return _erreur(400, f"decision inconnue : {decision}")
    mesures = []
    trouve = False
    for mesure in etat.resultat.mesures:
        if mesure.processus.id == processus_id:
            mesure = replace(
                mesure,
                processus=replace(mesure.processus, validation=statut, valide_par=identite.utilisateur),
            )
            trouve = True
        mesures.append(mesure)
    if not trouve:
        return _erreur(404, f"processus introuvable : {processus_id}")
    etat.resultat = replace(etat.resultat, mesures=tuple(mesures))
    return _ok({"processus": processus_id, "validation": statut.value})
