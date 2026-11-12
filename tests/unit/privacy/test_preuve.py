"""Idea #7 - a verifiable proof of k >= 5, without disclosing the headcount."""

from __future__ import annotations

from dataclasses import replace

from gisement.privacy import attester_sans_taille, certifier, verifier, verifier_chaine
from gisement.types.communs import Role
from gisement.types.conformite import OUTIL_MESURE, RequeteMesure


def requete(**kw) -> RequeteMesure:
    base = {
        "outil": OUTIL_MESURE,
        "tenant_id": "T-DEMO",
        "utilisateur": "u-1",
        "role": Role.CONSULTANT_MSP,
        "campagne_id": "CMP-0031",
        "groupements": ("service",),
        "filtres": {},
        "taille_groupe": 34,
    }
    base.update(kw)
    return RequeteMesure(**base)


def test_une_mesure_agregee_est_certifiee() -> None:
    preuve = certifier("CMP-0031", "M-1", taille_groupe=34, requetes=[requete()])
    assert preuve.conforme is True
    assert preuve.seuil == 5
    assert verifier(preuve) is True
    assert "au moins 5 individus" in preuve.attestation
    assert "34" not in preuve.attestation, "la taille ne doit pas etre publiee"


def test_une_mesure_sous_le_seuil_est_certifiee_refusee() -> None:
    preuve = certifier("CMP-0031", "M-2", taille_groupe=3, requetes=[requete(taille_groupe=3)])
    assert preuve.conforme is False
    assert verifier(preuve) is False
    assert "refusee" in preuve.attestation


def test_le_seuil_ne_peut_pas_etre_abaisse() -> None:
    preuve = certifier("CMP-0031", "M-3", taille_groupe=4, seuil=2)
    assert preuve.seuil == 5
    assert preuve.conforme is False


def test_une_preuve_falsifiee_ne_se_verifie_pas() -> None:
    preuve = certifier("CMP-0031", "M-4", taille_groupe=34, requetes=[requete()])
    assert verifier(preuve) is True
    for falsifiee in (
        replace(preuve, seuil=1),
        replace(preuve, campagne_id="CMP-AUTRE"),
        replace(preuve, mesure_id="M-999"),
        replace(preuve, horodatage="2020-01-01T00:00:00+00:00"),
        replace(preuve, empreinte="0" * 64),
    ):
        assert verifier(falsifiee) is False


def test_une_requete_individuelle_rompt_la_conformite() -> None:
    preuve = certifier(
        "CMP-0031",
        "M-5",
        taille_groupe=34,
        requetes=[requete(groupements=("service", "individu"))],
    )
    assert preuve.conforme is False
    assert "regle_individu" in preuve.regles_appliquees


def test_la_chaine_est_verifiable_et_sa_rupture_est_vue() -> None:
    premiere = certifier("CMP-0031", "M-1", taille_groupe=34, requetes=[requete()])
    seconde = certifier(
        "CMP-0031", "M-2", taille_groupe=12, requetes=[requete()], precedente=premiere.empreinte
    )
    assert verifier_chaine([premiere, seconde]) == ()
    rompue = replace(seconde, empreinte_precedente="0" * 64)
    assert any("maillon casse" in e for e in verifier_chaine([premiere, rompue]))


def test_l_attestation_ne_contient_aucune_donnee_personnelle() -> None:
    preuve = certifier(
        "CMP-0031",
        "M-6",
        taille_groupe=34,
        requetes=[requete(filtres={"service": "adv"})],
    )
    texte = attester_sans_taille(preuve)
    assert "adv" not in texte
    assert "34" not in texte
    assert preuve.empreinte[:16] in texte
