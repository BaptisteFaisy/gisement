"""The executive report, the business cases and the compliance register (lot 16).

The writer **computes nothing** (21.5): it receives the figures already
calculated by the engine and puts them in shape. Two pages in French and in
English (EF-65), for the sponsor, with the five prohibitions of 18.5 recalled
in each report.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from gisement.couverture import ligne_publication
from gisement.types.campagne import Campagne, Conformite, Couverture
from gisement.types.communs import Langue, Vague, pourcentage
from gisement.types.economie import (
    Gisement,
    Portefeuille,
    Projet,
)
from gisement.types.mesure import Processus


@dataclass(frozen=True)
class Libelles:
    """Labels of the report, in French and English (EF-65)."""

    titre: str
    vague1: str
    vague2: str
    vague3: str
    deconseilles: str
    couverture: str
    reference: str
    naif: str
    reel: str
    facteur: str
    prohibitions: tuple[str, ...]


FR = Libelles(
    titre="Rapport dirigeant - Gisement",
    vague1="Vague 1 - amorcage",
    vague2="Vague 2 - structurel",
    vague3="Vague 3 - transformation",
    deconseilles="A ne pas automatiser",
    couverture="Couverture de la mesure",
    reference="Cas de reference : le processus le plus mesure du perimetre",
    naif="Calcul naif",
    reel="Gisement",
    facteur="Facteur de surestimation",
    prohibitions=(
        "Gisement ne produit aucun classement, score ou indicateur individuel.",
        "Aucune mesure du temps de travail utilisable en paie ou en discipline.",
        "Aucune analyse de sentiment, d'opinion ou d'humeur.",
        "Aucune identification de sous-performance individuelle.",
        "Aucun croisement avec les donnees RH (evaluation, absence, sanction).",
    ),
)

EN = Libelles(
    titre="Executive report - Gisement",
    vague1="Wave 1 - quick wins",
    vague2="Wave 2 - structural",
    vague3="Wave 3 - transformation",
    deconseilles="Do not automate",
    couverture="Measurement coverage",
    reference="Reference case: the most measured process of the perimeter",
    naif="Naive calculation",
    reel="Gisement",
    facteur="Overstatement factor",
    prohibitions=(
        "Gisement produces no individual ranking, score or indicator.",
        "No measure of working time usable for payroll or discipline.",
        "No sentiment, opinion or mood analysis.",
        "No identification of individual underperformance.",
        "No cross-referencing with HR data (appraisal, absence, sanction).",
    ),
)


def libelles(langue: Langue) -> Libelles:
    return FR if langue == Langue.FR else EN


def _titre(campagne: Campagne, libelles: Libelles) -> str:
    fenetre = f"{campagne.perimetre.fenetre_debut} .. {campagne.perimetre.fenetre_fin}"
    return f"{libelles.titre}\nCampagne {campagne.id} - fenetre {fenetre}\n"


def rapport_dirigeant(
    portefeuille: Portefeuille,
    couverture: Couverture,
    reference: Gisement | None,
    campagne: Campagne,
    langue: Langue = Langue.FR,
) -> str:
    """Two pages for the sponsor: the deposit, the sequence, the first project."""
    lib = libelles(langue)
    lignes = [_titre(campagne, lib)]
    lignes.append(_ligne_vide())
    lignes.append(f"{lib.couverture}: {ligne_publication(couverture, langue.value)}")
    lignes.append(
        f"Gisement net annuel: {portefeuille.gain_net_annuel.bas} EUR "
        f"({portefeuille.gain_net_annuel.haut} avec l'incertitude)."
    )
    lignes.append(
        f"{lib.deconseilles}: {len(portefeuille.deconseilles)} processus "
        f"({pourcentage(portefeuille.part_deconseilles, 0)} %)."
    )
    lignes.append(_ligne_vide())
    for vague in (Vague.AMORCAGE, Vague.STRUCTUREL, Vague.TRANSFORMATION):
        lignes.extend(_lignes_vague(vague, portefeuille, lib))
    lignes.append(_ligne_vide())
    if reference is not None:
        lignes.extend(_tableau_reference(reference, lib))
    lignes.append(_ligne_vide())
    lignes.extend(f"- {p}" for p in lib.prohibitions)
    return "\n".join(lignes)


def _ligne_vide() -> str:
    return ""


def _lignes_vague(vague: Vague, portefeuille: Portefeuille, lib: Libelles) -> list[str]:
    titres = {Vague.AMORCAGE: lib.vague1, Vague.STRUCTUREL: lib.vague2, Vague.TRANSFORMATION: lib.vague3}
    projets = [p for p in portefeuille.projets if p.vague == vague]
    if not projets:
        return []
    lignes = [titres[vague]]
    for projet in projets:
        lignes.append(_ligne_projet(projet))
    return lignes


def _ligne_projet(projet: Projet) -> str:
    gain = projet.gisement.gain_mensuel or Decimal(0)
    delai = projet.gisement.delai_retour_mois or Decimal(0)
    return (
        f"  {projet.rang}. {projet.processus_id} [{projet.faisabilite.type}] "
        f"gain {gain} EUR/mois, retour {delai} mois"
    )


def _tableau_reference(reference: Gisement, lib: Libelles) -> list[str]:
    """13.3 - the naive/real table printed in every report."""
    gain_naif = reference.gain_naif_mensuel or Decimal(0)
    gain_reel = reference.gain_mensuel or Decimal(0)
    delai_naif = reference.delai_retour_naif_mois or Decimal(0)
    delai_reel = reference.delai_retour_mois or Decimal(0)
    facteur = reference.ecart_naif or Decimal(0)
    return [
        lib.reference,
        f"  {lib.naif}:    {gain_naif} EUR/mois, retour {delai_naif} mois",
        f"  {lib.reel}:      {gain_reel} EUR/mois, retour {delai_reel} mois",
        f"  {lib.facteur}: {facteur}",
    ]


def cas_business(projet: Projet, processus: Processus | None, langue: Langue = Langue.FR) -> str:
    """EF-61 - one exportable business case, reusable as a sales proposal."""
    lib = libelles(langue)
    g = projet.gisement
    nom = processus.nom if processus else projet.processus_id
    lignes = [f"Cas business - {nom} ({projet.processus_id})"]
    lignes.append(f"  Type d'automatisation recommande : {projet.faisabilite.type}")
    lignes.append(f"  Risque : {projet.risque.value}")
    lignes.append(
        f"  Temps net recuperable : {g.temps_net_heures} h/mois [{g.temps_net_intervalle.bas} - "
        f"{g.temps_net_intervalle.haut}]"
    )
    lignes.append(f"  Gain mensuel : {g.gain_mensuel} EUR | annuel : {g.gain_annuel} EUR")
    lignes.append(f"  Cout annee 1 : {g.cout.annee_1} EUR | retour : {g.delai_retour_mois} mois")
    lignes.append(f"  Gain sur 3 ans : {g.gain_trois_ans} EUR")
    lignes.append(f"  {lib.facteur} : {g.ecart_naif}")
    for raison in projet.faisabilite.motifs_decision:
        lignes.append(f"  - {raison}")
    return "\n".join(lignes)


def registre_conformite(
    campagne: Campagne,
    conformite: Conformite,
    langue: Langue = Langue.FR,
) -> str:
    """EF-62 / 24.4 - the document a DPO shows to the regulator."""
    lib = libelles(langue)
    lignes = [f"Registre de conformite - {campagne.id}"]
    lignes.append(f"Finalite : {conformite.finalite or 'mesure des processus de travail'}")
    lignes.append(f"Canaux autorises : {', '.join(c.value for c in conformite.canaux_autorises)}")
    lignes.append(f"Seuil d'agregation : k >= {conformite.seuil_agregation}")
    lignes.append(
        f"Validations : DPO {'oui' if conformite.validation_dpo else 'non'}, "
        f"representants {'oui' if conformite.validation_cse else 'non'}"
    )
    lignes.append(f"Categories filtrees avant stockage : {', '.join(conformite.categories_filtrees)}")
    lignes.append(f"Duree de conservation : {conformite.retention_jours} jours")
    lignes.append(f"Suspension : {'oui' if conformite.suspension else 'non'}")
    lignes.append("Interdictions (chapitre 18.5) :")
    lignes.extend(f"- {p}" for p in lib.prohibitions)
    return "\n".join(lignes)


def fiche_processus(
    processus: Processus, gisement: Gisement, projet: Projet, langue: Langue = Langue.FR
) -> str:
    """Annex D - the full sheet of one process."""
    lib = libelles(langue)
    lignes = [
        f"PROCESSUS {processus.id} - {processus.nom}",
        f"Service : {processus.service}",
        f"Canaux : {', '.join(c.value for c in processus.canaux)}",
        f"Validation : {processus.validation.value}",
        f"Temps brut : {gisement.temps_brut_heures} h/mois",
        f"Temps net : {gisement.temps_net_heures} h/mois [{gisement.temps_net_intervalle.bas} - "
        f"{gisement.temps_net_intervalle.haut}]",
        f"Gain mensuel : {gisement.gain_mensuel} EUR | retour : {gisement.delai_retour_mois} mois",
        f"Type : {projet.faisabilite.type} | risque : {projet.risque.value}",
    ]
    if projet.deconseille is not None:
        lignes.append(f"{lib.deconseilles} : {projet.deconseille.seuil_atteint}")
        lignes.append(f"Condition de reexamen : {projet.deconseille.condition_reexamen}")
    return "\n".join(lignes)
