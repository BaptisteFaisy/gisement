"""`gisement rapport` - produce the executive report, the business cases and
the compliance register, in French and English (lot 16, EF-60, EF-62, EF-65)."""

from __future__ import annotations

import argparse
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from gisement.calcul import calculer
from gisement.pipeline import campagne_demo, executer
from gisement.rapports import cas_business, rapport_dirigeant, registre_conformite
from gisement.types.campagne import Conformite
from gisement.types.communs import Canal, Langue
from gisement.types.economie import CoutAutomatisation


def main(argv: list[str] | None = None) -> int:
    args = _parseur().parse_args(argv)
    langue = Langue(args.langue)
    campagne = campagne_demo()
    resultat = executer(campagne)
    portefeuille = resultat.portefeuille

    reference = _reference_annexe_a(resultat)
    conformite = Conformite(
        campagne_id=campagne.id,
        finalite="mesure des processus de travail",
        canaux_autorises=tuple(Canal),
        validation_dpo=True,
        validation_cse=True,
    )
    rapport = rapport_dirigeant(portefeuille, resultat.couverture, reference, campagne, langue)
    registre = registre_conformite(campagne, conformite, langue)
    cas = _cas_business(portefeuille, resultat, langue)

    print(rapport)
    print("\n" + "=" * 60 + "\n")
    print(cas)
    return _ecrire(args.sortie, langue, rapport, cas, registre)


def _parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--langue", choices=["fr", "en"], default="fr")
    parseur.add_argument("--sortie", default=None, help="write the reports to a directory")
    return parseur


def _reference_annexe_a(resultat):
    """The full P-07, not the type-A action the portfolio recommends: it is the
    table that makes the factor 2.61 of annex A land in the report."""
    mesure = next(m for m in resultat.mesures if m.declare.id == "P-07")
    return calculer(
        replace(
            mesure.entree,
            part_volume_traitee=Decimal(1),
            suppression_etape=False,
            cout=CoutAutomatisation(
                jours=Decimal(12),
                tjm=Decimal(650),
                abonnement_mensuel=Decimal(180),
                taux_maintenance=Decimal("0.08"),
            ),
        )
    )


def _cas_business(portefeuille, resultat, langue: Langue) -> str:
    processus = {m.processus.id: m.processus for m in resultat.mesures}
    return "\n\n".join(
        cas_business(p, processus.get(p.processus_id), langue)
        for p in portefeuille.projets
        if p.vague.value != "aucune"
    )


def _ecrire(sortie: str | None, langue: Langue, rapport: str, cas: str, registre: str) -> int:
    if not sortie:
        return 0
    cible = Path(sortie)
    cible.mkdir(parents=True, exist_ok=True)
    (cible / f"rapport-dirigeant.{langue.value}.md").write_text(rapport, encoding="utf-8")
    (cible / f"cas-business.{langue.value}.md").write_text(cas, encoding="utf-8")
    (cible / f"registre-conformite.{langue.value}.md").write_text(registre, encoding="utf-8")
    print(f"\nrapports ecrits dans {cible}")
    return 0
