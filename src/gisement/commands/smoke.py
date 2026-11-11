"""`gisement smoke` - the whole pipeline on the frozen demo corpus.

This is what CI runs (`make smoke`) and what the demo video replays: five
channels in, a sequenced portfolio out, no AWS call, no network.
"""

from __future__ import annotations

from gisement.couverture import ligne_publication
from gisement.pipeline import campagne_demo, executer
from gisement.types.communs import Vague


def main(argv: list[str] | None = None) -> int:
    del argv
    campagne = campagne_demo()
    resultat = executer(campagne)
    portefeuille = resultat.portefeuille

    print(f"Gisement - campagne {campagne.id}")
    print(
        f"  activites mesurees : {resultat.activites} en {len(resultat.groupes)} groupes "
        f"({len(resultat.motifs)} motifs, {len(resultat.revues)} en revue humaine)"
    )
    print(f"  {ligne_publication(resultat.couverture)}")
    print(
        f"  gisement net annuel : {portefeuille.gain_net_annuel.bas} EUR "
        f"({len(portefeuille.deconseilles)} processus deconseilles, "
        f"{portefeuille.part_deconseilles * 100} %)"
    )

    print("\nVagues :")
    for vague in (Vague.AMORCAGE, Vague.STRUCTUREL, Vague.TRANSFORMATION):
        projets = [p for p in portefeuille.projets if p.vague == vague]
        if not projets:
            continue
        print(f"  {vague.value} :")
        for projet in projets:
            print(
                f"    {projet.rang}. {projet.processus_id:5s} {projet.faisabilite.type} gain "
                f"{projet.gisement.gain_mensuel} EUR/mois | retour "
                f"{projet.gisement.delai_retour_mois} mois"
            )
    if not portefeuille.vague1_existe:
        print("  " + portefeuille.recommandation_elargissement)

    print("\nNe pas automatiser :")
    for deconseille in portefeuille.deconseilles:
        print(
            f"  {deconseille.processus_id:5s} {deconseille.motif.value:24s} "
            f"-> {deconseille.condition_reexamen}"
        )

    reference = next((p for p in portefeuille.projets if p.processus_id == "P-07"), None)
    if reference is not None:
        g = reference.gisement
        print("\nCas de reference (P-07) : le facteur qui emporte l'adhesion")
        print(f"  calcul naif : {g.gain_naif_mensuel} EUR/mois  ->  Gisement : {g.gain_mensuel} EUR/mois")
        print(
            f"  facteur : {g.ecart_naif} x    retour naif {g.delai_retour_naif_mois} "
            f"mois vs {g.delai_retour_mois} mois"
        )
    return 0
