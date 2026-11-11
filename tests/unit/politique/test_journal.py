"""EF-53 / ENF-07 - every access to pseudonymised data is logged, and purgeable."""

from __future__ import annotations

import json

from gisement.politique import JournalAcces, evaluer


def test_chaque_decision_est_journalisee_autorisee_ou_non(fabrique_requete, requete_agregee, ctx) -> None:
    journal = JournalAcces()
    journal.enregistrer(requete_agregee, evaluer(requete_agregee, ctx))
    refusee = fabrique_requete(groupements=("salarie",))
    journal.enregistrer(refusee, evaluer(refusee, ctx))
    assert len(journal.entrees()) == 2
    assert len(journal.autorisations()) == 1
    assert len(journal.refus()) == 1


def test_une_entree_de_journal_porte_la_trace_complete(fabrique_requete, ctx) -> None:
    from gisement.types import Regle

    journal = JournalAcces()
    requete = fabrique_requete(groupements=("individu",))
    entree = journal.enregistrer(requete, evaluer(requete, ctx))
    assert entree.utilisateur == "u-consultant-01"
    assert entree.outil == "Mesure__agregat"
    assert entree.autorise is False
    assert Regle.INDIVIDU in entree.regles_violees
    assert len(entree.empreinte_requete) == 64
    assert entree.horodatage is not None


def test_le_journal_compte_les_refus_par_regle(fabrique_requete, ctx) -> None:
    from gisement.types import Regle

    journal = JournalAcces()
    for groupement in ("individu", "salarie"):
        requete = fabrique_requete(groupements=(groupement,))
        journal.enregistrer(requete, evaluer(requete, ctx))
    assert journal.par_regle()[Regle.INDIVIDU] == 2
    assert journal.par_utilisateur()["u-consultant-01"] == 2


def test_l_export_jsonl_est_relisible(fabrique_requete, ctx, tmp_path) -> None:
    cible = tmp_path / "registre" / "acces.jsonl"
    journal = JournalAcces(chemin=cible)
    requete = fabrique_requete(taille_groupe=2, taille_resultat_apres_filtres=2)
    journal.enregistrer(requete, evaluer(requete, ctx))
    lignes = cible.read_text(encoding="utf-8").strip().splitlines()
    assert len(lignes) == 1
    brut = json.loads(lignes[0])
    assert brut["autorise"] is False
    assert "regle_k5" in brut["regles_violees"]


def test_la_purge_est_prouvee(fabrique_requete, ctx, tmp_path) -> None:
    """ENF-06 - a purge is proven, not asserted."""
    cible = tmp_path / "acces.jsonl"
    journal = JournalAcces(chemin=cible)
    journal.enregistrer(requete_agregee := fabrique_requete(), evaluer(requete_agregee, ctx))
    journal.enregistrer(requete_agregee, evaluer(requete_agregee, ctx))
    preuve = journal.purger()
    assert preuve.nb_entrees_purgees == 2
    assert len(preuve.empreinte_avant) == 64
    assert journal.entrees() == ()
    assert not cible.exists()
