"""Lot 2 - the motif catalogue: 40 motifs, 8 families, all of it data (R25)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from gisement.empreinte import signature
from gisement.motifs import (
    COMPTES_PAR_FAMILLE,
    CandidatMotif,
    charger_catalogue,
    meilleur_candidat,
    nombres_valides,
    refs_en_double,
    score_motif,
    valider_catalogue,
)
from gisement.types import Canal, Repartition, StatutDuree, TypeAutomatisation

RACINE = Path(__file__).resolve().parents[3]
CATALOGUE = charger_catalogue()


def test_le_catalogue_contient_quarante_motifs_back_office_et_douze_motifs_reels() -> None:
    """The catalogue is alive (R25): the 40 back-office motifs, plus the 12 the
    real corpus of `reel/` made necessary - a new family, added as data."""
    assert len(CATALOGUE.famille("ingenierie")) == 12
    assert len(CATALOGUE) == 52
    assert valider_catalogue(CATALOGUE) == ()
    assert refs_en_double(CATALOGUE) == ()


def test_les_huit_familles_de_l_annexe_B() -> None:
    for famille, attendu in COMPTES_PAR_FAMILLE.items():
        assert len(CATALOGUE.famille(famille)) == attendu, famille
    assert sum(COMPTES_PAR_FAMILLE.values()) == 40


def test_chaque_motif_porte_ses_valeurs_par_defaut() -> None:
    motif = CATALOGUE.par_ref("RESS-01")
    assert motif.nom == "Courriel vers ERP"
    assert motif.duree_unitaire_typique_minutes == Decimal("9")
    assert motif.duree_statut_defaut == StatutDuree.MESUREE
    assert motif.repartition_defaut == Repartition.SEMI_REGROUPEE
    assert motif.taux_revue_defaut == Decimal("0.20")
    assert motif.part_atypique_defaut == Decimal("0.15")
    assert TypeAutomatisation.A in motif.types_envisageables
    assert motif.cout_jours_min == Decimal("3")
    assert motif.abonnement_mensuel == Decimal("180")
    assert Canal.COURRIELS in motif.canaux


def test_un_motif_inconnu_leve_une_erreur_explicite() -> None:
    with pytest.raises(KeyError, match="INCONNU"):
        CATALOGUE.par_ref("INCONNU-99")


def test_les_26_refs_du_jeu_de_demo_existent() -> None:
    """The ground truth of lot 0 only uses motifs that exist."""
    verite = json.loads((RACINE / "demo" / "spec-processus.json").read_text(encoding="utf-8"))
    refs = {m for p in verite["processus"] for m in p["motifs"]}
    assert len(refs) >= 20
    for ref in refs:
        assert CATALOGUE.par_ref(ref).ref == ref


@pytest.mark.parametrize("motif", CATALOGUE.motifs, ids=[m.ref for m in CATALOGUE.motifs])
def test_un_motif_est_reconnu_par_sa_propose_phrase(motif) -> None:
    """The canonical sentence of a motif must match that motif first."""
    sig = signature(motif.modele_texte, motif.systemes)
    meilleur = meilleur_candidat(CATALOGUE, sig, motif.systemes)
    assert meilleur is not None
    assert meilleur.ref == motif.ref, f"{motif.ref}: {meilleur.ref} passe devant ({meilleur.score})"


def test_le_score_est_borne_et_deterministe() -> None:
    motif = CATALOGUE.par_ref("RAPPR-01")
    sig = signature("Rapprocher la facture du bon de livraison", ("erp", "ged"))
    premier = score_motif(motif, sig, ("erp", "ged"))
    second = score_motif(motif, sig, ("erp", "ged"))
    assert premier == second
    assert Decimal(0) <= premier <= Decimal(1)
    assert premier > Decimal("0.5")


def test_un_motif_sans_rapport_ne_score_pas() -> None:
    sig = signature("Negocier un contrat cadre avec un fournisseur", ())
    assert meilleur_candidat(CATALOGUE, sig).score < Decimal("0.5")


def test_les_candidats_sont_tries_par_score_puis_par_ref() -> None:
    sig = signature("Relancer le devis sans reponse", ("crm",))
    liste = CATALOGUE.candidats(sig, ("crm",))
    assert len(liste) == len(CATALOGUE)
    assert isinstance(liste[0], CandidatMotif)
    scores = [c.score for c in liste]
    assert scores == sorted(scores, reverse=True)
    assert liste[0].ref == "RELAN-01"


def test_r25_ajouter_un_motif_en_donnees_sans_toucher_au_code(tmp_path: Path) -> None:
    """A partner adds a motif for their own clients: one JSON object, no release."""
    (tmp_path / "motifs").mkdir()
    nouveau = {
        "ref": "RESS-08",
        "famille": "ressaisie",
        "nom": "Saisie d'un releve de compteur",
        "nom_en": "Keying a meter reading",
        "description": "Recopier un releve de compteur dans l'outil.",
        "canaux": ["documents"],
        "indices": {"verbes": ["saisir"], "objets": ["compteur", "releve"], "systemes": ["ged"]},
        "modele_texte": "Saisir le releve de compteur dans l'outil",
        "duree_unitaire_typique_minutes": "5",
        "duree_statut_defaut": "inferree",
        "repartition_defaut": "regroupee",
        "taux_revue_defaut": "0.15",
        "duree_revue_minutes": "1",
        "part_atypique_defaut": "0.10",
        "types_envisageables": ["B"],
        "cout_jours_min": "3",
        "cout_jours_max": "9",
        "abonnement_mensuel": "0",
    }
    (tmp_path / "motifs" / "ressaisie.json").write_text(
        json.dumps([nouveau], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    catalogue = charger_catalogue(tmp_path)
    assert len(catalogue) == 1
    assert catalogue.par_ref("RESS-08").nom_en == "Keying a meter reading"
    assert valider_catalogue(catalogue) != ()  # the counts of annex B are no longer met
    assert meilleur_candidat(catalogue, signature(nouveau["modele_texte"], ("ged",))).ref == "RESS-08"


def test_le_validateur_signale_chaque_anomalie(tmp_path: Path) -> None:
    (tmp_path / "motifs").mkdir()
    casses = [
        {
            "ref": "X-01",
            "famille": "inconnue",
            "nom": "",
            "nom_en": "x",
            "canaux": ["tickets"],
            "indices": {"verbes": ["saisir"], "objets": ["x"]},
            "modele_texte": "",
            "types_envisageables": [],
            "duree_unitaire_typique_minutes": "abc",
            "repartition_defaut": "penible",
            "duree_statut_defaut": "devine",
        },
        {
            "ref": "X-01",
            "famille": "ressaisie",
            "nom": "doublon",
            "nom_en": "dup",
            "canaux": ["inexistant"],
            "indices": {"verbes": [], "objets": []},
            "modele_texte": "x",
            "types_envisageables": ["Z"],
        },
    ]
    (tmp_path / "motifs" / "casse.json").write_text(json.dumps(casses), encoding="utf-8")
    from gisement.motifs.catalogue import charger_catalogue as charger

    erreurs = []
    for brut in casses:
        erreurs.extend(nombres_valides(brut))
    assert any("nombre" in e for e in erreurs)
    catalogue = charger(tmp_path)
    assert refs_en_double(catalogue) == ("X-01",)


def test_les_fichiers_du_catalogue_sont_du_json_valide() -> None:
    fichiers = sorted((RACINE / "catalogue" / "motifs").glob("*.json"))
    assert len(fichiers) == 9
    for chemin in fichiers:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
        assert isinstance(brut, list) and brut
        assert nombres_valides(brut[0]) == ()
