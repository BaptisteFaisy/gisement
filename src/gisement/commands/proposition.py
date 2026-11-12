"""`gisement proposition` - the commercial proposal of the MSP (idea #10).

The mapping is sold at cost; what is sold is the portfolio of projects it
produces (8.1). This command turns a measured campaign into the document the
account manager sends: the deposit, the sequence, the first project with its
price, what is deliberately not automated, and the three lines of the offer.

    python3 -m gisement.cli proposition --pdf /tmp/proposition.pdf --langue fr
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gisement.couverture import ligne_publication
from gisement.observabilite import CompteurCout, ecart_a_l_estimation
from gisement.pipeline import campagne_demo, executer
from gisement.rapports.pdf import ecrire_pdf
from gisement.types.communs import Vague

TITRES_VAGUES = {
    Vague.AMORCAGE: "Vague 1 - amorcage (rapide, visible, sur)",
    Vague.STRUCTUREL: "Vague 2 - structurel",
    Vague.TRANSFORMATION: "Vague 3 - transformation",
}

OFFRE = (
    "Cartographie du travail reel : forfait, prix coutant, livree avec le portefeuille.",
    "Suivi trimestriel du realise contre le predit : abonnement, engagement d'un an.",
    "Projets d'automatisation : chiffres au cas par cas, le premier projet de la "
    "vague 1 est propose au cout indique ci-dessous.",
)


def main(argv: list[str] | None = None) -> int:
    args = _parseur().parse_args(argv)
    resultat = executer(campagne_demo())
    lignes = construire(resultat, args.client)
    texte = "\n".join(lignes)
    if args.pdf:
        ecrire_pdf(args.pdf, lignes, titre=f"Proposition - {args.client}")
        print(f"proposition ecrite dans {args.pdf}")
    if args.sortie:
        Path(args.sortie).write_text(texte + "\n", encoding="utf-8")
    if not args.pdf and not args.sortie:
        print(texte)
    return 0


def _parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--client", default="Demo Distribution SAS")
    parseur.add_argument("--pdf", default=None, help="write the proposal as a PDF")
    parseur.add_argument("--sortie", default=None, help="write the proposal as text")
    return parseur


def construire(resultat, client: str) -> list[str]:
    """The proposal, line by line. It formats; it never computes (21.5)."""
    portefeuille = resultat.portefeuille
    compteur = CompteurCout()
    compteur.charger_tarifs()
    compteur.ajouter_transcribe(360)
    compteur.ajouter_pages(200)
    cout = compteur.tarifer()
    lignes = [
        "Proposition - cartographie du travail automatisable",
        f"Client : {client}",
        f"Campagne : {resultat.campagne.id}",
        "",
        ligne_publication(resultat.couverture),
        f"Gisement net annuel identifie : {portefeuille.gain_net_annuel.bas} EUR,",
        f"sur {len(portefeuille.projets)} processus actionnables et "
        f"{len(portefeuille.deconseilles)} processus que nous recommandons de ne pas automatiser.",
        "",
        "Cout reel de la cartographie pour nous : "
        f"{cout.total_usd} USD (transcription {cout.transcribe_usd}, "
        f"extraction documentaire {cout.data_automation_usd}, inference {cout.inference_usd}; "
        f"ecart a l'estimation : {ecart_a_l_estimation(cout)}).",
        "",
    ]
    lignes.extend(_vagues(portefeuille))
    lignes.extend(_deconseilles(portefeuille))
    lignes.extend(_offre(portefeuille))
    return lignes


def _vagues(portefeuille) -> list[str]:
    lignes = ["La sequence que nous recommandons", ""]
    for vague in (Vague.AMORCAGE, Vague.STRUCTUREL, Vague.TRANSFORMATION):
        projets = [p for p in portefeuille.projets if p.vague == vague]
        if not projets:
            continue
        lignes.append(TITRES_VAGUES[vague])
        for projet in projets:
            lignes.append(
                f"  {projet.rang}. {projet.processus_id} (type {projet.faisabilite.type.value}, "
                f"risque {projet.risque.value}) - gain {projet.gisement.gain_mensuel} EUR/mois, "
                f"cout annee 1 {projet.gisement.cout.annee_1} EUR, "
                f"retour {projet.gisement.delai_retour_mois} mois"
            )
        lignes.append("")
    if not portefeuille.vague1_existe:
        lignes.extend([portefeuille.recommandation_elargissement, ""])
    return lignes


def _deconseilles(portefeuille) -> list[str]:
    lignes = ["Ce que nous recommandons de ne PAS automatiser", ""]
    for deconseille in portefeuille.deconseilles:
        lignes.append(f"  {deconseille.processus_id} - {deconseille.seuil_atteint}")
        lignes.append(f"      {deconseille.condition_reexamen}")
    lignes.append("")
    lignes.append(
        "Dire non est ce qui rend le oui credible : un outil qui trouve toujours "
        "quelque chose a automatiser est un outil de vente, pas un instrument."
    )
    lignes.append("")
    return lignes


def _offre(portefeuille) -> list[str]:
    premier = next((p for p in portefeuille.projets if p.vague == Vague.AMORCAGE), None)
    lignes = ["Notre offre", ""]
    lignes.extend(f"  - {offre}" for offre in OFFRE)
    if premier is not None:
        lignes.append("")
        lignes.append(
            f"Premier projet propose : {premier.processus_id}, "
            f"{premier.gisement.cout.annee_1} EUR, retour en "
            f"{premier.gisement.delai_retour_mois} mois, gain "
            f"{premier.gisement.gain_mensuel} EUR/mois."
        )
    lignes.append("")
    lignes.append(
        "Engagement : si le realise d'un trimestre s'ecarte de plus de 40 % du predit, "
        "l'ecart est publie, le modele de calcul est revu, et le trimestre de suivi est offert."
    )
    return lignes
