"""The end-to-end pipeline (lot 18): five channels in, a portfolio out.

`executer()` is what the CLI smoke, the API and the evaluation harness run. It
chains: collectors -> sanitisation -> fingerprint groups -> motif labelling ->
aggregation into processes -> economic engine -> feasibility -> advice against
-> sequencing. Every stage is offline; a model is called once per group, never
per activity (21.2), and no Amazon service is ever called during development
(26.4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

from gisement.assainissement import construire_motif_noms
from gisement.calcul import calculer
from gisement.canaux import appels, courriels, documents, journaux, tickets
from gisement.canaux.base import ParametresCollecte
from gisement.classifieur import a_revoir, etiqueter, grouper
from gisement.couverture import heures_par_canal
from gisement.deconseil import motif_deconseil, type_final
from gisement.faisabilite import evaluer_faisabilite, evaluer_risque
from gisement.modeles.base import Modele
from gisement.modeles.fictif import ModeleFictif
from gisement.motifs.catalogue import charger_catalogue
from gisement.processus import MesureProcessus, agreger, charger_declaration
from gisement.sequenceur import (
    charger_configuration,
    criteres,
    normaliser_gains,
    score,
    sequencer,
)
from gisement.types.campagne import Campagne, Couverture
from gisement.types.communs import Canal, decimal
from gisement.types.economie import Deconseille, Faisabilite, Gisement, Portefeuille, Projet
from gisement.types.mesure import Activite, GroupeEmpreinte, Motif, RevueHumaine

RACINE = Path(__file__).resolve().parents[2]
VERITE = RACINE / "demo" / "spec-processus.json"
DONNEES = RACINE / "demo" / "donnees"
DECLARE_DEFAUT = decimal(4040)
TAUX_DEFAUT = Decimal("42")


@dataclass(frozen=True)
class ResultatCampagne:
    """Every intermediate of one campaign, so a stage is auditable alone."""

    campagne: Campagne
    activites: int
    groupes: tuple[GroupeEmpreinte, ...]
    motifs: tuple[Motif, ...]
    mesures: tuple[MesureProcessus, ...]
    gisements: tuple[Gisement, ...]
    faisabilites: tuple[Faisabilite, ...]
    deconseilles: tuple[Deconseille, ...]
    projets: tuple[Projet, ...]
    portefeuille: Portefeuille
    revues: tuple[RevueHumaine, ...]
    couverture: Couverture
    modeles_appels: int


def executer(
    campagne: Campagne,
    *,
    taux_horaire: Decimal | None = TAUX_DEFAUT,
    racine: Path = DONNEES,
    declaration: Path = VERITE,
    modele: Modele | None = None,
    cle: str = "cle-de-campagne",
    objets_max: int = 6,
) -> ResultatCampagne:
    """Run the full pipeline on a corpus (the frozen demo one by default)."""
    declarees = charger_declaration(declaration)
    catalogue = charger_catalogue()
    modele = modele or ModeleFictif(graine=campagne.graine)
    prenoms, noms = _noms_depuis_manifeste(racine)
    parametres = ParametresCollecte(
        campagne_id=campagne.id,
        cle=cle,
        sel=campagne.id,
        graine=campagne.graine,
        motif_noms=construire_motif_noms(prenoms, noms),
        objets_max=objets_max,
    )
    mois = _mois(racine)
    activites = _collecter(racine, parametres)
    groupes = grouper(activites, mois)
    motifs = etiqueter(groupes, catalogue, modele, campagne.id)
    mesures = agreger(declarees, motifs, campagne.id, taux_horaire, campagne.graine)
    gisements = tuple(calculer(m.entree) for m in mesures)
    faisabilites, deconseilles, projets = _decider(mesures, gisements)
    portefeuille = sequencer(list(projets), {m.processus.id: m.processus for m in mesures})
    couverture = _couverture(mesures, gisements, campagne, racine)
    return ResultatCampagne(
        campagne=campagne,
        activites=len(activites),
        groupes=groupes,
        motifs=motifs,
        mesures=mesures,
        gisements=gisements,
        faisabilites=faisabilites,
        deconseilles=deconseilles,
        projets=projets,
        portefeuille=portefeuille,
        revues=a_revoir(motifs, campagne.id),
        couverture=couverture,
        modeles_appels=len(groupes),
    )


def _decider(
    mesures: tuple[MesureProcessus, ...],
    gisements: tuple[Gisement, ...],
) -> tuple[tuple[Faisabilite, ...], tuple[Deconseille, ...], tuple[Projet, ...]]:
    """Feasibility, risk, the advice against, and the project - per process."""
    configuration = charger_configuration()
    gains = normaliser_gains(gisements)
    faisabilites: list[Faisabilite] = []
    deconseilles: list[Deconseille] = []
    projets: list[Projet] = []
    for mesure, gisement in zip(mesures, gisements, strict=True):
        faisabilite = evaluer_faisabilite(mesure.processus, mesure.declare.faits)
        risque = evaluer_risque(
            mesure.declare.faits,
            mesure.entree.part_atypique,
            mesure.declare.changements_douze_mois,
            gisement,
        )
        deconseille = motif_deconseil(
            mesure.processus, gisement, mesure.declare.faits, mesure.entree.part_atypique
        )
        faisabilite = replace(faisabilite, type=type_final(faisabilite, deconseille))
        criteres_projet = criteres(mesure.processus, gisement, faisabilite, gains, configuration)
        projet = Projet(
            id=f"PRJ-{mesure.processus.id}",
            processus_id=mesure.processus.id,
            gisement=gisement,
            faisabilite=faisabilite,
            risque=risque,
            criteres=criteres_projet,
            score=score(criteres_projet, configuration.poids),
            deconseille=deconseille,
        )
        faisabilites.append(faisabilite)
        projets.append(projet)
        if deconseille is not None:
            deconseilles.append(deconseille)
    return tuple(faisabilites), tuple(deconseilles), tuple(projets)


def _collecter(racine: Path, parametres: ParametresCollecte) -> tuple[Activite, ...]:
    toutes: list[Activite] = []
    for module in (tickets, journaux, courriels, documents, appels):
        collectes, _ = module.collecter(module.source_fichiers(racine), parametres)
        toutes.extend(collectes)
    return tuple(toutes)


def _mois(racine: Path) -> list[str]:
    manifeste = racine / "manifeste.json"
    if manifeste.exists():
        return list(json.loads(manifeste.read_text(encoding="utf-8"))["mois"])
    return ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]


def _noms_depuis_manifeste(racine: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    manifeste = racine / "manifeste.json"
    if not manifeste.exists():
        return (), ()
    listes = json.loads(manifeste.read_text(encoding="utf-8")).get("listes", {})
    return tuple(listes.get("prenoms", ())), tuple(listes.get("noms", ()))


def _couverture(
    mesures: tuple[MesureProcessus, ...],
    gisements: tuple[Gisement, ...],
    campagne: Campagne,
    racine: Path,
) -> Couverture:
    heures_couvertes = sum(
        (
            g.temps_brut_heures * decimal(m.entree.occurrences.nb_mois)
            for m, g in zip(mesures, gisements, strict=True)
        ),
        Decimal(0),
    )
    declare = campagne.perimetre.volume_travail_estime_heures or _declare_depuis_manifeste(racine)
    return heures_par_canal({Canal.TICKETS: heures_couvertes}, declare)


def _declare_depuis_manifeste(racine: Path) -> Decimal:
    manifeste = racine / "manifeste.json"
    if not manifeste.exists():
        return DECLARE_DEFAUT
    couverture = json.loads(manifeste.read_text(encoding="utf-8")).get("couverture", {})
    return decimal(couverture.get("volume_travail_estime_heures", DECLARE_DEFAUT))


def campagne_depuis_manifeste(
    racine: Path,
    *,
    campagne_id: str,
    tenant_id: str,
    canaux: tuple[Canal, ...] | None = None,
) -> Campagne:
    """A campaign built from a corpus manifest - demo or real, same code.

    `canaux` defaults to the channels the manifest really carries records for: a
    real corpus declares its absent channels instead of pretending to have them.
    """
    from datetime import date

    from gisement.types.campagne import Perimetre

    manifeste = json.loads((racine / "manifeste.json").read_text(encoding="utf-8"))
    fenetre = manifeste["fenetre"]
    client = manifeste.get("client", {})
    autorises = canaux or tuple(
        Canal(canal) for canal, nombre in (manifeste.get("activites_par_canal") or {}).items() if nombre
    )
    return Campagne(
        id=campagne_id,
        tenant_id=tenant_id,
        perimetre=Perimetre(
            services=tuple(client.get("services", ())),
            sites=tuple(client.get("sites", ())),
            fenetre_debut=date.fromisoformat(fenetre["debut"]),
            fenetre_fin=date.fromisoformat(fenetre["fin"]),
            canaux_autorises=autorises,
            volume_travail_estime_heures=_declare_depuis_manifeste(racine),
        ),
        graine=int(manifeste["graine"]),
    )


def campagne_demo() -> Campagne:
    """A campaign object for the demo client, built from the frozen manifest."""
    return campagne_depuis_manifeste(
        DONNEES,
        campagne_id="CMP-0031",
        tenant_id="T-DEMO",
        canaux=(Canal.TICKETS, Canal.COURRIELS, Canal.DOCUMENTS, Canal.APPELS, Canal.JOURNAUX),
    )
