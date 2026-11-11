"""The sequencer: a portfolio is waves, not a list sorted by gain (15.1, lot 14).

Ranking by declining gain always sends the client at the biggest project first,
which is also the riskiest and the longest - and an initial failure kills the
automation programme for years. The sequence is the deliverable: a wave 1 that
is fast, visible and safe, then the rest.

Weights and wave caps come from `config/priorite.json`: a MSP may prefer gain
over speed without a line of code (15.2, Design criterion of 29.1).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

from gisement.types.communs import (
    Risque,
    TypeAutomatisation,
    Vague,
    arrondi,
    decimal,
)
from gisement.types.economie import (
    CriterePriorite,
    Faisabilite,
    Gisement,
    Intervalle,
    Portefeuille,
    Projet,
)
from gisement.types.mesure import Processus

RACINE_CONFIG = Path(__file__).resolve().parents[2] / "config"


@dataclass(frozen=True)
class PoidsPriorite:
    """15.2 - the versioned weights of the priority score."""

    gain: Decimal = Decimal("0.35")
    faisabilite: Decimal = Decimal("0.25")
    rapidite: Decimal = Decimal("0.20")
    visibilite: Decimal = Decimal("0.15")
    securite_juridique: Decimal = Decimal("0.05")


@dataclass(frozen=True)
class ConfigurationSequence:
    poids: PoidsPriorite
    score_faisabilite: dict[str, Decimal]
    delai_reference: Decimal
    vagues: dict[str, dict]


def charger_configuration(chemin: Path | None = None) -> ConfigurationSequence:
    cible = chemin or (RACINE_CONFIG / "priorite.json")
    brut = json.loads(cible.read_text(encoding="utf-8"))
    poids = brut["poids"]
    return ConfigurationSequence(
        poids=PoidsPriorite(**{k: decimal(v) for k, v in poids.items()}),
        score_faisabilite={k: decimal(v) for k, v in brut["score_faisabilite_par_type"].items()},
        delai_reference=decimal(brut["rapidite_delai_reference_mois"]),
        vagues={k: dict(v) for k, v in brut["vagues"].items()},
    )


def normaliser_gains(gisements: Sequence[Gisement]) -> dict[str, Decimal]:
    brut = {g.processus_id: (g.gain_annuel or Decimal(0)) for g in gisements}
    maximum = max(brut.values(), default=Decimal(1))
    if maximum <= 0:
        return {identifiant: Decimal(0) for identifiant in brut}
    return {identifiant: arrondi(valeur / maximum, 4) for identifiant, valeur in brut.items()}


def critere_faisabilite(type_: TypeAutomatisation, configuration: ConfigurationSequence) -> Decimal:
    return configuration.score_faisabilite.get(type_.value, Decimal(0))


def critere_rapidite(g: Gisement, configuration: ConfigurationSequence) -> Decimal:
    if g.delai_retour_mois is None or configuration.delai_reference <= 0:
        return Decimal(0)
    rapport = g.delai_retour_mois / configuration.delai_reference
    return max(Decimal(0), min(Decimal(1), Decimal(1) - rapport))


def critere_visibilite(processus: Processus | None) -> Decimal:
    if processus is None:
        return Decimal("0.3")
    return Decimal("1.0") if processus.visibilite_dirigeant else Decimal("0.3")


def critere_securite(faisabilite: Faisabilite) -> Decimal:
    if faisabilite.donnee_sensible or faisabilite.obligation_legale:
        return Decimal("0.2")
    return Decimal(1)


def criteres(
    processus: Processus | None,
    gisement: Gisement,
    faisabilite: Faisabilite,
    gains_normalises: Mapping[str, Decimal],
    configuration: ConfigurationSequence,
) -> CriterePriorite:
    return CriterePriorite(
        gain=gains_normalises.get(gisement.processus_id, Decimal(0)),
        faisabilite=critere_faisabilite(faisabilite.type, configuration),
        rapidite=critere_rapidite(gisement, configuration),
        visibilite=critere_visibilite(processus),
        securite_juridique=critere_securite(faisabilite),
    )


def score(criteres_projet: CriterePriorite, poids: PoidsPriorite) -> Decimal:
    total = (
        poids.gain * criteres_projet.gain
        + poids.faisabilite * criteres_projet.faisabilite
        + poids.rapidite * criteres_projet.rapidite
        + poids.visibilite * criteres_projet.visibilite
        + poids.securite_juridique * criteres_projet.securite_juridique
    )
    return arrondi(total, 4)


def _exclu_de_la_vague(vague: dict, projet: Projet, processus: Processus | None) -> bool:
    types = set(vague.get("types", ()))
    if projet.faisabilite.type.value not in types:
        return True
    if vague.get("risque_max") == "faible" and projet.risque != Risque.FAIBLE:
        return True
    if vague.get("visibilite_minimale") and (processus is None or not processus.visibilite_dirigeant):
        return True
    delai_max = decimal(vague.get("delai_retour_max_mois", 0))
    retour = projet.gisement.delai_retour_mois
    return delai_max > 0 and retour is not None and retour > delai_max


def sequencer(
    projets: Sequence[Projet],
    processus: Mapping[str, Processus],
    configuration: ConfigurationSequence | None = None,
) -> Portefeuille:
    """Assign the three waves, honouring the caps, and publish the reserve."""
    configuration = configuration or charger_configuration()
    restante = {nom: int(v.get("projets_max", len(projets))) for nom, v in configuration.vagues.items()}
    budgets = {nom: decimal(v.get("budget_max", 0)) for nom, v in configuration.vagues.items()}
    classes = sorted(projets, key=lambda p: (-p.score, p.processus_id))
    plus_gros = max((p.gisement.gain_annuel or Decimal(0) for p in classes), default=Decimal(0))
    assignes: dict[str, list[Projet]] = {nom: [] for nom in configuration.vagues}
    reserve: list[Projet] = []
    vague1_existe = False
    for projet in classes:
        if projet.deconseille is not None or projet.faisabilite.type == TypeAutomatisation.E:
            continue
        cible = _choisir_vague(
            projet, processus.get(projet.processus_id), configuration, restante, budgets, plus_gros
        )
        if cible is None:
            reserve.append(projet)
            continue
        assignes[cible].append(projet)
        restante[cible] -= 1
        budgets[cible] -= projet.gisement.cout.annee_1
        vague1_existe = vague1_existe or cible == "vague_1"
    return _assembler(configuration, assignes, reserve, classes, vague1_existe)


def _choisir_vague(
    projet: Projet,
    processus: Processus | None,
    configuration: ConfigurationSequence,
    restante: dict[str, int],
    budgets: dict[str, Decimal],
    plus_gros: Decimal,
) -> str | None:
    for nom in configuration.vagues:
        vague = configuration.vagues[nom]
        if restante.get(nom, 0) <= 0:
            continue
        if _exclu_de_la_vague(vague, projet, processus):
            continue
        if budgets.get(nom, Decimal(0)) > 0 and projet.gisement.cout.annee_1 > budgets[nom]:
            continue
        # R17: the biggest gain of the portfolio never starts in wave 1
        if nom == "vague_1" and (projet.gisement.gain_annuel or Decimal(0)) >= plus_gros:
            continue
        return nom
    return None


def _assembler(
    configuration: ConfigurationSequence,
    assignes: dict[str, list[Projet]],
    reserve: list[Projet],
    tous: list[Projet],
    vague1_existe: bool,
) -> Portefeuille:
    projets_finaux: list[Projet] = []
    for nom in configuration.vagues:
        for position, projet in enumerate(assignes[nom], start=1):
            projets_finaux.append(replace(projet, vague=Vague(nom), rang=position))
    projets_finaux.extend(replace(p, vague=Vague.AUCUNE, rang=0) for p in reserve)
    deconseilles = tuple(
        p.deconseille
        for p in tous
        if p.deconseille is not None and p.faisabilite.type == TypeAutomatisation.E
    )
    gain_total = sum((p.gisement.gain_annuel or Decimal(0) for p in tous), Decimal(0))
    part = arrondi(Decimal(len(deconseilles)) / Decimal(len(tous)), 2) if tous else Decimal(0)
    return Portefeuille(
        campagne_id="",
        projets=tuple(projets_finaux),
        reserve=tuple(reserve),
        deconseilles=deconseilles,
        vague1_existe=vague1_existe,
        recommandation_elargissement=(
            ""
            if vague1_existe
            else "Aucun processus ne permet une vague 1 a delai court et risque faible : "
            "elargir le perimetre plutot que de fabriquer une vague 1 artificielle (EF-43, R18)."
        ),
        gain_net_annuel=Intervalle(bas=arrondi(gain_total, 2), haut=arrondi(gain_total, 2)),
        part_deconseilles=part,
    )
