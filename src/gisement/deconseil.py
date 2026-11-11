"""Category E: what must NOT be automated (chapter 16, EF-44).

A tool that always finds something to automate is a sales tool, not an
instrument. The six reasons of 16.1 are applied by code on measured facts, the
advice is published with the same care as the projects, and every advice
carries its **re-examination condition** - which turns a "no" into a "not yet"
and gives the quarterly follow-up a reason to exist.
"""

from __future__ import annotations

from decimal import Decimal

from gisement.types.communs import (
    CHANGEMENTS_INSTABILITE,
    DELAI_RETOUR_MAXIMAL_MOIS,
    GAIN_ANNUEL_MINIMAL,
    PART_ATYPIQUE_MAXIMALE,
    Langue,
    MotifDeconseil,
    TypeAutomatisation,
    pourcentage,
)
from gisement.types.economie import Deconseille, Faisabilite, FaitsFaisabilite, Gisement
from gisement.types.mesure import Processus

#: Band of a healthy portfolio (16.3, KPI-9): below 10 % the tool is too
#: complacent, above 40 % the scope was badly chosen.
PART_PORTEFEUILLE_SAIN_MIN = Decimal("0.15")
PART_PORTEFEUILLE_SAIN_MAX = Decimal("0.30")

#: 16.1 order: the headline reason of a process is the first one it triggers.
#: This order reproduces the five reasons published in annex E.
ORDRE_MOTIFS: tuple[MotifDeconseil, ...] = (
    MotifDeconseil.OBLIGATION_LEGALE,
    MotifDeconseil.INSTABILITE,
    MotifDeconseil.DEPENDANCE_EXTERNE,
    MotifDeconseil.VOLUME_INSUFFISANT,
    MotifDeconseil.JUGEMENT_NON_FORMALISABLE,
    MotifDeconseil.RETOUR_TROP_LONG,
)

CONDITIONS_REEXAMEN: dict[MotifDeconseil, str] = {
    MotifDeconseil.OBLIGATION_LEGALE: "reexamen si le texte qui impose un traitement humain change",
    MotifDeconseil.INSTABILITE: "reexamen apres six mois de stabilite du processus",
    MotifDeconseil.DEPENDANCE_EXTERNE: "reexamen si une API contractuelle devient disponible",
    MotifDeconseil.VOLUME_INSUFFISANT: "reexamen si le volume depasse 15 occurrences par mois",
    MotifDeconseil.JUGEMENT_NON_FORMALISABLE: "reexamen si la part de cas atypiques passe sous 30 %",
    MotifDeconseil.RETOUR_TROP_LONG: "reexamen si le cout d'automatisation passe sous douze mois de gain",
}


def tous_les_motifs(
    processus: Processus,
    gisement: Gisement,
    faits: FaitsFaisabilite,
    part_atypique: Decimal = Decimal(0),
) -> tuple[Deconseille, ...]:
    """Every reason that applies, in the order of 16.1."""
    valeurs = {
        "temps_net_heures": gisement.temps_net_heures,
        "gain_annuel": gisement.gain_annuel or Decimal(0),
        "cout_annee_1": gisement.cout.annee_1,
        "delai_retour_mois": gisement.delai_retour_mois or Decimal(0),
        "part_atypique": part_atypique,
        "changements_douze_mois": Decimal(processus.changements_douze_mois),
    }
    trouves: dict[MotifDeconseil, str] = {}
    if faits.obligation_legale_humaine:
        trouves[MotifDeconseil.OBLIGATION_LEGALE] = "obligation legale de traitement humain (signature)"
    if processus.changements_douze_mois >= CHANGEMENTS_INSTABILITE:
        trouves[MotifDeconseil.INSTABILITE] = (
            f"{processus.changements_douze_mois} changements du processus en 12 mois"
        )
    if faits.dependance_externe_non_contractuelle:
        trouves[MotifDeconseil.DEPENDANCE_EXTERNE] = "interface tierce sans API ni engagement de stabilite"
    if valeurs["gain_annuel"] < GAIN_ANNUEL_MINIMAL:
        trouves[MotifDeconseil.VOLUME_INSUFFISANT] = (
            f"gain annuel net {valeurs['gain_annuel']} EUR inferieur a {GAIN_ANNUEL_MINIMAL} EUR"
        )
    if part_atypique > PART_ATYPIQUE_MAXIMALE:
        trouves[MotifDeconseil.JUGEMENT_NON_FORMALISABLE] = (
            f"part de cas atypiques {pourcentage(part_atypique, 0)} % superieure a 40 %"
        )
    if gisement.delai_retour_mois is not None and gisement.delai_retour_mois > DELAI_RETOUR_MAXIMAL_MOIS:
        trouves[MotifDeconseil.RETOUR_TROP_LONG] = (
            f"delai de retour {gisement.delai_retour_mois} mois superieur a {DELAI_RETOUR_MAXIMAL_MOIS} mois"
        )
    return tuple(
        Deconseille(
            processus_id=processus.id,
            motif=motif,
            seuil_atteint=trouves[motif],
            condition_reexamen=CONDITIONS_REEXAMEN[motif],
            valeurs=valeurs,
        )
        for motif in ORDRE_MOTIFS
        if motif in trouves
    )


def motif_deconseil(
    processus: Processus,
    gisement: Gisement,
    faits: FaitsFaisabilite,
    part_atypique: Decimal = Decimal(0),
) -> Deconseille | None:
    """The headline reason, or None when the process is worth automating."""
    motifs = tous_les_motifs(processus, gisement, faits, part_atypique)
    return motifs[0] if motifs else None


def formuler(deconseille: Deconseille, langue: Langue = Langue.FR) -> str:
    """16.2 - the wording of an advice. It formats, it never computes."""
    heures = deconseille.valeurs.get("temps_net_heures", Decimal(0))
    annuel = deconseille.valeurs.get("gain_annuel", Decimal(0))
    cout = deconseille.valeurs.get("cout_annee_1", Decimal(0))
    delai = deconseille.valeurs.get("delai_retour_mois", Decimal(0))
    if langue == Langue.EN:
        return (
            "Do not automate. This process represents "
            f"{heures} h/month, i.e. {annuel} EUR per year. The automation cost is estimated at "
            f"{cout} EUR, a payback of {delai} months. Recommendation: {deconseille.condition_reexamen}."
        )
    return (
        "Ne pas automatiser. Ce processus represente "
        f"{heures} h/mois, soit {annuel} EUR par an. Le cout d'automatisation est estime a "
        f"{cout} EUR, soit un retour en {delai} mois. Recommandation : {deconseille.condition_reexamen}."
    )


def part_deconseilles(nb_deconseilles: int, nb_processus: int) -> Decimal:
    """KPI-9 - share of the portfolio that is advised against."""
    if nb_processus <= 0:
        return Decimal(0)
    return Decimal(nb_deconseilles) / Decimal(nb_processus)


def qualifier_portefeuille(part: Decimal) -> str:
    """16.3 - is the share of category E a sign of a healthy mapping?"""
    if part < Decimal("0.10"):
        return "trop complaisant : moins de 10 % de processus deconseilles"
    if part < PART_PORTEFEUILLE_SAIN_MIN:
        return "part faible : la cartographie merite d'etre etendue"
    if part <= PART_PORTEFEUILLE_SAIN_MAX:
        return "portefeuille sain"
    if part <= Decimal("0.40"):
        return "part elevee : le perimetre est probablement trop large"
    return "perimetre mal choisi : plus de 40 % de processus deconseilles"


def type_final(faisabilite: Faisabilite, deconseille: Deconseille | None) -> TypeAutomatisation:
    """A process advised against is published as category E, whatever its tree type."""
    return TypeAutomatisation.E if deconseille is not None else faisabilite.type
