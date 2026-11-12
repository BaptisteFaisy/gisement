"""Portal views over the product: follow-up, back-test, privacy, policy, quality.

Same contract as `api/handlers.py`: `(status, body)`, so the local server, the
Lambda and the static site generator share one implementation.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from gisement.commands.proposition import construire as construire_proposition
from gisement.connecteurs import FauxClientHttp, SourceJira, SourceSage, SourceServiceNow
from gisement.evaluation import resume_backtest, resume_evaluation
from gisement.observabilite import CompteurCout, estimation_annexe_g, repartition
from gisement.pipeline import campagne_demo
from gisement.politique.cedar import (
    ROLES_AUTORISES,
    configuration_passerelle,
    definition_politique,
    politique_cedar,
    verifier_cedar,
)
from gisement.politique.regles import ContextePolitique
from gisement.privacy import (
    ParametresDP,
    bruit_agregat,
    certifier,
    resume_garanties,
    verifier_chaine,
)
from gisement.suivi import (
    calibrer,
    comparer,
    detecter,
    precision_cumulee,
)
from gisement.suivi import (
    resume as resume_alertes,
)
from gisement.types.communs import arrondi, decimal

#: Demo history of realised gains, as a multiplier of the predicted monthly
#: gain per quarter. Synthetic on purpose: the real base is built quarter after
#: quarter on live clients, and it is the asset nobody can copy (8.2).
REALISE_DEMO: dict[str, tuple[str, ...]] = {
    "P-07": ("1.06", "1.11", "1.08"),
    "P-14": ("0.97", "1.02", "1.00"),
    "P-19": ("0.88", "0.91", "0.94"),
    "P-01": ("1.42", "1.35", "1.28"),
    "P-16": ("0.55", "0.61", "0.58"),
    "P-11": ("1.03", "1.05", "1.01"),
}
TRIMESTRES_DEMO = ("2027-T1", "2027-T2", "2027-T3")

#: Canned payloads of the connector demo: no network, ever (26.4).
URL_JIRA = "/rest/api/3/search?jql=project=SUP ORDER BY created&maxResults=100"
ISSUE_JIRA = {
    "key": "SUP-12",
    "fields": {
        "summary": "Recopier la commande fournisseur",
        "created": "2026-06-01T09:00:00.000+0200",
        "resolutiondate": "2026-06-01T09:20:00.000+0200",
        "assignee": {"displayName": "Marie Dupont"},
        "status": {"name": "Done"},
        "project": {"key": "SUP"},
    },
}
URL_SNOW = "/api/now/table/incident?sysparm_limit=100&sysparm_query=ORDERBYopened_at"
INCIDENT_SNOW = {
    "number": "INC0001",
    "short_description": "Verifier la coherence des montants",
    "opened_at": "2026-06-03 08:00:00",
    "assigned_to": {"name": "Paul Martin"},
}

#: Canned payloads of the connector demo: no network, ever (26.4).
URL_JIRA = "/rest/api/3/search?jql=project=SUP ORDER BY created&maxResults=100"
ISSUE_JIRA = {
    "key": "SUP-12",
    "fields": {
        "summary": "Recopier la commande fournisseur",
        "created": "2026-06-01T09:00:00.000+0200",
        "resolutiondate": "2026-06-01T09:20:00.000+0200",
        "assignee": {"displayName": "Marie Dupont"},
        "status": {"name": "Done"},
        "project": {"key": "SUP"},
    },
}
URL_SNOW = "/api/now/table/incident?sysparm_limit=100&sysparm_query=ORDERBYopened_at"
INCIDENT_SNOW = {
    "number": "INC0001",
    "short_description": "Verifier la coherence des montants",
    "opened_at": "2026-06-03 08:00:00",
    "assigned_to": {"name": "Paul Martin"},
}


def _ok(donnees: object) -> tuple[int, dict]:
    return 200, {"ok": True, "donnees": donnees}


def _erreur(statut: int, message: str) -> tuple[int, dict]:
    return statut, {"ok": False, "erreur": message}


def _suivis_de_demo(resultat) -> list:
    """The demo history: predicted gains replayed with fixed multipliers."""
    gisements = {g.processus_id: g for g in resultat.gisements}
    suivis = []
    for projet_id, multiplicateurs in REALISE_DEMO.items():
        gisement = gisements.get(projet_id)
        if gisement is None or gisement.gain_mensuel is None:
            continue
        for trimestre, facteur in zip(TRIMESTRES_DEMO, multiplicateurs, strict=True):
            mesure = arrondi(gisement.gain_mensuel * decimal(facteur), 2)
            suivis.append(comparer(gisement.gain_mensuel, mesure, projet_id, trimestre))
    return suivis


def suivi_longitudinal(resultat) -> tuple[int, dict]:
    """Idea #4 - realised against predicted, cumulative accuracy, calibration."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    suivis = _suivis_de_demo(resultat)
    precision = precision_cumulee(suivis)
    alertes = detecter(suivis)
    return _ok(
        {
            "trimestres": list(TRIMESTRES_DEMO),
            "suivis": [
                {
                    "projet": s.projet_id,
                    "trimestre": s.trimestre,
                    "predit": str(s.gain_predit),
                    "mesure": str(s.gain_mesure),
                    "ecart": str(s.ecart),
                    "statut": s.statut,
                    "parametre_fautif": s.parametre_fautif,
                }
                for s in suivis
            ],
            "precision_cumulee": {
                "nb_trimestres": precision.nb_trimestres,
                "nb_projets": precision.nb_projets,
                "ecart_moyen": str(precision.ecart_moyen),
                "part_conformes": str(precision.part_conformes),
                "part_invalides": str(precision.part_invalides),
                "cible": "ecart < 25 % (KPI-6)",
            },
            "alertes": [
                {
                    "projet": a.projet_id,
                    "gravite": a.gravite,
                    "code": a.code,
                    "message": a.message,
                    "valeur": str(a.valeur),
                }
                for a in alertes
            ],
            "resume_alertes": resume_alertes(alertes),
            "coefficients_calibres": _calibration(suivis),
            "note": (
                "Historique de demonstration : les reels sont simules de facon "
                "deterministe. En production, chaque trimestre est saisi par le "
                "consultant et la base devient l'actif longitudinal (8.2)."
            ),
        }
    )


def _calibration(suivis) -> list[dict]:
    return [
        {
            "nom": c.nom,
            "defaut": str(c.valeur_par_defaut),
            "calibre": str(c.valeur_calibree),
            "echantillons": c.echantillons,
            "confiance": str(c.confiance),
            "ratio_realise": str(c.ratio_realise),
            "commentaire": c.commentaire,
        }
        for c in calibrer(suivis)
    ]


def backtest() -> tuple[int, dict]:
    """Idea #6 - the overstatement factor as a distribution across sectors."""
    return _ok(resume_backtest())


def evaluation() -> tuple[int, dict]:
    """Chapter 27 - the four quality measures, published."""
    return _ok(resume_evaluation())


def privacy(resultat) -> tuple[int, dict]:
    """Idea #7 - differential privacy and the verifiable proof of k >= 5."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    parametres = ParametresDP(epsilon=Decimal("1.0"), actif=True)
    groupes = len(resultat.mesures)
    heures = [g.temps_brut_heures for g in resultat.gisements]
    exact = arrondi(sum(heures, Decimal(0)), 2)
    bruite = bruit_agregat(parametres, heures, Decimal(50), graine=resultat.campagne.graine)
    preuves = _chaine_preuves(resultat)
    return _ok(
        {
            "resume_garanties": resume_garanties(parametres, groupes),
            "epsilon": str(parametres.epsilon),
            "delta": str(parametres.delta),
            "agregat_exact_heures": str(exact),
            "agregat_bruite_heures": str(bruite),
            "ecart_absolu": str(abs(exact - bruite)),
            "seuil_revelation": str(decimal(1) / decimal(groupes) if groupes else Decimal(0)),
            "preuves": [
                {
                    "mesure": p.mesure_id,
                    "seuil": p.seuil,
                    "conforme": p.conforme,
                    "regles": list(p.regles_appliquees),
                    "empreinte": p.empreinte[:16],
                    "attestation": p.attestation,
                }
                for p in preuves
            ],
            "chaine_verifiee": verifier_chaine(preuves) == (),
            "erreurs_chaine": list(verifier_chaine(preuves)),
        }
    )


def _chaine_preuves(resultat):
    """One certificate per published process measure, chained by fingerprint."""
    preuves = []
    precedente = ""
    for mesure in resultat.mesures:
        preuves.append(
            certifier(
                campagne_id=resultat.campagne.id,
                mesure_id=mesure.declare.id,
                taille_groupe=max(5, len(mesure.declare.service) + 5),
                seuil=5,
                precedente=precedente,
            )
        )
        precedente = preuves[-1].empreinte
    return tuple(preuves)


def politique_cedar_vue() -> tuple[int, dict]:
    """Idea #2 - the real AgentCore artefacts: Cedar policy and gateway config."""
    contexte = ContextePolitique(
        campagne_id="*",
        tenant_id="*",
        conforme=True,
        suspendue=False,
        budget_restant=Decimal(20),
    )
    texte = politique_cedar(contexte)
    return _ok(
        {
            "cedar": texte,
            "lignes": len(texte.splitlines()),
            "interdictions": texte.count("forbid ("),
            "autorisations": texte.count("permit ("),
            "roles_autorises": list(ROLES_AUTORISES),
            "verification": list(verifier_cedar(texte, contexte)),
            "definition_cloudformation": definition_politique(contexte),
            "configuration_passerelle": configuration_passerelle(
                lambda_arn="arn:aws:lambda:eu-west-3:ACCOUNT:function:gisement-intercepteur",
                policy_engine_arn="arn:aws:bedrock-agentcore:eu-west-3:ACCOUNT:policy-engine/gisement",
                role_arn="arn:aws:iam::ACCOUNT:role/gisement-gateway",
                discovery_url=(
                    "https://cognito-idp.eu-west-3.amazonaws.com/POOL/.well-known/openid-configuration"
                ),
                allowed_clients=("client-id",),
            ),
            "note": (
                "Le Cedar est genere par gisement.politique.cedar a partir du meme "
                "registre que le moteur teste hors ligne : la politique deployee et la "
                "politique testee ne peuvent pas diverger (D-09, D-22)."
            ),
        }
    )


def connecteurs() -> tuple[int, dict]:
    """Idea #8 - the real connectors, demonstrated on canned payloads."""
    jira = SourceJira(FauxClientHttp(pages={URL_JIRA: [ISSUE_JIRA]}), projet="SUP")
    snow = SourceServiceNow(FauxClientHttp(pages={URL_SNOW: [INCIDENT_SNOW]}))
    return _ok(
        {
            "jira": {"canal": jira.canal.value, "volume": jira.volume(), "exemple": next(iter(jira.lire()))},
            "servicenow": {
                "canal": snow.canal.value,
                "volume": snow.volume(),
                "exemple": next(iter(snow.lire())),
            },
            "sage": {"canal": "journaux", "exemple": _exemple_sage()},
            "note": (
                "Le client HTTP est injecte : aucune requete reseau en CI. Les "
                "identifiants de personne sont transmis par le connecteur et "
                "pseudonymises a l'ingestion, en aval (R3)."
            ),
        }
    )


def _exemple_sage() -> dict:
    """One normalised ERP line, from an in-memory CSV."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fichier:
        fichier.write(
            "Date;Operation;Compte;Montant;Utilisateur;Duree\n"
            "2026-06-01T09:00:00;Saisie commande;401000;1284,50;ADV-JOUR;540\n"
        )
        chemin = fichier.name
    ligne = next(iter(SourceSage(chemin).lire()))
    Path(chemin).unlink(missing_ok=True)
    return ligne


def proposition(resultat) -> tuple[int, dict]:
    """Idea #10 - the commercial proposal, as text (the PDF is the same lines)."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    return _ok(
        {
            "client": "Demo Distribution SAS",
            "texte": "\n".join(construire_proposition(resultat, "Demo Distribution SAS")),
            "pdf": "python3 -m gisement.cli proposition --pdf proposition.pdf",
        }
    )


def quick_assets(resultat) -> tuple[int, dict]:
    """Lot 19 - the tables Amazon Quick renders, straight from the campaign."""
    if resultat is None:
        return _erreur(409, "la mesure n'a pas ete lancee")
    from gisement.commands.assets import (
        spec_tableau_de_bord,
        table_portefeuille,
        table_tendances,
        table_vagues,
    )

    return _ok(
        {
            "portefeuille": table_portefeuille(resultat),
            "vagues": table_vagues(resultat),
            "tendances": table_tendances(resultat)[:6],
            "tableau_de_bord": spec_tableau_de_bord(),
        }
    )


def cout_detaille() -> tuple[int, dict]:
    """KPI-8 / R24 - the measured cost, itemised against the annex G estimate."""
    compteur = CompteurCout()
    compteur.charger_tarifs()
    compteur.ajouter_transcribe(360)
    compteur.ajouter_pages(200)
    for _ in range(42):
        compteur.ajouter_appel(4000, 200)
    cout = compteur.tarifer()
    return _ok(
        {
            "cout_mesure_usd": str(cout.total_usd),
            "transcribe": {"minutes": str(cout.transcribe_minutes), "usd": str(cout.transcribe_usd)},
            "data_automation": {"pages": cout.data_automation_pages, "usd": str(cout.data_automation_usd)},
            "inference": {
                "jetons_entree": cout.jetons_entree,
                "jetons_sortie": cout.jetons_sortie,
                "appels": cout.appels_modele,
                "usd": str(cout.inference_usd),
            },
            "repartition": {k: str(v) for k, v in repartition(cout).items()},
            "estimation_annexe_g_usd": str(estimation_annexe_g()),
            "ecart_a_l_estimation": str(_ecart(cout.total_usd)),
            "budget_credits_usd": "200.00",
            "cartographies_financees": str(arrondi(Decimal(200) / cout.total_usd, 1)),
        }
    )


def _ecart(mesure: Decimal) -> Decimal:
    estimation = estimation_annexe_g()
    return arrondi(abs(mesure - estimation) / estimation, 4)


def campagne_courante() -> dict:
    """The demo campaign descriptor, for the portal header."""
    campagne = campagne_demo()
    return {
        "id": campagne.id,
        "tenant": campagne.tenant_id,
        "fenetre": f"{campagne.perimetre.fenetre_debut} .. {campagne.perimetre.fenetre_fin}",
        "services": list(campagne.perimetre.services),
        "graine": campagne.graine,
    }
